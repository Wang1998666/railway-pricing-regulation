from pathlib import Path
import fitz
from PIL import Image, ImageOps, ImageDraw
P=Path(__file__).resolve().parent
names=['calibration','fares_headroom','od_arcs','shocks','polarization','entries','guarantees','equity','governance']
sheet=Image.new('RGB',(1500,1500),'#e8ebee')
for i,n in enumerate(names):
    doc=fitz.open(P.parent/'main_figures'/f'round3_{n}.pdf')
    pix=doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
    im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    im.thumbnail((480,450))
    x=(i%3)*500+(500-im.width)//2;y=(i//3)*500+30
    sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text(((i%3)*500+10,(i//3)*500+8),n,fill='black')
sheet.save(P/'original_contact.png')
