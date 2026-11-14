import os
import json, csv, collections, sys, pickle
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit')
E=json.load(open(f'{KIT}/schemas/enums.json'))
PT=E['PropertyType']
models=collections.defaultdict(list)
for r in csv.DictReader(open(f'{KIT}/commercial-properties.csv',encoding='utf-8-sig')):
    if r['MatterportModelId']: models[int(r['PropertyId'])].append(r['MatterportModelId'])
rows=[]
for line in open(f'{KIT}/data/commercial-property.jsonl'):
    p=json.loads(line)
    a=p.get('primaryAddress') or {}
    sub=p.get('propertyIndustrial') or p.get('propertyFlex') or p.get('propertyOffice') or p.get('propertyRetail') or {}
    st=(sub or {}).get('structural') or {}
    park=sum((x.get('totalSpaces') or 0) for x in p.get('parking') or [])
    yb=[e['year'] for e in p.get('constructionEvents') or [] if e.get('eventType')==1]
    rows.append(dict(id=p['id'],type=PT.get(str(p.get('propertyType')),p.get('propertyType')),
      market=a.get('researchMarketId'),addr=a.get('addressLine1') or a.get('streetAddress'),city=a.get('city'),
      lat=a.get('latitude'),lon=a.get('longitude'),
      gba=p.get('grossBuildingAreaSquareFeet'),rba=p.get('rentableBuildingAreaSquareFeet'),
      stories=p.get('numStoriesAboveGrade'),typ=p.get('grossTypicalFloorSquareFeet'),height=p.get('buildingHeightInFeet'),
      park=park or None,ratio=p.get('parkingRatio'),lot=p.get('lotSize'),lotunit=p.get('lotSizeMeasurementType'),
      yearbuilt=yb[0] if yb else None,
      docks=((sub or {}).get('numExternalLoadingDocks') or 0)+((sub or {}).get('numInternalLoadingDocks') or 0) or None,
      ceiling=st.get('ceilingHeightFeet'),sprink=p.get('hasSprinklers'),amen=p.get('amenities') or [],
      floors=len(p.get('floors') or []),nmodels=len(models.get(p['id'],[])),models=models.get(p['id'],[]),
      name=p.get('buildingName')))
pickle.dump(rows,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'props.pkl'),'wb'))
c=collections.Counter((r['market'],r['type']) for r in rows)
for k,v in sorted(c.items(),key=lambda x:-x[1]): print(k,v)
H=[r for r in rows if r['market']==14 and r['type']!='Multifamily' and r['nmodels']]
print('Houston non-MF with models',len(H))
for f in ['gba','rba','stories','typ','height','park','ratio','lot','yearbuilt','docks','ceiling','sprink']:
    print(f, sum(1 for r in H if r[f] not in (None,0)))
print(list(rows[0].keys()))
print(sample:=[ (r['id'],r['type'],r['addr'],r['gba'],r['stories'],r['typ'],r['park'],r['ceiling'],r['docks'],r['nmodels']) for r in H][:40])
