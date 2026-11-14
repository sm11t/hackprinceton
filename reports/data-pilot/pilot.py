import json, csv, pickle, random, sys, os, re, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__)); import api
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit'); OUT=os.path.join(os.path.dirname(__file__),'raw'); os.makedirs(OUT,exist_ok=True)
rows=pickle.load(open(os.path.join(os.path.dirname(__file__),'props.pkl'),'rb'))
addr={}
for r in csv.DictReader(open(f'{KIT}/commercial-properties.csv',encoding='utf-8-sig')): addr[int(r['PropertyId'])]=r['Address']
H=[r for r in rows if r['market']==14 and r['type']!='Multifamily' and r['nmodels'] and r['lat']]
random.seed(7)
def pick(t,n,cond=lambda r:True):
    c=[r for r in H if r['type']==t and cond(r)]; random.shuffle(c); return c[:n]
sample=([r for r in H if r['id']==23296]+pick('Industrial',6,lambda r:r['id']!=23296)+pick('Flex',4,lambda r:r['id']!=23296)
        +pick('Office',6,lambda r:(r['stories'] or 0)<=4)+pick('Office',5,lambda r:(r['stories'] or 0)>4)
        +pick('GeneralRetail',4)+pick('Hospitality',3))
ids={r['id'] for r in sample}
# CoStar occupancy + listings
occ={i:{'cur_tenants':0,'cur_sf':0.0,'past_tenants':0,'latest_move':None,'latest_out':None} for i in ids}
for l in open(f'{KIT}/data/location-occupancy.jsonl'):
    if '"propertyId": ' not in l: pass
    o=json.loads(l); pid=o['propertyId']
    if pid not in ids: continue
    sf=sum((s.get('squareFeetOccupied') or 0) for s in o.get('spaces') or [])
    if o.get('toDate') is None:
        occ[pid]['cur_tenants']+=1; occ[pid]['cur_sf']+=sf
        mi=o.get('moveInDate') or o.get('fromDate')
        if mi and (occ[pid]['latest_move'] or '')<mi: occ[pid]['latest_move']=mi
    else:
        occ[pid]['past_tenants']+=1
        if (occ[pid]['latest_out'] or '')<o['toDate']: occ[pid]['latest_out']=o['toDate']
avail={i:{'active_lease_listings':0,'avail_sf':0.0,'for_sale':False} for i in ids}
for l in open(f'{KIT}/data/commercial-listing-summary.jsonl'):
    L=json.loads(l); pid=L.get('propertyId')
    if pid not in ids or L.get('listingStatus')!=1: continue
    if L.get('forLeaseSummary'):
        avail[pid]['active_lease_listings']+=1; avail[pid]['avail_sf']+=L['forLeaseSummary'].get('totalAvailableSquareFeet') or 0
    if L.get('forSaleSummary'): avail[pid]['for_sale']=True
MPQ='''query M($id: ID!){ model(id:$id){ id name created
 dimensions(units: imperial){ areaFloor volume }
 floors{ id label sequence dimensions(units: imperial){ areaFloor } }
 rooms{ id label classifications{ label confidence } dimensionEstimates(units: imperial){ area height } }
 locations{ id floor{id} room{id} panos{ id skybox(resolution:"low"){ children } } } }}'''
def vexcel(r):
    s,b=api.vx_get('property/extract', wkt=f"POINT({r['lon']} {r['lat']})", srid=4326, layer=api.LAYERS, latest='true', include='precomputed', **{'unit-system':'imperial'})
    open(f"{OUT}/vx_{r['id']}.json",'wb').write(b); return s
def matterport(mid):
    s,d=api.mp(MPQ,{'id':mid}); json.dump(d,open(f"{OUT}/mp_{mid}.json",'w')); return s
jobs=[]
with cf.ThreadPoolExecutor(6) as ex:
    for r in sample:
        jobs.append(('vx',r['id'],ex.submit(vexcel,r)))
        for m in r['models'][:2]: jobs.append(('mp',m,ex.submit(matterport,m)))
    for k,i,f in jobs:
        try: st=f.result()
        except Exception as e: st=repr(e)
        if st!=200: print('ERR',k,i,st)
for r in sample: r['address']=addr.get(r['id']); r.update(occ[r['id']]); r.update(avail[r['id']])
pickle.dump(sample,open(os.path.join(os.path.dirname(__file__),'sample.pkl'),'wb'))
print(len(sample),'properties;',sum(min(2,len(r['models'])) for r in sample),'models')
