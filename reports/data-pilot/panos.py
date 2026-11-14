import json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import api
D=os.path.dirname(os.path.abspath(__file__))
targets={'S8Mbgjc2vqQ':'yorkcentre_suite159','jbR6PcGEELD':'yorkcentre_suite260','n5qk6PjJstf':'10920wsh_suite100',
 'PgqhK7kjcH6':'1400nsh_suite155','w7zyuanCUxW':'1400nsh_suite170','sM4yjPEtn6K':'sherwood_suiteC1A','MbjtAbXfCCU':'rollingcreek_16909',
 'NMFw5cNycKe':'bridgewood_suite144','2bnBGuo9TdS':'grant_suite213'}
Q='query M($id: ID!){ model(id:$id){ name locations{ id panos{ skybox(resolution:"low"){ children } } } } }'
for mid,tag in targets.items():
    s,d=api.mp(Q,{'id':mid}); locs=d['data']['model']['locations']
    picks=sorted({0,len(locs)//2,len(locs)-1})
    for i in picks:
        ch=locs[i]['panos'][0]['skybox']['children']
        for face in (1,3):
            fn=f"{D}/img/{tag}_loc{i}_f{face}.jpg"
            with urllib.request.urlopen(ch[face],timeout=60) as r: open(fn,'wb').write(r.read())
    print(tag,len(locs),'sweeps; saved',len(picks)*2)
