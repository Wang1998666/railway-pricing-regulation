"""Recover the old manuscript's actual Amap vector trajectories and basemap.
No straight-line replacement is allowed. Coordinates are recovered from labeled
geographic axes in the source PDF, whose SHA-256 is recorded.
"""
import json,hashlib
from pathlib import Path
import fitz,numpy as np
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[2]/'TRA-V10'/'V1'/'Fig'/'corridor_od_trajectories.pdf'
doc=fitz.open(SOURCE); page=doc[0]; drawings=page.get_drawings(); images=page.get_images()
spans=[s for b in page.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
out={}
for ci,img in zip(['HN','WC','JX'],images):
    xref=img[0]; rect=page.get_image_rects(xref)[0]; info=doc.extract_image(xref); (ROOT/f'{ci}_basemap.{info["ext"]}').write_bytes(info['image'])
    xt=[]; yt=[]
    for span in spans:
        bbox=fitz.Rect(span['bbox']); text=span['text']
        try: value=float(text)
        except ValueError: continue
        if rect.x0-3<=bbox.x0<=rect.x1 and rect.y1<=bbox.y0<=rect.y1+15:
            pos=(bbox.x0+bbox.x1)/2
            ticks=[q[1].x for z in drawings if z['color']==(0.,0.,0.) for q in z['items'] if q[0]=='l' and abs(q[1].x-q[2].x)<.01 and 0<abs(q[1].y-q[2].y)<5 and abs(q[1].x-pos)<3 and abs(q[1].y-rect.y1)<5]
            xt.append((ticks[0] if ticks else pos,value))
        if rect.x0-32<=bbox.x0<rect.x0-2 and rect.y0<=bbox.y0<=rect.y1:
            pos=(bbox.y0+bbox.y1)/2
            ticks=[q[1].y for z in drawings if z['color']==(0.,0.,0.) for q in z['items'] if q[0]=='l' and abs(q[1].y-q[2].y)<.01 and 0<abs(q[1].x-q[2].x)<5 and abs(q[1].y-pos)<3 and abs(q[1].x-rect.x0)<5]
            yt.append((ticks[0] if ticks else pos,value))
    fx=np.polyfit(*np.array(xt).T,1); fy=np.polyfit(*np.array(yt).T,1)
    route=[]
    for draw in drawings:
        color=draw['color']
        if color and color[0]>.65 and color[1]<.4 and rect.contains(draw['rect']):
            points=[]
            for item in draw['items']:
                if item[0]=='l':
                    if not points: points.append(item[1])
                    points.append(item[2])
            if len(points)>20: route.append([[float(np.polyval(fx,p.x)),float(np.polyval(fy,p.y))] for p in points])
    assert route,ci
    nodes=[]
    for draw in drawings:
        color=draw['fill']
        if color and abs(color[0]-.10196)<.001 and rect.contains(draw['rect']) and 8<draw['rect'].width<10:
            center=(draw['rect'].tl+draw['rect'].br)/2; nodes.append([float(np.polyval(fx,center.x)),float(np.polyval(fy,center.y))])
    nodes=sorted(nodes,key=lambda p:p[1],reverse=ci in ['HN','WC'])
    names={'HN':['Nanjing','Hangzhou'],'WC':['Wuhan','Changsha'],'JX':['Ganzhou',"Ji'an",'Nanchang','Jiujiang']}[ci]
    extent=[float(np.polyval(fx,rect.x0)),float(np.polyval(fx,rect.x1)),float(np.polyval(fy,rect.y1)),float(np.polyval(fy,rect.y0))]
    out[ci]=dict(road_routes=route,cities=dict(zip(names,nodes)),extent=extent,basemap=f'{ci}_basemap.{info["ext"]}',axis_fit_error_degrees=float(max(np.max(abs(np.polyval(fx,np.array(xt)[:,0])-np.array(xt)[:,1])),np.max(abs(np.polyval(fy,np.array(yt)[:,0])-np.array(yt)[:,1])))))
out['provenance']=dict(source=str(SOURCE),sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),road_geometry='Amap route vectors from previous manuscript; illustrative geometry, not a new timetable/distance input',basemap_credit='© OpenStreetMap contributors © CARTO',coordinate_method='Affine recovery from geographic tick locations in archived vector PDF')
(ROOT/'reference_geometry.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print({ci:(len(out[ci]['road_routes']),len(out[ci]['cities'])) for ci in ['HN','WC','JX']})
