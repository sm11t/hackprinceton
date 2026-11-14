import json, pickle, os, collections
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit'); D=os.path.dirname(os.path.abspath(__file__))
focus=[237647,239910,239914,686041,7617618,721925,238105,9292792,240723,9594573,23296,233927,239686,1176444,13890701,10878589]
cur=collections.defaultdict(list); past=collections.defaultdict(list)
for l in open(f'{KIT}/data/location-occupancy.jsonl'):
    o=json.loads(l)
    if o['propertyId'] in focus:
        sf=sum((s.get('squareFeetOccupied') or 0) for s in o.get('spaces') or [])
        (cur if o.get('toDate') is None else past)[o['propertyId']].append((o.get('tenantLocationId'),sf,(o.get('moveInDate') or o.get('fromDate') or '')[:10],(o.get('toDate') or '')[:10]))
tl={t for d in (cur,past) for v in d.values() for t,*_ in v if t}
comp={}
for l in open(f'{KIT}/data/company-detail.jsonl'):
    c=json.loads(l)
    if c['id'] in tl:
        a=c.get('address') or {}; comp[c['id']]=(c.get('name'),c.get('suite'),f"{a.get('streetNumber')} {a.get('streetName')}")
props={}
for l in open(f'{KIT}/data/commercial-property.jsonl'):
    p=json.loads(l)
    if p['id'] in focus:
        pa=p.get('primaryAddress') or {}
        props[p['id']]=dict(primary=f"{pa.get('streetNumber')} {pa.get('streetName')}", others=[f"{a.get('streetNumber')} {a.get('streetName')}" for a in (p.get('addresses') or [])][:8], park=p.get('buildingPark'), keys=[k for k in p.keys() if 'ddress' in k])
for pid in focus:
    print(f"\n#{pid} {props[pid]}")
    print('  CURRENT:', [(comp.get(t,('?',None,''))[0], comp.get(t,('',None,''))[1], comp.get(t,('','',''))[2], sf, mi) for t,sf,mi,_ in cur[pid]])
    pp=sorted(past[pid],key=lambda x:x[3],reverse=True)[:6]
    print('  RECENT PAST:', [(comp.get(t,('?',None,''))[0], comp.get(t,('',None,''))[1], sf, out) for t,sf,_,out in pp])
