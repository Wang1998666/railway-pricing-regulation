import json,sys
from pathlib import Path
import fitz
from PIL import Image,ImageOps,ImageDraw
from model import ROOT,dump
sys.stdout.reconfigure(encoding='utf-8')
PDF=ROOT.parent/'TRA-20261014-V3.pdf'; output=ROOT/'preview'; output.mkdir(exist_ok=True)
doc=fitz.open(PDF); findings=[]; bad=[]
for i,p in enumerate(doc):
    text=p.get_text()
    for term in ['4. Case study','5. Discussion and conclusion','Table 5:','Table 6:','Table 7:','Table 8:','Table 9:','Table 10:']:
        if term in text: findings.append([i+1,term])
    if '??' in text: bad.append(i+1)
    pix=p.get_pixmap(matrix=fitz.Matrix(1.2,1.2)); pix.save(output/f'page_{i+1:02d}.png')
for begin in range(0,len(doc),6):
    sheet=Image.new('RGB',(1200,1720),'#eeeeee'); draw=ImageDraw.Draw(sheet)
    for j in range(6):
        n=begin+j
        if n>=len(doc): break
        im=Image.open(output/f'page_{n+1:02d}.png'); im.thumbnail((390,820)); x=(j%3)*400+(400-im.width)//2; y=(j//3)*860+25
        sheet.paste(im,(x,y)); draw.text((x,y-20),f'Page {n+1}',fill='black')
    sheet.save(output/f'contact_{begin+1:02d}.png')
report=dict(pages=len(doc),section_and_table_pages=findings,unresolved_reference_pages=bad)
dump(ROOT/'pdf_qa.json',report); print(json.dumps(report,ensure_ascii=False,indent=2))
