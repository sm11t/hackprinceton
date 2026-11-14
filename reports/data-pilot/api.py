import json, os, base64, time, urllib.request, urllib.parse, urllib.error
VX="https://api.vexcelgroup.com/v2"; MP="https://api.matterport.com/api/models/graph"
LAYERS="urban,urban-r,wide-area,urban-g"
def _req(url, headers, body=None, method=None, timeout=120):
    data=None
    if body is not None:
        headers={**headers,"Content-Type":"application/json"}; data=json.dumps(body).encode()
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers,method=method),timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(2**attempt); continue
            return e.code, e.read()
    return 429, b''
def vx_get(path, **params):
    return _req(f"{VX}/{path}?"+urllib.parse.urlencode(params), {"X-API-KEY":os.environ["VEXCEL_API_KEY"]})
def vx_post(path, body):
    return _req(f"{VX}/{path}", {"X-API-KEY":os.environ["VEXCEL_API_KEY"]}, body)
def mp(query, variables):
    auth=base64.b64encode(f"{os.environ['MATTERPORT_API_KEY']}:{os.environ['MATTERPORT_API_TOKEN']}".encode()).decode()
    s,b=_req(MP,{"Authorization":f"Basic {auth}"},{"query":query,"variables":variables})
    return s, json.loads(b) if b else None
