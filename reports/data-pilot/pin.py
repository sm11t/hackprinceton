import json, pickle, os, re, math
D=os.path.dirname(os.path.abspath(__file__))
def poly(wkt):
    nums=re.findall(r'(-?\d+\.\d+) (-?\d+\.\d+)', wkt); return [(float(a),float(b)) for a,b in nums]
def inside(pt,pg):
    x,y=pt; c=False; j=len(pg)-1
    for i in range(len(pg)):
        xi,yi=pg[i]; xj,yj=pg[j]
        if ((yi>y)!=(yj>y)) and (x<(xj-xi)*(y-yi)/(yj-yi+1e-15)+xi): c=not c
        j=i
    return c
def dist_m(pt,pg):
    cx=sum(p[0] for p in pg)/len(pg); cy=sum(p[1] for p in pg)/len(pg)
    return math.hypot((pt[0]-cx)*111320*math.cos(math.radians(pt[1])),(pt[1]-cy)*111320)
S=pickle.load(open(f'{D}/sample.pkl','rb')); out=[]
for r in S:
    vx=json.load(open(f"{D}/raw/vx_{r['id']}.json")); st=vx['features'][0]['properties'].get('structures') or []
    pt=(r['lon'],r['lat']); hit=None; how=''
    for s in st:
        if inside(pt,poly(s['footprint.wkt'])): hit=s; how='pin inside'; break
    if not hit and st:
        hit=min(st,key=lambda s:dist_m(pt,poly(s['footprint.wkt']))); how=f"nearest ({dist_m(pt,poly(hit['footprint.wkt'])):.0f} m)"
    fp=hit['footprint.area'] if hit else None
    exp=r['typ'] or ((r['gba'] or 0)/(r['stories'] or 1))
    ratio=fp/exp if fp and exp else None
    out.append((r['id'],r['type'],r['address'],r['stories'],exp,fp,ratio,how,len(st)))
    print(f"{r['id']:>9} {r['type']:<13} {str(r['address'])[:24]:<24} st={r['stories']:<3} CoStar floor={exp:>9,.0f}  Vexcel fp={fp or 0:>9,.0f}  ratio={ratio or 0:5.2f}  {how}  ({len(st)} structures)")
pickle.dump(out,open(f'{D}/pin.pkl','wb'))
rs=[o for o in out if o[6]]
print('\nwithin ±20%:',sum(1 for o in rs if 0.8<=o[6]<=1.2),'of',len(rs),'| >1.2:',sum(1 for o in rs if o[6]>1.2),'| <0.8:',sum(1 for o in rs if o[6]<0.8))
