"""Bounded read-only CoStar, Matterport and Vexcel evidence adapters."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import math
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .contracts import evidence_claim

VEXCEL_BASE = "https://api.vexcelgroup.com/v2/"
MATTERPORT_GRAPH = "https://api.matterport.com/api/models/graph"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def _status(http_status, *, has_data=True):
    if http_status == 200:
        return "available" if has_data else "not_covered"
    if http_status in (401, 403): return "unauthorized"
    if http_status == 404: return "not_covered"
    if http_status == 429: return "rate_limited"
    if http_status == 0 or (http_status and http_status >= 500): return "temporarily_unavailable"
    return "unknown"


def _safe_call_error(error):
    if isinstance(error, HTTPError):
        try: error.close()
        except Exception: pass
        return error.code, None
    return 0, type(error).__name__


class CoStarAdapter:
    def collect(self, handoff, costar_service=None):
        selected = handoff["selected_listing"]
        facts = handoff.get("property_facts") or {}
        retrieved = utcnow()
        if not facts.get("address") and costar_service:
            try:
                facts = costar_service.get_property(int(selected["property_id"]))
            except Exception as error:
                return {"status": "temporarily_unavailable", "error": type(error).__name__, "claims": [], "facts": {}}
        if not facts or facts.get("error"):
            return {"status": "unknown", "claims": [], "facts": {}}
        property_id = str(selected["property_id"])
        facts_id = str(facts.get("property_id", property_id))
        if facts_id != property_id:
            return {"status": "unknown", "error": "identity_mismatch", "claims": [], "facts": {}}
        fields = {
            "gross_building_area_sqft": (facts.get("gross_building_area_sqft"), "sqft", "building_gross_floor_area"),
            "rentable_building_area_sqft": (facts.get("rentable_building_area_sqft"), "sqft", "building_rentable_area"),
            "stories": (facts.get("stories"), "stories", "above_grade_story_count"),
            "property_type": (facts.get("property_type"), None, "provider_asset_class"),
            "building_class": (facts.get("building_class"), None, "provider_building_class"),
            "zoning_description": (None if facts.get("zoning_description")=="Unzoned / Harris County jurisdiction" else facts.get("zoning_description"), None, "provider_zoning_label"),
            "has_sprinklers": (facts.get("has_sprinklers"), None, "provider_recorded_sprinkler_flag"),
            "parking_ratio": (facts.get("parking_ratio"), "ratio", "provider_parking_ratio"),
        }
        claims = [evidence_claim(claim_id=f"costar:{property_id}:{fact}", fact=fact, value=value, unit=unit,
                    source="costar", source_record_id=property_id, scope_type="costar_property_record", scope_id=property_id,
                    semantics=semantics, observed_at=facts.get("source_updated_at"), retrieved_at=retrieved,
                    evidence_ref=facts.get("source_reference") or f"CoStar property {property_id}", quality="provider_reported",
                    identity_key=f"costar-property:{property_id}") for fact,(value,unit,semantics) in fields.items()]
        raw_record = None
        if costar_service and hasattr(costar_service, "get_stage2_raw_record"):
            try: raw_record = costar_service.get_stage2_raw_record(int(property_id))
            except Exception: raw_record = None
        if isinstance(raw_record, dict):
            for key,field in (("grossTypicalFloorSquareFeet","gross_typical_floor_sqft"),):
                if key in raw_record: summary_value=raw_record.get(key)
                else: summary_value=None
                facts[field]=summary_value
            if "yearBuilt" in raw_record: facts["year_built"] = raw_record.get("yearBuilt")
        claims.append(evidence_claim(claim_id=f"costar:{selected.get('listing_id')}:suite_area",
                    fact="available_suite_area", value=selected.get("area_min_sqft"), unit="sqft", source="costar",
                    source_record_id=selected.get("listing_id"), scope_type="suite" if selected.get("space_id") else "listing",
                    scope_id=selected.get("space_id") or selected.get("listing_id"),
                    semantics="advertised_area_range_not_verified_usable_area", observed_at=selected.get("source_updated_at"),
                    retrieved_at=retrieved, evidence_ref=selected.get("source_reference"), quality="provider_reported",
                    identity_key=f"costar-property:{property_id}"))
        summary = {k:facts.get(k) for k in ("property_id","address","city","state","latitude","longitude","property_type","building_class","gross_building_area_sqft","rentable_building_area_sqft","gross_typical_floor_sqft","stories","has_sprinklers","zoning_description","parking_ratio","matterport_model_ids")}
        if facts.get("year_built") is not None: summary["year_built"] = facts["year_built"]
        summary["source_reference"] = f"CoStar property {property_id}"
        claims.append(evidence_claim(claim_id=f"costar:{property_id}:address",fact="property_address",value=facts.get("address"),
            source="costar",source_record_id=property_id,scope_type="costar_property_record",scope_id=property_id,
            semantics="provider property address; not a separate building identifier",retrieved_at=retrieved,
            evidence_ref=summary["source_reference"],quality="provider_reported",identity_key=f"costar-property:{property_id}"))
        for field,fact,unit,semantics in (("gross_typical_floor_sqft","typical_floor_area","sqft","gross typical floor area"),
                                         ("year_built","year_built",None,"provider reported year built")):
            if summary.get(field) is not None:
                claims.append(evidence_claim(claim_id=f"costar:{property_id}:{fact}",fact=fact,value=summary[field],unit=unit,
                    source="costar",source_record_id=property_id,scope_type="costar_property_record",scope_id=property_id,
                    semantics=semantics,retrieved_at=retrieved,evidence_ref=summary["source_reference"],quality="provider_reported",
                    identity_key=f"costar-property:{property_id}"))
        tenancies=self._tenancies(costar_service,int(property_id)) if costar_service else None
        if tenancies:
            for tenancy in tenancies[:100]:
                for suite in sorted(tenancy.get("suites") or [],key=str)[:10]:
                    claims.append(evidence_claim(claim_id=f"costar:tenancy:{tenancy.get('id')}:{suite}",fact="suite_occupancy",
                        value="occupied",source="costar",source_record_id=tenancy.get("id"),scope_type="suite",scope_id=str(suite),
                        semantics="reported tenancy interval; not a current physical observation",observed_at=tenancy.get("start"),
                        retrieved_at=retrieved,evidence_ref=f"CoStar occupancy record {tenancy.get('id')}",quality="provider_reported",
                        identity_key=f"costar-property:{property_id}",extra={"move_in_date":tenancy.get("start"),"move_out_date":tenancy.get("end"),"area_sqft":tenancy.get("square_feet")}))
        return {"status": "available", "retrieved_at": retrieved, "facts": summary, "claims": claims,
                "raw_property_record": raw_record,
                "tenancies": tenancies,
                "listing_context": {k:selected.get(k) for k in ("property_id","listing_id","space_id","stable_id","transaction_type","suite","address","area_min_sqft","area_max_sqft","asking_price_usd","rent_normalization")}}

    @staticmethod
    def _tenancies(costar_service, property_id):
        try:
            import sys
            from pathlib import Path
            playground = Path(__file__).resolve().parents[2] / "playground"
            if str(playground) not in sys.path: sys.path.insert(0, str(playground))
            from reconcile import load_tenancies
            return load_tenancies(str(costar_service.kit_path), {property_id}, costar_service.password).get(property_id, [])
        except Exception:
            return None


def _canonical_address(value):
    words = re.findall(r"[a-z0-9]+", (value or "").casefold())
    aliases = {"road":"rd","street":"st","drive":"dr","parkway":"pkwy","boulevard":"blvd","highway":"hwy","avenue":"ave","north":"n","south":"s","east":"e","west":"w"}
    return " ".join(aliases.get(w,w) for w in words)


class MatterportAdapter:
    QUERY = """query($id: ID!) { model(id: $id) { id name state visibility created modified description address { streetAddressLines locality administrativeArea postalCode countryCode } floors { id label dimensions(units: imperial) { areaFloor height units } rooms { id label dimensions(units: imperial) { areaFloor height units } } } rooms { id label dimensions(units: imperial) { areaFloor height units } } locations { id label position { x y z } floor { id label } room { id } panos { id skybox(resolution: \"high\") { id status format children } } } } }"""

    def __init__(self, opener=urlopen): self.opener = opener

    def _query(self, model_id, key, secret):
        auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
        request = Request(MATTERPORT_GRAPH, data=json.dumps({"query":self.QUERY,"variables":{"id":model_id}}).encode(),
            headers={"Authorization":f"Basic {auth}","Content-Type":"application/json","Accept":"application/json"})
        with self.opener(request,timeout=25) as response:
            return response.status, json.loads(response.read())

    def collect(self, handoff):
        ids=(handoff.get("property_facts") or {}).get("matterport_model_ids") or []
        if not ids:
            return {"status":"unknown","reason":"No Matterport model ID is linked in the selected CoStar property record.","models":[],"claims":[]}
        key,secret=os.environ.get("MATTERPORT_API_KEY"),os.environ.get("MATTERPORT_API_TOKEN")
        if not key or not secret:
            return {"status":"unknown","reason":"Matterport API credentials are not configured.","models":[],"claims":[]}
        models=[]; claims=[]; statuses=[]; visual={"status":"not_run","reason":"Visual analysis is disabled.","observations":[]}
        for model_id in list(dict.fromkeys(str(v) for v in ids))[:3]:
            try:
                code,payload=self._query(model_id,key,secret)
            except HTTPError as error:
                code,_=_safe_call_error(error); statuses.append(_status(code)); continue
            except (URLError,TimeoutError,OSError,ValueError) as error:
                statuses.append("temporarily_unavailable"); continue
            model=((payload.get("data") or {}).get("model")) if code==200 else None
            if code==401 or code==403:
                statuses.append("unauthorized"); continue
            if not model or payload.get("errors"):
                statuses.append("not_covered" if code==200 else _status(code)); continue
            facts=handoff.get("property_facts") or {}
            # Stage 1's selected listing is the exact record the user chose and
            # often carries a directional prefix omitted from the property summary.
            expected=_canonical_address(handoff["selected_listing"].get("address") or facts.get("address"))
            actual=_canonical_address(model.get("name"))
            addr=model.get("address") or {}
            address_lines=addr.get("streetAddressLines") or []
            if isinstance(address_lines, str):
                address_lines = [address_lines]
            model_street=_canonical_address(" ".join(str(line) for line in address_lines))
            street_match=bool(expected and ((model_street and (model_street==expected or model_street in expected or expected in model_street)) or
                (not model_street and (actual==expected or actual in expected or expected in actual))))
            city_match=not addr.get("locality") or _canonical_address(addr.get("locality"))==_canonical_address(facts.get("city"))
            state_match=not addr.get("administrativeArea") or _canonical_address(addr.get("administrativeArea"))==_canonical_address(facts.get("state"))
            identity="matched" if street_match and city_match and state_match else "quarantined"
            floors=model.get("floors") or []; rooms=model.get("rooms") or []; locations=model.get("locations") or []
            panoramas=[p for loc in locations for p in (loc.get("panos") or [])]
            # Keep a small, useful room sample in the browser dossier; counts preserve
            # the inventory without shipping every panorama reference.
            images=[]; seen_rooms=set()
            for loc in locations:
                room_id=(loc.get("room") or {}).get("id")
                if room_id in seen_rooms or len(images)>=4: continue
                for pano in loc.get("panos") or []:
                    if (pano.get("skybox") or {}).get("status") != "available": continue
                    images.append({"model_id":model_id,"location_id":loc.get("id"),"panorama_id":pano.get("id"),
                        "floor_id":(loc.get("floor") or {}).get("id"),"room_id":room_id,
                        "skybox_status":"available","capture_date":None,"retrieved_at":utcnow(),
                        "coordinate_system":"Matterport-local; API response does not declare geographic CRS"})
                    seen_rooms.add(room_id); break
            safe_model={"model_id":model_id,"name":model.get("name"),"visibility":model.get("visibility"),"state":model.get("state"),
                "created":model.get("created"),"modified":model.get("modified"),"timestamps_interpretation":"API model timestamps are not camera capture dates",
                "identity_status":identity,"identity_note":"Exact normalized street-address label match required; nearby coordinates are not used to match.",
                "floor_count":len(floors),"room_count":len(rooms),"panorama_count":len(panoramas),
                "available_panorama_count":sum((p.get("skybox") or {}).get("status")=="available" for p in panoramas),
                "rooms":[{"room_id":r.get("id"),"label":r.get("label"),"area":(r.get("dimensions") or {}).get("areaFloor"),
                           "height":(r.get("dimensions") or {}).get("height"),"unit":(r.get("dimensions") or {}).get("units"),"scope":"room"} for r in rooms],
                "images":images}
            models.append(safe_model); statuses.append("available")
            if identity=="matched" and not visual.get("observations") and os.environ.get("HELIX_STAGE2_VISION_ENABLED")=="1":
                # One frame from one explicit CoStar-linked, public Matterport model; never crawl a tour.
                candidate=next(((loc,p,p.get("skybox") or {}) for loc in locations for p in (loc.get("panos") or [])
                                if (p.get("skybox") or {}).get("status")=="available"
                                and (p.get("skybox") or {}).get("children")),None)
                if candidate:
                    loc,pano,skybox=candidate; frame=(skybox.get("children") or [None])[0]
                    try:
                        parsed_url=urlparse(frame or "")
                        if parsed_url.scheme!="https" or not (parsed_url.hostname or "").endswith("matterport.com"):
                            raise ValueError("unsupported_source_host")
                        with self.opener(Request(frame,headers={"User-Agent":"Helix Stage 2 evidence viewer"}),timeout=30) as image_response:
                            blob=image_response.read(8*1024*1024+1); content_type=image_response.headers.get("Content-Type","").split(";")[0]
                        from .vision import analyze_one_image
                        dimensions=None
                        try:
                            from PIL import Image
                            from io import BytesIO
                            with Image.open(BytesIO(blob)) as image:
                                dimensions={"width":image.width,"height":image.height}
                        except Exception:
                            pass
                        visual=analyze_one_image(blob,content_type,{"image_id":f"{model_id}:{loc.get('id')}:{pano.get('id')}:face0",
                            "model_id":model_id,"location_id":loc.get("id"),"evidence_ref":f"Matterport model {model_id} panorama {pano.get('id')} face 0",
                            "captured_at":None,"retrieved_at":utcnow()},opener=self.opener)
                        visual["image_metadata"]={"content_type":content_type,"dimensions":dimensions,"bytes":len(blob),
                            "permissions_context":model.get("visibility"),"source":"authorized CoStar-linked Matterport model"}
                    except Exception as error:
                        visual={"status":"temporarily_unavailable","error":type(error).__name__,"observations":[]}
            if identity=="matched":
                claims += [evidence_claim(claim_id=f"matterport:{model_id}:room:{r['room_id']}:area",fact="room_area",value=r["area"],unit=r["unit"],source="matterport",source_record_id=f"{model_id}:{r['room_id']}",scope_type="room",scope_id=r["room_id"],semantics="Matterport dimension estimate",observed_at=None,retrieved_at=utcnow(),evidence_ref=f"Matterport model {model_id} room {r['room_id']}",quality="model_reported",identity_key=f"costar-property:{handoff['selected_listing']['property_id']}") for r in safe_model["rooms"]]
        state= "available" if any(s=="available" for s in statuses) else (statuses[0] if statuses else "unknown")
        if len(models)>1 and sum(m["identity_status"]=="matched" for m in models)!=1:
            state="unknown"
        return {"status":state,"retrieved_at":utcnow(),"models":models,"claims":claims,"visual_analysis":visual,
                "reason":None if any(m["identity_status"]=="matched" for m in models) else "No exact-address model match; model measurements are quarantined."}


class VexcelAdapter:
    def __init__(self, opener=urlopen): self.opener=opener

    def _get(self,key,path,params):
        req=Request(VEXCEL_BASE+path+"?"+urlencode(params),headers={"X-API-KEY":key,"Accept":"application/json"})
        last=None
        for attempt in range(2):
            try:
                with self.opener(req,timeout=20) as response:
                    return response.status,json.loads(response.read())
            except HTTPError as error:
                if error.code==429 and attempt==0:
                    time.sleep(1); last=error
                    try: error.close()
                    except Exception: pass
                    continue
                raise
        raise last

    @staticmethod
    def _rings(wkt):
        if not isinstance(wkt,str): return []
        return [[(float(x),float(y)) for x,y in re.findall(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)",part)]
                for part in re.findall(r"\(([^()]+)\)",wkt)]

    @staticmethod
    def _inside(lon,lat,ring):
        inside=False
        for i in range(len(ring)-1):
            x1,y1=ring[i]; x2,y2=ring[i+1]
            if (y1>lat)!=(y2>lat) and lon < (x2-x1)*(lat-y1)/(y2-y1+1e-30)+x1: inside=not inside
        return inside

    @classmethod
    def _distance_m(cls,lon,lat,ring):
        if not ring: return float("inf")
        cx=sum(p[0] for p in ring)/len(ring); cy=sum(p[1] for p in ring)/len(ring)
        return math.hypot((lon-cx)*111320*math.cos(math.radians(lat)),(lat-cy)*111320)

    @classmethod
    def _structures_at_pin(cls, structures, lon, lat, collection, capture_date):
        candidates=[]
        for index,s in enumerate(structures or []):
            rings=cls._rings(s.get("footprint.wkt")); outer=rings[0] if rings else []
            if len(outer)<4: continue
            in_footprint=cls._inside(lon,lat,outer) and not any(cls._inside(lon,lat,hole) for hole in rings[1:])
            candidates.append((index,s,outer,in_footprint,cls._distance_m(lon,lat,outer)))
        containing=[c for c in candidates if c[3]]
        chosen=containing if containing else sorted(candidates,key=lambda c:c[4])[:1]
        result=[]
        for index,s,ring,in_pin,distance in chosen:
            sid=f"{collection}:structure:{index}"
            get=lambda key:s.get(key)
            result.append({"structure_id":sid,"collection":collection,"capture_estimate":capture_date,
                "footprint_area_sqft":get("footprint.area"),"pin_within_footprint":in_pin,
                "pin_to_footprint_centroid_distance_m":round(distance,1),
                "identity_status":"pin_within_footprint" if in_pin else "nearest_candidate_only",
                "roof_signals":{"condition_score":get("roof-characteristics.condition"),"condition_precise_value":get("roof-characteristics.condition.precise-value"),
                    "material":get("roof-characteristics.material.class"),"shape":get("roof-characteristics.shape.value"),
                    "maximum_roof_height":get("roof-characteristics.maximum-roof-height"),
                    "stories_below_eave":get("roof-characteristics.number-of-stories-below-eave")},
                "rooftop_objects":{"hvac_unit_count":get("roof-objects.ac-unit.count"),"roof_vent_count":get("roof-objects.roof-vent.count"),
                    "skylight_count":get("roof-objects.skylight.count"),"solar_panels":get("roof-objects.solar-panel-photovoltaic.count")},
                "roof_defect_signals":{"tarp_detected":get("roof-defects.tarp.detected"),
                    "discoloration_detected":get("roof-defects.discoloration.detected"),
                    "water_pooling_detected":get("roof-defects.discoloration.types.water-pooling.detected"),
                    "structural_damage_detected":get("roof-defects.structural-damage.detected")},
                "interpretation_limit":"Vexcel imagery-derived labels/signals only; not an inspection, engineering condition assessment, or safety finding."})
        return result

    def collect(self,handoff):
        facts=handoff.get("property_facts") or {}; lat=facts.get("latitude"); lon=facts.get("longitude")
        key=os.environ.get("VEXCEL_API_KEY")
        if not key:
            return {"status":"unknown","reason":"VEXCEL_API_KEY is not configured.","collections":[],"claims":[]}
        if lat is None or lon is None:
            return {"status":"unknown","reason":"Selected CoStar property coordinates are unavailable.","collections":[],"claims":[]}
        point=f"POINT({lon} {lat})"; common={"wkt":point,"srid":"4326"}; results={}; statuses=[]
        for name,path,params in (
            ("property_extract","property/extract",{**common,"layer":"urban,urban-r,wide-area,urban-g","latest":"true","include":"precomputed","unit-system":"imperial"}),
            ("oriented_coverage","oriented/collections",{**common,"layer":"urban","product-type":"oblique","include":"product-type,collection,last-capture-date"}),
            ("oriented_metadata","oriented/query",{**common,"layer":"urban","product-type":"oblique","include":"image-name,geometry,capture-date,collection,product-type,first-publish-date,last-publish-date"}),
            ("ortho_coverage","ortho/collections",{**common,"layer":"urban,urban-r,wide-area,urban-g","include":"collection,last-capture-date"}),
            ("ortho_dates","ortho/dates",{**common,"layer":"urban,urban-r,wide-area,urban-g"})):
            try:
                code,body=self._get(key,path,params)
            except HTTPError as error:
                code,_=_safe_call_error(error); body={}
            except (URLError,TimeoutError,OSError,ValueError) as error:
                code=0; body={"error_type":type(error).__name__}
            fs=body.get("features",[]) if isinstance(body,dict) else []
            state=_status(code,has_data=bool(fs) if name!="ortho_dates" else bool(body and not body.get("error")))
            statuses.append(state)
            results[name]={"status":state,"http_status":code,"retrieved_at":utcnow()}
            if name != "ortho_dates":
                results[name]["feature_count"]=len(fs)
            if name=="property_extract":
                safe=[]
                for index,f in enumerate(fs[:20]):
                    props=f.get("properties") or {}
                    safe.append({"source_record_id":f"vexcel:{props.get('metadata.collection') or 'collection'}:{index}",
                        "collection":props.get("metadata.collection"),"capture_estimate":props.get("metadata.ortho-date-estimate"),
                        "structure_count":props.get("structure.count"),"geometry_type":(f.get("geometry") or {}).get("type"),
                        "structures":props.get("structures") or []})
                results[name]["features"]=safe
            elif name in ("oriented_coverage","ortho_coverage"):
                results[name]["collections"]=[{k:(f.get("properties") or {}).get(k) for k in ("product-type","collection","last-capture-date") if (f.get("properties") or {}).get(k) is not None} for f in fs[:100]]
            elif name=="oriented_metadata":
                results[name]["images"]=[{k:(f.get("properties") or {}).get(k) for k in ("image-name","capture-date","collection","product-type","first-publish-date","last-publish-date") if (f.get("properties") or {}).get(k) is not None} for f in fs[:100]]
            elif name=="ortho_dates":
                results[name]["dates"]=body if isinstance(body,dict) else None
        useful=sum(results[n]["feature_count"] for n in ("property_extract","oriented_coverage","oriented_metadata","ortho_coverage"))
        state="available" if useful else ("unauthorized" if "unauthorized" in statuses else "not_covered" if statuses and all(s=="not_covered" for s in statuses) else "temporarily_unavailable" if "temporarily_unavailable" in statuses else "unknown")
        claims=[]
        for index,item in enumerate(results["property_extract"].get("features",[])):
            if item.get("structure_count") is not None:
                claims.append(evidence_claim(claim_id=item["source_record_id"]+":structure-count",fact="structure_count",value=item["structure_count"],unit="structures",source="vexcel",source_record_id=item["source_record_id"],scope_type="parcel_candidate",scope_id=item["collection"] or str(index),semantics="Vexcel property-extract metadata; not a CoStar building ID",observed_at=item.get("capture_estimate"),retrieved_at=utcnow(),evidence_ref=item["source_record_id"],quality="provider_reported",identity_key=f"costar-property:{handoff['selected_listing']['property_id']}"))
        # The latest capture's raw API property metadata can contain structure-level
        # footprints/roof signals. Keep the point-in-footprint match explicit.
        feature_rows=results["property_extract"].get("features",[])
        newest=max(feature_rows,key=lambda f:f.get("capture_estimate") or "") if feature_rows else None
        structures=(newest or {}).get("structures") or []
        selected_structures=self._structures_at_pin(structures,float(lon),float(lat),(newest or {}).get("collection"),(newest or {}).get("capture_estimate"))
        for structure in selected_structures:
            if structure.get("footprint_area_sqft") is not None:
                claims.append(evidence_claim(claim_id=f"vexcel:{structure['structure_id']}:footprint-area",fact="vexcel_structure_footprint_area",
                    value=structure["footprint_area_sqft"],unit="sqft",source="vexcel",source_record_id=structure["structure_id"],
                    scope_type="structure_candidate",scope_id=structure["structure_id"],semantics="ground footprint area; not gross floor area",
                    observed_at=structure.get("capture_estimate"),retrieved_at=utcnow(),evidence_ref=structure["structure_id"],quality="imagery_derived_measurement",
                    identity_key=f"costar-property:{handoff['selected_listing']['property_id']}",extra={"identity_status":structure["identity_status"],"pin_within_footprint":structure["pin_within_footprint"]}))
            for key,value in structure.get("roof_signals",{}).items():
                if value is None: continue
                claims.append(evidence_claim(claim_id=f"vexcel:{structure['structure_id']}:{key}",fact=f"vexcel_{key}",value=value,
                    unit="ft" if key=="maximum_roof_height" else None,source="vexcel",source_record_id=structure["structure_id"],
                    scope_type="structure_candidate",scope_id=structure["structure_id"],semantics="Vexcel imagery-derived attribute",
                    observed_at=structure.get("capture_estimate"),retrieved_at=utcnow(),evidence_ref=structure["structure_id"],quality="imagery_derived_signal",
                    identity_key=f"costar-property:{handoff['selected_listing']['property_id']}",extra={"structure_identity_status":structure["identity_status"],"pin_within_footprint":structure["pin_within_footprint"]}))
        for item in feature_rows:
            item["structures"]=[]  # never return full footprint geometry/property response to the browser
        results["property_extract"]["structures_at_pin"]=selected_structures
        return {"status":state,"retrieved_at":utcnow(),"coordinates_wgs84":{"latitude":lat,"longitude":lon},"operations":results,"claims":claims,
                "image_extraction":"disabled: selected-property discovery uses metadata only until extraction terms/scope are confirmed"}
