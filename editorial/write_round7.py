"""Final editorial alignment; no new experiments and no visual inspection."""
import json,re,statistics,hashlib,ast
from pathlib import Path
HERE=Path(__file__).resolve().parent;P=HERE.parent;BACK=P/'archive/before_round7_20261015';R6=P/'experiments'/'policy_grid'
def paragraph(t,prefix,new):
    t,n=re.subn(r'(?m)^'+re.escape(prefix)+r'[^\n]*',lambda _:new,t);assert n==1,(prefix,n);return t
def main():
    t=(BACK/'TRA-20261014-V3.tex').read_text(encoding='utf-8')
    t=t.replace('Regulated Railway Product, Fare, and Frequency Design under Income and Road-Cost Shocks','Railway Product, Fare, and Frequency Design: Pricing Authority, Fare Caps, and Participation Floors')
    t=t.replace('Railway product portfolio \\sep Value-of-time heterogeneity \\sep Road electrification \\sep Elastic travel demand \\sep Fare and frequency \\sep Transport equity','Railway service design \\sep Pricing authority \\sep Fare caps \\sep Participation floors \\sep Elastic travel demand \\sep Transport equity')
    t=paragraph(t,'Income composition is one source of demand uncertainty',r'Income composition matters for regulation because heterogeneous income changes alter willingness to pay for time savings and sensitivity to fares \citep{Borjesson2012,Hensher2001}. Opposite-sign shocks across income classes can widen the distribution of the value of travel time (VOT), whereas a uniform income shifter moves all classes together. The model therefore admits class-specific shocks when comparing price and mobility safeguards. These are parametric scenarios, not estimates of realized income polarization; the regulatory comparisons do not require polarization to be the dominant demand shock.')
    old=r'This strand therefore leaves open the question of how class-specific income shocks of opposite sign reshape aggregate railway demand and product composition; the present paper addresses it through the monetary-sensitivity elasticity $\rho_k$ and reports the resulting class composition of realized and rail demand in the counterfactual analysis (Sections~\ref{subsec:reference_results} and~\ref{subsec:scenario_analysis}).'
    new=r'For regulation, the remaining question is how price and service controls affect participation when potential travelers differ in monetary sensitivity and can choose not to travel. The present model uses class-specific monetary sensitivities and income scenarios to compare fare caps with participation floors under identical operating and financial constraints, separating welfare changes from the exclusion of vulnerable travelers (Sections~\ref{subsec:regulation} and~\ref{subsec:calibration_dependence}).'
    assert old in t;t=t.replace(old,new)
    anchor='Bilevel programming provides the natural mathematical structure'
    insert=r'Price-cap regulation restricts the fare an operator can charge while allowing service frequency and the remaining fare structure to respond. Within the taxonomy of \citet{ZhangLindseyYang2018}, it is a fare-regulation instrument, distinct from frequency, objective-function and fiscal regulation. For railway design, a cap on product--period fare multipliers can limit pricing authority without fixing departures. A participation floor instead constrains the number of vulnerable travelers who continue to travel after all fare, frequency and modal responses. The two instruments therefore restrict different aspects of the operator\textquotesingle{}s choice; their ability to preserve mobility and welfare must be compared within the same demand, resource and financial setting.'
    pos=t.index(anchor);t=t[:pos]+insert+'\n\n'+t[pos:]
    t=t.replace('Second, the retention requirement is imposed as a hard constraint within the bilevel program, and its cost is traced numerically through a profit--retention frontier.','Second, the retention requirement is imposed as a hard constraint and compared with direct fare caps and their combinations on a certified finite-menu policy grid, revealing the associated profit, welfare and participation tradeoffs.')
    t=t.replace('Fourth, in equity and regulation, distributional outcomes are typically evaluated post hoc or through an $\\varepsilon$-constraint on cost ratios among realized travelers, whereas the present trip-retention constraint, imposed as a hard constraint, captures non-participation exclusion and its cost is traced through a profit--retention frontier. The principal contribution is the integration of all four dimensions within a single bilevel framework that is evaluated through calibrated counterfactual stress tests.','Fourth, in equity and regulation, distributional outcomes are typically evaluated post hoc or through an $\\varepsilon$-constraint on cost ratios among realized travelers, whereas the present trip-retention constraint captures exclusion through non-participation and can be compared directly with fare caps. The principal contribution is a joint railway-design framework for assessing how pricing authority, fare caps and participation floors redistribute operator profit, traveler surplus and vulnerable mobility. Certified single-OD policy grids establish the regulatory tradeoffs within the tested menus; income, road-cost and network scenarios define their application boundaries.')
    old='Joint regulation changes the profit--welfare tradeoff without establishing universal complementarity.'
    new='In HN, adding a 1.05 cap to the strict floor raises welfare by 132 thousand CNY/day for a 4-thousand-CNY profit reduction, reaching 93 percent of the welfare optimum; in WC the floor alone already reaches 95 percent.'
    assert old in t;t=t.replace(old,new)
    manifest=json.loads((R6/'run_manifest.json').read_text(encoding='utf-8'))
    times=[a['record']['meta']['seconds'] for p in (R6/'grid').glob('*.json') for a in json.loads(p.read_text(encoding='utf-8'))['rows']]
    runtime=dict(batch_wall_seconds=manifest['seconds'],certificate_calls=len(times),median_certificate_call_seconds=statistics.median(times),minimum_certificate_call_seconds=min(times),maximum_certificate_call_seconds=max(times),workers=manifest['workers'],scope='60 HN/WC certificates plus four JX P3/P4 variant re-solves; warm starts and within-cap period-column reuse; not a cold full-study runtime')
    assert len(times)==60
    prefix='Computations run on 64-bit Windows 11 Pro'
    line=next(s for s in t.splitlines() if s.startswith(prefix))
    extra=f" The focused batch of 60 certificates and four JX variant re-solves took {runtime['batch_wall_seconds']:.1f} seconds wall-clock with four workers; the median recorded certificate call took {runtime['median_certificate_call_seconds']:.2f} seconds (range {min(times):.2f}--{max(times):.2f}). These timings describe this supplementary batch with warm starts and reuse of period columns within each cap domain."
    t=paragraph(t,prefix,line+extra)
    old='HN therefore benefits more from additional fare restraint than WC in this comparison; the experiment supports corridor-specific regulatory tradeoffs rather than universal complementarity.'
    new=old+' The WC reference welfare benchmark has profit/welfare gains of 852.5/769.6 thousand CNY/day, exceeding both strict-floor designs in both coordinates. Its retention is 0.999754, just below 1.00, and its largest active G/D multiplier is 1.20, so it fails the strict floor and is also excluded by tighter caps. Where the benchmark is feasible under looser regulation, a profit-maximizing operator need not select it.'
    assert old in t;t=t.replace(old,new)
    abstract=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',t,re.S)[1].split()
    assert len(abstract)<=200,len(abstract)
    # The behavioral and upper-level mathematical model stays untouched.
    a=r'\section{Model}';b=r'\section{Case study}'
    prior=(BACK/'TRA-20261014-V3.tex').read_text(encoding='utf-8')
    assert t[t.index(a):t.index(b)]==prior[prior.index(a):prior.index(b)]
    (P/'TRA-20261014-V3.tex').write_text(t,encoding='utf-8')
    (HERE/'runtime_summary.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
    # Reuse the certified-data plot; only the HN cluster label offsets change.
    source=(R6/'analyze_round6.py').read_text(encoding='utf-8');tree=ast.parse(source)
    func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='plot')
    plot='\n'.join(source.splitlines()[func.lineno-1:func.end_lineno])
    old="ax.annotate(f'{cap:.2f}',(x,y),xytext=(0,-17),textcoords='offset points',ha='center',fontsize=9,color=color)"
    new="ax.annotate(f'{cap:.2f}',(x,y),xytext=(-15,-14) if ci=='HN' and cap==1. else (0,-17),textcoords='offset points',ha='right' if ci=='HN' and cap==1. else 'center',fontsize=9,color=color)"
    assert old in plot;plot=plot.replace(old,new)
    old="offset=(9,26) if ci=='WC' and floor==1. else (9,8)"
    new="offset=(22,-6) if ci=='HN' and floor==1. else ((9,26) if ci=='WC' and floor==1. else (9,8))"
    assert old in plot;plot=plot.replace(old,new)
    header='''"""Final HN label-position adjustment using unchanged certified grid values."""
import sys,csv
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'experiments'/'main'))
import numpy as np
from analyze import groups,record
'''
    tail='''
if __name__=='__main__':
    with (HERE.parent/'experiments'/'policy_grid'/'cap_floor_frontier.csv').open(encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    for r in rows:
        for k in ['cap','floor','profit_gain','welfare']:r[k]=float(r[k])
        r['nondominated']=r['nondominated']=='True'
    plot(rows)
'''
    (HERE/'figure17_round7.py').write_text(header+plot+tail,encoding='utf-8')
    print('Final editorial update written; abstract words:',len(abstract),'runtime:',runtime)
if __name__=='__main__':main()
