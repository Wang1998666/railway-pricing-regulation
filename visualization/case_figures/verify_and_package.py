"""Package final chart PDFs and audit integration, fonts, and numerical invariants."""
from pathlib import Path
import json,re,hashlib,datetime
import fitz
P=Path(__file__).resolve().parent
M=json.loads((P/'manifest.json').read_text(encoding='utf-8'))
tex=P.parent/'TRA-20261014-V3.tex';backup=P.parent/'TRA-20261014-V3.backup-20261016-095232.tex'
current=tex.read_text(encoding='utf-8');before=backup.read_text(encoding='utf-8')
def stripfig(t):return re.sub(r'\\begin\{figure\}.*?\\end\{figure\}','',t,flags=re.S)
assert stripfig(current)==stripfig(before),'Unexpected changes outside figure environments'
newpaths=re.findall(r'\\includegraphics[^\n]*?\{(新成的图/[^}]+)\}',current)
assert len(newpaths)==14
for s in newpaths:assert (P.parent/s).exists()
oldpaths=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',before)
samepaths=[s for s in oldpaths if s in current]
assert len(oldpaths)==17 and len(samepaths)==3
hashes={}
for path in sorted((P.parent/'main_figures').glob('*')):
    if path.is_file():hashes[str(path.relative_to(P.parent))]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mtime':path.stat().st_mtime}
assert all(v['mtime']<backup.stat().st_mtime for v in hashes.values()),'Original figures were modified after backup'
font_audit={};out=fitz.open()
for n in range(4,18):
    f=P/M[str(n)]['pdf'];d=fitz.open(f);assert len(d)==1
    fonts=sorted({x[3] for x in d[0].get_fonts()});font_audit[str(n)]=fonts
    assert any('Arial' in s for s in fonts),f'Arial absent in Figure {n}'
    assert not any('Times' in s or 'DejaVu' in s or 'ztm' in s for s in fonts),f'Unexpected text font in Figure {n}'
    if n!=6:
        assert abs(d[0].rect.width-612)<.05,(n,'Nonuniform canvas width')
        for t in M[str(n)]['panel_titles']:
            assert t['size']==10 and t['color']=='#263C4A' and t['weight']=='bold' and t['family']==['Arial'],(n,'Nonuniform panel title',t)
    rect=d[0].rect
    for b in d[0].get_text('dict')['blocks']:
        if 'lines' not in b:continue
        for l in b['lines']:
            for s in l['spans']:
                assert rect.contains(fitz.Rect(s['bbox'])),(n,'clipped text',s['text'])
    out.insert_pdf(d)
out.save(P/'新版案例研究图合集.pdf',garbage=4,deflate=True)
# Exact library counts independently computed from archived physical decisions.
rows=[r for r in json.loads((P.parents[1]/'experiments'/'main'/'equity_unique.json').read_text(encoding='utf-8')) if r['feasible']]
ll=sum(r['dG']< -1e-7 and r['deta']< -1e-7 for r in rows)
assert len(rows)==1842 and ll==341
# Caption figure numbers and source records remain consistent with the paper.
departures={};loss={}
for ci,targetN,targetLoss in [('HN',147,-398.9),('WC',185,-709.7),('JX',190,-941.2)]:
    g=json.loads((P.parents[1]/'experiments'/'main'/f'runs/E2/{ci}_reference_none.json').read_text(encoding='utf-8'))
    get=lambda p:next(r for r in g['records'] if r['policy']==p and r['objective']=='profit')
    r=get('P0');departures[ci]=sum(sum(a) for a in r['N']);loss[ci]=get('P3')['welfare']/1000
    assert departures[ci]==targetN and abs(loss[ci]-targetLoss)<.1
report={'changed_figures':list(range(4,18)),'preserved_figures':[1,2,3],
 'nonfigure_tex_unchanged':True,'new_asset_paths':newpaths,'fonts':font_audit,
 'equity':{'total':len(rows),'lower_left':ll},'reference_departures':departures,'P3_welfare_CNY_k':loss,
 'original_figure_hashes':hashes}
(P/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['original_figure_hashes','new_asset_paths']},ensure_ascii=False,indent=2))
doc=fitz.open(P.parent/'TRA-20261014-V3.pdf');qa=P/'论文插图排版核查';qa.mkdir(exist_ok=True)
pageids=[]
for i,page in enumerate(doc):
    t=page.get_text()
    if any(re.search(r'Figure\s+'+str(n)+r'\s*:',t) for n in range(4,18)):
        page.get_pixmap(matrix=fitz.Matrix(1.35,1.35),alpha=False).save(qa/f'page_{i+1:02d}.png');pageids.append(i+1)
print('Rendered paper pages:',pageids)
