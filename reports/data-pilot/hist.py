import os
import json, collections
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit')
focus={237647:['155','170'],239910:['144','110'],7617618:['C-1A','C1-A','C1A']}
occ=[]
for l in open(f'{KIT}/data/location-occupancy.jsonl'):
    o=json.loads(l)
    if o['propertyId'] in focus: occ.append(o)
tl={o.get('tenantLocationId') for o in occ if o.get('tenantLocationId')}
comp={}
for l in open(f'{KIT}/data/company-detail.jsonl'):
    c=json.loads(l)
    if c['id'] in tl: comp[c['id']]=(c.get('name'),c.get('suite'))
for pid,suites in focus.items():
    print(f'\n#{pid} tenancies overlapping 2024-01..2026-11 (suite, tenant, sf, from, to):')
    rows=[]
    for o in occ:
        if o['propertyId']!=pid: continue
        fr=(o.get('moveInDate') or o.get('fromDate') or '')[:10]; to=(o.get('toDate') or '')[:10] or 'current'
        if to!='current' and to<'2024-01-01': continue
        n,s=comp.get(o.get('tenantLocationId'),('unknown tenant',None))
        sf=sum((x.get('squareFeetOccupied') or 0) for x in o.get('spaces') or [])
        rows.append((str(s),n,sf,fr,to))
    for r in sorted(rows,key=lambda r:(r[0],r[3])): print('  ',r)
