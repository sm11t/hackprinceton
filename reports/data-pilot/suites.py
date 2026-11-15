import json, pickle, os, collections, re
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit'); D=os.path.dirname(os.path.abspath(__file__))
S=pickle.load(open(f'{D}/sample.pkl','rb')); res=pickle.load(open(f'{D}/res.pkl','rb')); spaces=pickle.load(open(f'{D}/spaces.pkl','rb'))
ids={r['id'] for r in S}
cur=collections.defaultdict(list)
for l in open(f'{KIT}/data/location-occupancy.jsonl'):
    o=json.loads(l)
    if o['propertyId'] in ids and o.get('toDate') is None:
        cur[o['propertyId']].append((o.get('tenantLocationId'), sum((s.get('squareFeetOccupied') or 0) for s in o.get('spaces') or []), o.get('moveInDate')))
tl={t for v in cur.values() for t,_,_ in v if t}
comp={}
for l in open(f'{KIT}/data/company-detail.jsonl'):
    c=json.loads(l)
    if c['id'] in tl:
        a=c.get('address') or c.get('primaryAddress') or {}
        comp[c['id']]=(c.get('name') or c.get('companyName'), json.dumps(a)[:200] if not isinstance(a,dict) else (a.get('addressLine1') or a.get('streetAddress') or '')+' | '+str(a.get('addressLine2') or a.get('suite') or ''))
for x in res:
    r=x['r']; pid=r['id']
    print(f"\n#{pid} {r['type']} {r['address']} RBA {r['rba']} GBA {r['gba']}")
    print('  scans:', [m.get('name') for m in x['mp']])
    sp=spaces.get(pid,[])
    print(f"  available spaces in THIS building ({len(sp)}): total {sum(s['squareFeetMax'] or 0 for s in sp):.0f} sf;", [(s['suite'],s['floorName'],s['squareFeetMax'],(s['availableOnDate'] or '')[:10]) for s in sp][:10])
    print(f"  current tenants ({len(cur[pid])}): occ {sum(v for _,v,_ in cur[pid]):.0f} sf;", [(comp.get(t,('?',''))[0], comp.get(t,('',''))[1], v) for t,v,_ in cur[pid]][:8])
