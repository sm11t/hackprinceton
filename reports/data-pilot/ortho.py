import json, os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import api
D=os.path.dirname(os.path.abspath(__file__))
S={r['id']:r for r in pickle.load(open(f'{D}/sample.pkl','rb'))}
for pid in [237647, 9292792, 23296]:
    vx=json.load(open(f'{D}/raw/vx_{pid}.json')); f=vx['features'][0]
    g=f['geometry']; parcel=g if isinstance(g,str) else None
    if parcel is None:
        coords=g['coordinates'][0] if g['type']=='Polygon' else g['coordinates'][0][0]
        parcel='POLYGON(('+','.join(f'{x} {y}' for x,y in coords)+'))'
    draw=[{'wkt':parcel,'outline-color':'rgb(255,204,0)','outline-width':4}]
    for s in f['properties'].get('structures',[]):
        draw.append({'wkt':s['footprint.wkt'],'outline-color':'rgb(0,229,255)','outline-width':3,'label':f"{round(s['footprint.area']):,} sf",'label-color':'rgb(0,229,255)','label-size':20})
    lat,lon=S[pid]['lat'],S[pid]['lon']
    draw.append({'wkt':f'POINT({lon} {lat})','outline-color':'rgb(255,64,64)','outline-width':10,'label':'CoStar pin','label-color':'rgb(255,64,64)','label-size':20})
    st,b=api.vx_post('ortho/extract',{'wkt':parcel,'srid':4326,'layer':api.LAYERS,'buffer-meter':40,'crop':'bounding_box','image-format':'jpeg','destination-dimensions':'900,900','drawing':draw})
    print(pid,st,len(b), b[:200] if st!=200 else '')
    if st==200: open(f'{D}/sheets/aerial_{pid}.jpg','wb').write(b)
