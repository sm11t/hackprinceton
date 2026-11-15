import os
import json, re, collections
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit')
num=re.compile(r'\b(\d{3,6})\s+(?:[NSEW]\.?\s+)?([A-Za-z][A-Za-z]+)')
stats=collections.Counter(); examples=[]
for l in open(f'{KIT}/data/commercial-property.jsonl'):
    p=json.loads(l)
    nums={str(a.get('streetNumber') or '').split('-')[0] for a in [p.get('primaryAddress') or {}]+(p.get('addresses') or [])}
    rng=set()
    for a in [p.get('primaryAddress') or {}]+(p.get('addresses') or []):
        sn=str(a.get('streetNumber') or '')
        m=re.match(r'(\d+)\s*-\s*(\d+)',sn)
        if m: rng.add((int(m.group(1)),int(m.group(2))))
        for k in ('addressLine1','streetAddress'):
            mm=re.match(r'(\d+)(?:\s*-\s*(\d+))?',str(a.get(k) or ''))
            if mm:
                nums.add(mm.group(1))
                if mm.group(2): rng.add((int(mm.group(1)),int(mm.group(2))))
    streets={str(a.get('streetName') or '').lower() for a in [p.get('primaryAddress') or {}]+(p.get('addresses') or [])}
    seen=set()
    for a in p.get('attachments') or []:
        if a.get('videoExternalReferenceType') not in (36,234) or a.get('videoKey') in seen: continue
        seen.add(a.get('videoKey')); stats['scans']+=1
        cap=a.get('caption') or ''
        m=num.search(cap)
        if not m: continue
        n,st=m.group(1),m.group(2).lower()
        if st not in streets: continue   # only compare when caption names the SAME street
        stats['scans_with_same_street_address']+=1
        inr=any(lo<=int(n)<=hi for lo,hi in rng)
        if n not in nums and not inr:
            stats['different_number_same_street']+=1
            if len(examples)<15: examples.append((p['id'],(p.get('primaryAddress') or {}).get('streetNumber'),(p.get('primaryAddress') or {}).get('streetName'),cap[:70]))
print(dict(stats));
for e in examples: print(e)
