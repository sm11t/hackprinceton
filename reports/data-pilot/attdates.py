import os
import json
KIT=os.environ.get('COSTAR_KIT_DIR', 'costar-hackathon-kit')
want={'S8Mbgjc2vqQ':239914,'jbR6PcGEELD':239914,'n5qk6PjJstf':686041,'PgqhK7kjcH6':237647,'w7zyuanCUxW':237647,'sM4yjPEtn6K':7617618,'MbjtAbXfCCU':9594573,'NMFw5cNycKe':239910,'2bnBGuo9TdS':9292792,'oNAvrNiXZS7':23296}
pids=set(want.values()); shown=False
for src in ['commercial-property','commercial-listing-summary']:
    for l in open(f'{KIT}/data/{src}.jsonl'):
        r=json.loads(l); pid=r['id'] if src=='commercial-property' else r.get('propertyId')
        if pid not in pids: continue
        for a in r.get('attachments') or []:
            if a.get('videoKey') in want:
                if not shown: print('ATTACHMENT KEYS:',sorted(a.keys())); shown=True
                print(src, pid, a['videoKey'], {k:v for k,v in a.items() if any(s in k.lower() for s in ('date','time','created','modified','year','caption','description','name','title'))})
