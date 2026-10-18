import json,re,hashlib,sys
from pathlib import Path
import fitz
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;P=HERE.parent;sys.path.insert(0,str(P/'main'))
from model import dump
doc=fitz.open(P/'TRA-20261014-V3.pdf');out=HERE/'preview';out.mkdir(exist_ok=True);findings=[]
for i,p in enumerate(doc):
    text=p.get_text();assert '??' not in text,(i+1,'unresolved reference')
    terms=[s for s in ['4. Case study','5. Discussion and conclusion','Computations run','cap–floor grid','Figure 17:','Table 9:','Table 10:','Table 11:','Data and code availability'] if s in text]
    if terms:findings.append(dict(page=i+1,terms=terms))
    p.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(out/f'page_{i+1:02d}.png')
for begin in range(0,len(doc),6):
    sheet=Image.new('RGB',(1200,1720),'#eeeeee');draw=ImageDraw.Draw(sheet)
    for j in range(6):
        n=begin+j
        if n>=len(doc):break
        im=Image.open(out/f'page_{n+1:02d}.png');im.thumbnail((390,820));x=(j%3)*400+(400-im.width)//2;y=(j//3)*860+25;sheet.paste(im,(x,y));draw.text((x,y-20),f'Page {n+1}',fill='black')
    sheet.save(out/f'contact_{begin+1:02d}.png')
t=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8');old=(P/'archive/before_round6_20261015/TRA-20261014-V3.tex').read_text(encoding='utf-8')
start=r'\section{Literature review}';end=r'\section{Case study}'
assert t[t.index(start):t.index(end)]==old[old.index(start):old.index(end)]
protected={name:hashlib.sha256((P/'Fig'/name).read_bytes()).hexdigest() for name in ['case_fig03.pdf','case_fig05.pdf','case_fig05.tex','round3_calibration.pdf']}
assert protected['case_fig03.pdf']=='caaf675da9225c98e7c17a730fbd08e23172b30646dc743a00fd9ae7ebb982c9'
assert protected['case_fig05.pdf']=='d9f0f6d91bcc2a68a7116d844cecf561ce0bea544a174b655a3e5cb3149df3b2'
assert protected['case_fig05.tex']=='15536f8a54372c168012d8eea034534d77db25dd35d82c5f4c3fb4698bc662bc'
case=t[t.index(end):];assert not re.search(r'\\begin\{(?:equation|longtable|align)\}',case)
ledger=list(__import__('csv').DictReader((HERE/'reported_open_scope.csv').open(encoding='utf-8')))
assert len({(r['state'],r['policy'],r['objective']) for r in ledger})==63
log=(P/'TRA-20261014-V3.log').read_text(encoding='utf-8',errors='replace');over=re.findall(r'Overfull[^\n]*(?:\n[^\n]*)?',log)
assert len(over)<=2,over
dump(HERE/'pdf_qa.json',dict(pages=len(doc),locations=findings,pdf_sha256=hashlib.sha256((P/'TRA-20261014-V3.pdf').read_bytes()).hexdigest(),protected_sha256=protected,sections_2_3_unchanged=True,unresolved_references=False,case_numbered_equations=False,longtable=False,overfull_warnings=over,open_scope_complete=True))
print(json.dumps(dict(pages=len(doc),locations=findings,overfull_warning_count=len(over)),indent=2))
