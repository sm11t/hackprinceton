"""Collect scoped source records for the location and demand run."""
from datetime import datetime, timezone
import json
import os
import re
from urllib.parse import urlencode, urlsplit
from zipfile import ZipFile

from probe import VEXCEL, load_property, matterport_model, request


def select(record, *fields):
    return {field: record[field] for field in fields if record.get(field) is not None}


def get_json(endpoint, params=None, *, headers=None, body=None):
    url = endpoint + ("?" + urlencode(params) if params else "")
    return json.loads(request(url, headers or {}, body))


def record(source, source_id, scope, value, url=None, captured_at=None, note=""):
    return {
        "fact": scope,
        "value": value,
        "source": source,
        "source_id": source_id,
        "captured_at": captured_at,
        "confidence": None,
        "evidence_url": url,
        "status": "unknown" if value is None else "agrees",
        "needs_human": value is None,
        "note": note,
    }


def collect_property(kit, property_id):
    password = os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None
    prop, mapping = load_property(kit, property_id, password, require_model=False)
    pin = prop["primaryAddress"]
    postal_code = str(pin.get("postcode") or "")[:5]
    address = f'{mapping[0]["Address"]}, {pin["city"]}, {pin["state"]} {postal_code}'.strip()
    records = [record("costar", f"property-{property_id}", "Building record", select(
        prop, "id", "buildingName", "propertyType", "parcelNumbers", "parcelReferences",
        "grossBuildingAreaSquareFeet", "rentableBuildingAreaSquareFeet",
        "grossTypicalFloorSquareFeet", "numStoriesAboveGrade", "parking", "parkingRatio",
        "zoningDescription", "propertyFlex", "propertyIndustrial", "hasSprinklers", "environmental", "amenities",
        "yearBuilt", "yearRenovated", "primaryAddress", "constructionType", "propertyRetail", "propertyOffice",
    ), note="Building-level inventory. Recorded zoning requires jurisdictional verification.")]
    with ZipFile(kit) as archive:
        for dataset in ("commercial-listing-summary", "location-occupancy", "commercial-sale-comp"):
            with archive.open(f"data/{dataset}.jsonl", pwd=password) as stream:
                for line in stream:
                    row = json.loads(line)
                    if dataset == "commercial-sale-comp":
                        matched = any(e.get("propertyId") == property_id for e in row.get("entities") or [])
                        value = select(row, "soldDate", "soldForPrice", "salePriceStatus", "saleType", "monetaryUnit")
                    elif dataset == "location-occupancy":
                        matched = row.get("propertyId") == property_id
                        value = select(row, "fromDate", "moveInDate", "moveOutDate", "toDate", "industryType", "tenantName", "name", "spaces")
                    else:
                        matched = row.get("propertyId") == property_id
                        value = select(row, "listingStatus", "listingType", "certifiedFreshDate")
                        lease = row.get("forLeaseSummary") or {}
                        value["lease"] = select(lease, "askingRateBasis", "askingRateLow", "askingRateHigh",
                                                "askingRateMeasurementType", "serviceType",
                                                "totalAvailableSquareFeet", "minDateOnMarket")
                        value["spaces"] = [
                            select(s, "id", "spaceId", "suite", "suiteNumber", "floorNumber", "availableSquareFeet",
                                   "spaceType", "minDivisibleSquareFeet", "maxContiguousSquareFeet",
                                   "availableDate", "askingRateLow", "askingRateHigh", "askingRateBasis")
                            for s in lease.get("spaces") or []
                        ]
                    if matched:
                        records.append(record("costar", f'{dataset}-{row["id"]}', dataset, value,
                                              captured_at=row.get("certifiedFreshDate") or row.get("soldDate"),
                                              note="Dated sponsor record. Confirm current status and exact suite separately."))
    for scan_id in dict.fromkeys(m["MatterportModelId"] for m in mapping if m["MatterportModelId"]):
        url = f"https://my.matterport.com/show/?m={scan_id}"
        attachment = next((a for a in prop.get("attachments") or []
                           if a.get("videoKey") == scan_id or scan_id in (a.get("attachmentUri") or "")), {})
        try:
            scan = matterport_model(scan_id)
            rooms = []
            for floor in scan.get("floors") or []:
                for room in floor.get("rooms") or []:
                    dimensions = room.get("dimensionEstimates") or {}
                    rooms.append({"floor": floor.get("label"), "room": room.get("label"),
                                  "area_m2": dimensions.get("area"),
                                  "estimated_height_m": dimensions.get("height") or None})
            value = {"model_name": scan.get("name"), "rooms": rooms}
        except (KeyError, ValueError, OSError, RuntimeError):
            value = None
        scan_record = record("matterport", f"scan-{scan_id}", "Linked scan",
                             value, url, attachment.get("originationDate"),
                             "Scan-to-suite match unresolved. Preserve labels and room scope; zero height is unknown.")
        scan_record["status"] = "unknown"
        scan_record["needs_human"] = True
        records.append(scan_record)

    endpoint = f"{VEXCEL}/structure/extract"
    try:
        structures = get_json(endpoint, {
            "wkt": f'POINT({pin["longitude"]} {pin["latitude"]})',
            "srid": 4326, "metadata-format": "json",
        }, headers={"X-API-KEY": os.environ["VEXCEL_API_KEY"]})
        primary = [f["properties"] for f in structures["features"] if f["properties"].get("primary-structure")]
        structure = primary[0] if len(primary) == 1 else {}
    except (KeyError, ValueError, OSError, RuntimeError):
        structure = {}
    value = select(structure, "footprint.area", "roof-characteristics.condition",
                   "roof-characteristics.material.class", "roof-characteristics.shape.value",
                   "roof-objects.ac-unit.count", "roof-objects.solar-panel.count", "roof-defects",
                   "vehicle.count", "metadata.collection")
    records.append(record("vexcel", f"structure-at-{property_id}", "Primary structure at CoStar pin",
                          value or None, endpoint, structure.get("metadata.ortho-date-estimate"),
                          "Imagery date is estimated. Footprint is in square meters; roof observations are vendor detections."))
    return address, records


