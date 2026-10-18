from pathlib import Path
import fitz
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent
out=Image.new('RGB',(1600,1450),'#E8EDF0');dr=ImageDraw.Draw(out)
for i,(n,name) in enumerate([(5,'round3_elasticity'),(7,'round3_attribution'),(13,'round6_frontier'),(17,'round3_calibration_dependence')]):
    d=fitz.open(P.parent/'main_figures'/f'{name}.pdf');pix=d[0].get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False)
    im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((770,680))
    out.paste(im,((i%2)*800+(800-im.width)//2,(i//2)*725+30));dr.text(((i%2)*800+10,(i//2)*725+8),f'Figure {n}',fill='black')
out.save(P/'本轮原图核对.png')
