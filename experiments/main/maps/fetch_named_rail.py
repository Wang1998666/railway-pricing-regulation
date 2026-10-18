import requests,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ref=json.loads((ROOT/'reference_geometry.json').read_text(encoding='utf-8'))
for ci,pattern in [('HN','宁杭|京沪|沪昆'),('WC','京广')]:
    target=ROOT/f'{ci}_rail_osm.json'
    if target.exists(): continue
    w,e,s,n=ref[ci]['extent']; query=f'[out:json][timeout:15];way["railway"="rail"]["name"~"{pattern}"]({s},{w},{n},{e});out geom;'
    endpoint='https://overpass-api.de/api/interpreter'
    try:
        r=requests.get(endpoint,params={'data':query},timeout=25); r.raise_for_status(); a=r.json(); assert a['elements']
        a['provenance']=dict(query=query,endpoint=endpoint,accessed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attribution='© OpenStreetMap contributors, ODbL',purpose='named main-line railway geometry, not train-specific itineraries')
        target.write_text(json.dumps(a,ensure_ascii=False),encoding='utf-8'); print(ci,len(a['elements']),flush=True)
    except Exception as exc: print(ci,type(exc).__name__,str(exc)[:100],flush=True)
