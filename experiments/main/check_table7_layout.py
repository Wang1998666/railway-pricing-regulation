"""Isolated layout preview using inherited values; never a final result artifact."""
import json
from pathlib import Path
from model import ROOT
from paper_helpers import panel,row,f

def main():
    out=ROOT/'layout_preview';out.mkdir(exist_ok=True)
    inherited=(ROOT.parent/'tables/v3_experiments.tex').read_text(encoding='utf-8');rows=''
    for ci in ['HN','WC','JX']:
        for cap in [1.1,1.2,1.3]:
            values=[]
            for anchor in [.6,.8,.85,.9,.95,1.]:
                found=[]
                for path in (ROOT/'runs/E16').glob(ci+'*.json'):
                    g=json.loads(path.read_text(encoding='utf-8'))
                    if abs(g['job']['anchor']-anchor)<1e-9 and abs(g['job']['cap']-cap)<1e-9:found.append(g)
                assert len(found)==1
                r=next(r for r in found[0]['records'] if r['policy']=='P3' and r['objective']=='profit');b=next(r for r in found[0]['records'] if r['policy']=='P0' and r['objective']=='profit')
                values.append(r'\shortstack{'+f((r['profit']-b['profit'])/1000)+r'\\'+f(r['welfare']/1000)+'}')
            rows+=row([ci+(r'$^{*}$' if ci!='JX' else ''),f(cap,2),*values])
    start=inherited.index(r'\par\noindent\textbf{D.');end=inherited.index(r'\par\noindent\fontsize{8}{9.5}',start)
    t=inherited[:start]+panel('D. Commercial P3: profit gain above welfare change (CNY k/day)','llrrrrrr',['Case','Cap','-0.60','-0.80','-0.85','-0.90','-0.95','-1.00'],rows)+inherited[end:]
    t=t.replace(r'\fontsize{8}{10}\selectfont',r'\fontsize{8}{9.5}\selectfont').replace(r'\renewcommand{\arraystretch}{1.08}',r'\renewcommand{\arraystretch}{1.02}')
    (out/'table7.tex').write_text(t,encoding='utf-8')
    source=r'''\documentclass[preprint]{elsarticle}
\usepackage{amsmath,amssymb,booktabs,array,caption,geometry,setspace,parskip}
\geometry{a4paper,scale=0.8}\setstretch{1.20}
\begin{document}\input{table7.tex}\clearpage\end{document}
'''
    (out/'table7_layout.tex').write_text(source,encoding='utf-8');print(out)

if __name__=='__main__':main()
