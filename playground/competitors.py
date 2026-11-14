"""Validate extracted operator facts against retrieved source text; compute distance in Python."""
from datetime import datetime, timezone
from math import radians, sin, cos, asin, sqrt
import re

CATEGORIES={
 'indoor pickleball':('pickleball',), 'fitness studio':('fitness','gym','pilates','yoga','personal training','strength training'),
 'warehouse / storage':('warehouse','storage'), 'flex workspace':('cowork','workspace','flex space'),
 'office / service':('office','cowork','workspace'), 'retail / showroom':('retail','showroom'),
}


def normalized(text):
    return ' '.join(str(text).casefold().split())


def distance_miles(a,b):
    lat1,lat2=radians(a['y']),radians(b['y'])
    dlat,dlon=lat2-lat1,radians(b['x']-a['x'])
    return round(3958.8*2*asin(min(1,sqrt(sin(dlat/2)**2+cos(lat1)*cos(lat2)*sin(dlon/2)**2))),2)


def validate_competitors(candidates, sources, use, city, *, origin=None, geocode=None, now=None):
    now=now or datetime.now(timezone.utc)
    lookup={r['source_id']:r for r in sources}
    accepted,rejected,seen=[],[],set()
    for candidate in candidates:
        row=dict(candidate)
        source=lookup.get(row.get('source_id'),{})
        value=source.get('value') or {}
        excerpt=normalized(value.get('excerpt',''))
        name,address,category=(normalized(row.get(k,'')) for k in ('name','address','category_excerpt'))
        reason=None
        if not name or not address or not category or any(x not in excerpt for x in (name,address,category)):
            reason='Name, address or category is not copied from the cited original page.'
        elif use=='fitness studio' and any(token in category for token in ('equipment','supplies','retail')):
            reason='Equipment retailer is not a fitness studio competitor.'
        elif not any(token in category for token in CATEGORIES.get(use,())):
            reason='Category does not match the requested use.'
        elif normalized(city) not in address or not re.search(r'\d',address):
            reason='Exact local street address is unverified.'
        try:
            observed=datetime.fromisoformat(value.get('retrieved_at','').replace('Z','+00:00'))
            if observed.tzinfo is None: observed=observed.replace(tzinfo=timezone.utc)
            if (now-observed).days > 30 or observed > now:
                reason='Source observation is stale or future-dated.'
        except ValueError:
            reason='Source observation date missing.'
        key=(re.sub(r'\W','',name),re.sub(r'\W','',address))
        if key in seen:
            reason='Duplicate operator/location.'
        if reason:
            rejected.append({'name':row.get('name'),'reason':reason}); continue
        seen.add(key)
        price=row.get('published_price')
        if price and normalized(price) not in excerpt:
            price=None
        point=None
        if geocode:
            try: point=geocode(row['address'])
            except (OSError,ValueError,KeyError,RuntimeError): pass
        distance=distance_miles(origin,point) if origin and point else None
        if distance is not None and distance>10:
            rejected.append({'name':row['name'],'reason':'Outside selected 10-mile straight-line screening radius.'});continue
        accepted.append(dict(name=row['name'],address=row['address'],use=use,source_id=row['source_id'],
             evidence_url=source.get('evidence_url'),observed_at=value['retrieved_at'],published_price=price,
             publication_date=value.get('published_at'),distance_miles=distance,
             catchment='10-mile straight-line screening radius; not driving time or a demand trade area',
             geography_status='within screening radius' if distance is not None else 'same city address; distance unverified',
             demand_verified=False))
    return {'competitors':accepted,'rejected':rejected,'demand_verified':False,
            'status':'observed competitors; paid demand unverified' if accepted else 'demand unverified',
            'limitation':'Search coverage is incomplete. Zero accepted results does not imply zero competitors. Retrieval date is not publication date; rates may have changed.'}


def census_point(address):
    from location_sources import get_json
    result=get_json('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress',
                    {'address':address,'benchmark':'Public_AR_Current','format':'json'})
    matches=result.get('result',{}).get('addressMatches',[])
    return matches[0]['coordinates'] if len(matches)==1 else None
