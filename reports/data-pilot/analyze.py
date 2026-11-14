import json, pickle, os, re
D=os.path.dirname(os.path.abspath(__file__)); RAW=f'{D}/raw'
S=pickle.load(open(f'{D}/sample.pkl','rb'))
def num(a):
    m=re.match(r'\s*(\d+)',a or ''); return m.group(1) if m else None
res=[]
for r in S:
    v={}; vxj=json.load(open(f"{RAW}/vx_{r['id']}.json")) if os.path.exists(f"{RAW}/vx_{r['id']}.json") else {}
    if vxj.get('features'):
        p=vxj['features'][0]['properties']; st=p.get('structures') or []
        prim=[s for s in st if s.get('primary-structure')] or st[:1]
        v=dict(n_struct=p.get('structure.count'), fp_total=sum(s.get('footprint.area') or 0 for s in st),
               fp_primary=(prim[0].get('footprint.area') if prim else None),
               stories=(prim[0].get('roof-characteristics.number-of-stories-below-eave') if prim else None),
               maxh=(prim[0].get('roof-characteristics.maximum-roof-height') if prim else None),
               vehicles=p.get('vehicles.count'), date=p.get('metadata.ortho-date-estimate'), coll=p.get('metadata.collection'),
               roof_cond=(prim[0].get('roof-characteristics.condition') if prim else None))
    else: v=dict(err=str(vxj)[:120])
    ms=[]
    for mid in r['models'][:2]:
        d=json.load(open(f"{RAW}/mp_{mid}.json"))
        m=(d or {}).get('data',{}).get('model') if d else None
        if not m: ms.append(dict(id=mid,err=str(d)[:150])); continue
        rooms=m.get('rooms') or []
        hs=[(x.get('dimensionEstimates') or {}).get('height') or 0 for x in rooms]
        labels=[x.get('label') for x in rooms if x.get('label')]
        cls=[ (x.get('classifications') or [{}])[0].get('label') for x in rooms]
        ms.append(dict(id=mid,name=m.get('name'),created=m.get('created'),area=(m.get('dimensions') or {}).get('areaFloor'),
                   floors=len(m.get('floors') or []),rooms=len(rooms),maxh=max(hs) if hs else None,
                   sweeps=len(m.get('locations') or []),labels=labels[:12],cls=sorted(set(c for c in cls if c))))
    res.append(dict(r=r,vx=v,mp=ms))
pickle.dump(res,open(f'{D}/res.pkl','wb'))
for x in res:
    r,v=x['r'],x['vx']
    print(f"\n#{r['id']} {r['type']} | {r['address']} | {r.get('name')}")
    print(f"  CoStar: GBA {r['gba']} RBA {r['rba']} stories {r['stories']} typFloor {r['typ']} height {r['height']} park {r['park']} docks {r['docks']} ceiling {r['ceiling']} | tenants now {r['cur_tenants']} ({r['cur_sf']:.0f} sf) avail {r['avail_sf']:.0f} sf listings {r['active_lease_listings']} forSale {r['for_sale']}")
    print(f"  Vexcel: {v}")
    for m in x['mp']: print(f"  MP: {m}")