def collect_official(address):
    geocoder = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
    fema = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
    acs = "https://api.census.gov/data/2024/acs/acs5"
    census = None
    try:
        result = get_json(geocoder, {"address": address, "benchmark": "Public_AR_Current",
                                     "vintage": "Current_Current", "format": "json"})
        matches = result["result"]["addressMatches"]
        if len(matches) == 1:
            match = matches[0]
            tracts = match["geographies"].get("Census Tracts", [])
            if len(tracts) == 1:
                census = (match, tracts[0])
    except (KeyError, ValueError, OSError, RuntimeError):
        pass
    if not census:
        return [record("public:census", "census-geocode", "Address geocode and Census tract",
                       None, geocoder, note="No unique tract match. FEMA and ACS need a verified geography.")]
    match, tract = census
    coords = match["coordinates"]
    records = [record("public:census", "census-geocode", "Address geocode and Census tract",
                      {"address": match["matchedAddress"], "point": coords, "tract": tract["GEOID"]},
                      geocoder, note="Census address point. Municipal jurisdiction requires a separate boundary lookup.")]
    try:
        result = get_json(fema, {"f": "json", "geometry": f'{coords["x"]},{coords["y"]}',
                                "geometryType": "esriGeometryPoint", "inSR": 4326,
                                "spatialRel": "esriSpatialRelIntersects", "returnGeometry": "false",
                                "outFields": "FLD_ZONE,ZONE_SUBTY"})
        zones = [f["attributes"] for f in result["features"]]
    except (KeyError, ValueError, OSError, RuntimeError):
        zones = []
    records.append(record("public:fema", "fema-effective-zone", "Effective flood map at geocoded point",
                          zones or None, fema, note="Mapped exposure at the queried point. Property flood history is unknown."))
    population = None
    acs_gap = "Census API key is missing."
    key = os.environ.get("CENSUS_API_KEY")
    if key:
        acs_gap = "The ACS lookup failed. Check key activation and request availability."
        try:
            fields = "NAME,B01003_001E,B01003_001M,B11001_001E,B11001_001M,B19013_001E,B19013_001M"
            rows = get_json(acs, {"get": fields, "for": f'tract:{tract["TRACT"]}',
                                  "in": f'state:{tract["STATE"]} county:{tract["COUNTY"]}', "key": key})
            population = {field: (int(value) if int(value) >= 0 else None)
                          for field, value in zip(rows[0], rows[1])
                          if field.startswith("B") and value is not None}
        except (IndexError, KeyError, TypeError, ValueError, OSError, RuntimeError):
            pass
    records.append(record("public:acs", "acs-2024-tract", "2020–2024 ACS five-year tract estimates",
                          population, acs, note=("Population, households and median household income estimates "
                                                "with margins of error. Tract context only."
                                                if population else acs_gap)))
    return records


def market_sources(city, use):
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return [record("public:web", "market-unavailable", "Market search", None,
                       note="Tavily credentials are unavailable.")]
    headers = {"Authorization": f"Bearer {key}"}
    # Search category + market, then calculate actual proximity. The exact subject
    # street address dominated search and returned unrelated tenants on that road.
    area = ', '.join(city.split(',')[-2:]).strip()
    term = {'indoor pickleball':'indoor pickleball courts', 'fitness studio':'gym fitness classes',
            'warehouse / storage':'self storage warehouse', 'flex workspace':'coworking flex workspace',
            'office / service':'serviced office coworking', 'retail / showroom':'retail showroom'}.get(use,use)
    try:
        search = get_json("https://api.tavily.com/search", headers=headers, body={
            "query": f"{term} {area} official locations address membership -equipment -supplies",
            "max_results": 8, "include_answer": False, "auto_parameters": False,
        })
        urls = list(dict.fromkeys(item["url"] for item in search["results"]
                                  if urlsplit(item["url"]).scheme == "https"
                                  and not any(domain in (urlsplit(item['url']).hostname or '')
                                              for domain in ('yahoo.com','fresha.com','yelp.com','facebook.com','instagram.com','mapquest.com','compass.com','loopnet.com'))))[:4]
        if not urls:
            raise ValueError("No eligible search results")
        extracts = get_json("https://api.tavily.com/extract", headers=headers, body={"urls": urls})
        retrieved = datetime.now(timezone.utc).isoformat()
        records = [
            record("public:web", f"market-page-{i}", "Public operator research candidate",
                   {"excerpt": re.sub(r"!\[[^\]]*\]\([^)]*\)", "", item["raw_content"])[:12000], "retrieved_at": retrieved},
                   item["url"], note="Confirm operator identity and exact location. Retrieval date is not publication date.")
            for i, item in enumerate(extracts["results"], 1)
            if item.get("raw_content") and item.get("url") in urls
        ]
        if records:
            return records
    except (KeyError, ValueError, OSError, RuntimeError):
        pass
    return [record("public:web", "market-unavailable", "Market search", None,
                   note="Search or page extraction returned no usable sources.")]
