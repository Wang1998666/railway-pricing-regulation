"""Write versioned table copies under exp_v4 only."""
from common import *
import re

def wording(text):
    text=re.sub(r'\bcertified\b','proven optimal',text,flags=re.I)
    text=re.sub(r'\bcertify\b','prove optimal',text,flags=re.I)
    text=re.sub(r'\bwitnesses\b','best designs found by search',text,flags=re.I)
    return re.sub(r'\bwitness\b','best design found by search',text,flags=re.I)

def main():
    folder=HERE/'tables';folder.mkdir(exist_ok=True)
    originals={p.name:sha(p) for p in (HERE.parents[1]/'tables'/'supplementary').glob('*.tex')}
    dump(HERE/'original_files.json',dict(manuscript_sha256=sha(HERE.parent/'TRA-20261016-V4.tex'),tables_sha256=originals))
    for name in ['v3_findings','v3_governance','v3_experiments','review_numerics','round2_polarization','review_appendix_design']:
        old=(HERE.parents[1]/'tables'/'supplementary'/(name+'.tex')).read_text(encoding='utf-8-sig');new=wording(old)
        new=new.replace('exact reference best designs found by search','proven-optimal reference designs').replace('P3 best designs found by search','P3 feasible designs').replace('P4 best designs found by search','P4 feasible designs').replace('Counts pool best designs found by search across objectives; missing best designs found by search do not prove optimal impossibility.','Counts pool feasible saved designs across objectives; failure to find a feasible design does not prove infeasibility.')
        new=new.replace('a coordinated multi-start best design found by search','the best design found by coordinated multi-start search')
        if name=='v3_experiments':
            new=new[:new.index(r'\par\noindent\textbf{D.')]
            new=new.replace('Six elasticity anchors','Eight elasticity anchors').replace('feasible best designs found by search and P0 violations','feasible designs and P0 violations')
            new+=r'''\par\noindent\fontsize{8}{9.5}\selectfont B uses the absolute 0.95 pre-shock floor and a 2,000-CNY allowance per reference departure. Violation counts may overlap. Unresolved optimized cells do not prove infeasibility. C pools profit and welfare comparisons; negative values identify a reduced decision domain. HN/WC common-pricing domains use exhaustive period enumeration and a coupled integer master with hard finance and retention when required. JX and differentiated pricing use multi-start joint fare--frequency search and independent local audits.
\end{minipage}\end{table}
\begin{table}[p]\ContinuedFloat\centering
\caption[]{Experimental domains and solution checks (continued)}
\begin{minipage}{.95\textwidth}\fontsize{8}{10}\selectfont\setstretch{1}\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.10}
\par\noindent\textbf{D. Commercial P3 across elasticity anchors (thousand CNY/day)}\par\smallskip
\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}llrrrrrr@{}}\toprule
& & \multicolumn{2}{c}{Cap 1.10} & \multicolumn{2}{c}{Cap 1.20} & \multicolumn{2}{c}{Cap 1.30} \\
Case & Anchor & Profit gain & $\Delta W$ & Profit gain & $\Delta W$ & Profit gain & $\Delta W$ \\
\midrule
'''
            a=read(HERE/'exp4'/'analysis.json');rows=a['old_rows']+a['rows']
            for ci in ['HN','WC','JX']:
                for anchor in [.6,.8,.85,.9,.95,1.,1.2,1.5]:
                    vals=[]
                    for cap in [1.1,1.2,1.3]:
                        r=next(r for r in rows if r['case_id']==ci and abs(r['anchor']+anchor)<1e-9 and r['cap']==cap and r['objective']=='profit');vals += [f"{r['profit_gain']:,.1f}",f"{r['delta_W']:,.1f}"]
                    new += (ci+r'$^{*}$' if ci!='JX' else ci)+f' & $-{anchor:.2f}$ & '+' & '.join(vals)+r' \\'+'\n'
                if ci!='JX':new+=r'\addlinespace'+'\n'
            new+=r'''\bottomrule\end{tabular*}\par\medskip
\par\noindent Profit gain and $\Delta W$ are relative to the same-state P0. Each elasticity anchor is recalibrated to preserve reference flows and the 0.88 peak load; the floor is 0.95 and fares use the 0.025 menu. Stars identify proven-optimal commercial designs: 48 HN/WC optima; the 24 JX entries are best designs found by search. Welfare is evaluated at each commercial design. The new anchors are $-1.20$ and $-1.50$; WC welfare is positive at $-1.50$ under all three caps.
\end{minipage}\end{table}
'''
        if name=='v3_governance':
            a=read(HERE/'exp1'/'analysis.json')
            new+=r'''\begin{table}[p]\ContinuedFloat\centering
\caption[]{Mobility guarantees, governance accounts and bounded carbon effects (continued)}
\begin{minipage}{.95\textwidth}\fontsize{8}{10}\selectfont\setstretch{1}\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.10}
\par\noindent\textbf{E. Refined participation floors: commercial P3 relative to P0}\par\smallskip
\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrrrr@{}}\toprule
Case & Cap & Floor & Profit gain & $\Delta W$ & L retention & W benchmark (\%) \\
\midrule
'''
            for ci in ['HN','WC']:
                for r in a[ci]['selected']:
                    new+=f"{ci}$^{{*}}$ & {r['cap']:.2f} & {r['floor']:.4f} & {r['profit_gain']:,.1f} & {r['delta_W']:,.1f} & {r['L_retention']:.6f} & {r['welfare_optimum_share']*100:.1f}"+r' \\'+'\n'
                if ci=='HN':new+=r'\addlinespace'+'\n'
            new+=r'''\bottomrule\end{tabular*}\par\medskip
\par\noindent Money is in thousand CNY/day, one direction. Stars identify proven-optimal commercial designs. W benchmark is the cap-1.20 welfare optimum in Table~\ref{tab:baseline_policy_values}; WC's 100.0\% is rounded, with welfare 0.3 thousand CNY/day below the optimum. A floor may affect the selected integer design while remaining numerically slack. At cap 1.20, WC's floor 0.9995 yields higher profit and welfare than the strict-floor designs under either cap 1.20 or cap 1.05.
\end{minipage}\end{table}
'''
        assert not re.search(r'\b(?:certified|certify|witness\w*)\b',new,re.I),name
        (folder/(name+'_v4.tex')).write_text(new,encoding='utf-8')
    print('Prepared six versioned table files',flush=True)
if __name__=='__main__':main()
