"""LaTeX helpers using ordinary, consistent 95-percent-width tables."""
import re
from model import ROOT
P=ROOT.parent
def f(x,d=1):return f'{0 if abs(x)<.5*10**(-d) else x:,.{d}f}'
def row(x):return ' & '.join(map(str,x))+r' \\'+'\n'
def panel(title,cols,header,body):
    cols=re.sub(r'p\{([^}]+)\}',lambda m:r'>{\raggedright\arraybackslash}p{'+m[1]+'}',cols)
    return r'\par\noindent\textbf{'+title+r'}\par\smallskip'+'\n'+r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}'+cols+r'@{}}\toprule'+'\n'+row(header)+r'\midrule'+'\n'+body+r'\bottomrule\end{tabular*}\par\medskip'+'\n'
def table(name,title,label,body,note='',continued=False):
    s=r'\begin{table}[htbp]\centering'+('\n'+r'\ContinuedFloat' if continued else '')+'\n'+r'\caption{'+title+'}'+('' if continued else r'\label{'+label+'}')+'\n'+r'\begin{minipage}{.95\textwidth}\fontsize{8}{10}\selectfont\setstretch{1}\setlength{\tabcolsep}{2pt}\renewcommand{\arraystretch}{1.08}'+'\n'+body+r'\par\noindent\fontsize{8}{9.5}\selectfont '+note+'\n'+r'\end{minipage}\end{table}'+'\n'
    (ROOT.parents[1]/'tables'/'main'/name).write_text(s,encoding='utf-8')
def fig(n,text,label,width=r'\textwidth'):
    return '\n'+r'\begin{figure}[htbp]\centering\includegraphics[width='+width+r']{fig/case_fig'+f'{n:02d}'+r'.pdf}\caption{'+text+r'}\label{'+label+r'}\end{figure}'+'\n'
