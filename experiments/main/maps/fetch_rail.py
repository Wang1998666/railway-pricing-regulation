import json,sys,time,datetime
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'reference_geometry.json').read_text(encoding='utf-8'))
for ci in ['HN','WC','JX']:
    target=ROOT/f'{ci}_rail_osm.json'
    if target.exists(): continue
    west,east,south,north=data[ci]['extent']; query=f'[out:json][timeout:30];way["railway"="rail"]["usage"="main"]({south},{west},{north},{east});out geom;'
    for endpoint in ['https://overpass.private.coffee/api/interpreter','https://overpass-api.de/api/interpreter']:
        try:
            response=requests.get(endpoint,params={'data':query},timeout=40,headers={'User-Agent':'TRA academic figure reconstruction'})
            response.raise_for_status(); payload=response.json(); assert payload.get('elements')
            payload['provenance']=dict(endpoint=endpoint,query=query,accessed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attribution='© OpenStreetMap contributors, ODbL',purpose='mapped railway geometry for geographic illustration; not train-specific paths')
            target.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8'); print(ci,len(payload['elements']),flush=True); break
        except Exception as exc: print(ci,type(exc).__name__,str(exc)[:100],flush=True)
