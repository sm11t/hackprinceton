import json, pickle, os, collections
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit'); D=os.path.dirname(os.path.abspath(__file__))
S=pickle.load(open(f'{D}/sample.pkl','rb')); ids={r['id'] for r in S}
spaces=collections.defaultdict(list)
for l in open(f'{KIT}/data/commercial-listing-summary.jsonl'):
    L=json.loads(l); f=L.get('forLeaseSummary')
    if not f or L.get('listingStatus')!=1: continue
    for sp in f.get('spaces') or []:
        if sp.get('propertyId') in ids:
            spaces[sp['propertyId']].append({k:sp.get(k) for k in ('suite','floor','floorName','squareFeetMax','availableOnDate','spaceType','dateOnMarket','isVacant','vacant','occupancyStatus','suiteName','spaceName')})
print('space keys sample:', next(iter(spaces.values()))[:1] if spaces else None)
# raw keys of one space
for l in open(f'{KIT}/data/commercial-listing-summary.jsonl'):
    L=json.loads(l); f=L.get('forLeaseSummary')
    if f and f.get('spaces'): print(sorted(f['spaces'][0].keys())); break
pickle.dump(dict(spaces),open(f'{D}/spaces.pkl','wb'))
