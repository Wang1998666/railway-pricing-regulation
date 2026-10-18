"""Generate all empirical tables and revise V3 from the preserved V2 source."""
import json,datetime,shutil,collections
from pathlib import Path
import numpy as np
from model import ROOT
from analyze import groups,record,pair_feasible

PAPER=ROOT.parent
A=json.loads((ROOT/'analysis.json').read_text(encoding='utf-8'))
C={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']}
REF={ci:next(g for g in groups('E2') if g['job']['id']==f'{ci}_reference_none') for ci in C}

def write(name,text): (PAPER/name).write_text(text,encoding='utf-8')
def fmt(v,d=1): return f'{v:.{d}f}'
def row(values): return ' & '.join(map(str,values))+r' \\'+'\n'
def table(name,caption,label,columns,header,rows,note='',long=False):
    text=r'\begingroup\footnotesize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.12}'+'\n'
    if long:
        text+=r'\begin{longtable}{'+columns+'}\n'+r'\caption{'+caption+r'}\label{'+label+r'}\\'+'\n'+r'\toprule'+'\n'+row(header)+r'\midrule\endfirsthead'+'\n'+r'\multicolumn{'+str(len(header))+r'}{l}{\textit{Continued}}\\\toprule'+'\n'+row(header)+r'\midrule\endhead'+'\n'+rows+r'\bottomrule\end{longtable}'+'\n'
    else:
        text+=r'\begin{table}[htbp]\centering\caption{'+caption+r'}\label{'+label+'}\n'+r'\begin{tabular}{'+columns+'}\n'+r'\toprule'+'\n'+row(header)+r'\midrule'+'\n'+rows+r'\bottomrule\end{tabular}'+'\n'+r'\parbox{.98\textwidth}{\footnotesize '+note+r'}\end{table}'+'\n'
    if long and note: text+=r'{\footnotesize '+note+'}\n'
    text+=r'\endgroup'+'\n'; write('tables/'+name,text)

def tables():
    rows=''
    for ci,c in C.items():
        ps=c['products']; counts=[sum(p['tier']==t and not p['candidate'] for p in ps) for t in ['G','D','K']]; N=np.array([p['N0'] for p in ps]); total=int(N.sum()); week={'HN':1124,'WC':1297,'JX':3464}[ci]; refs={'HN':160,'WC':185,'JX':494}[ci]
        rows+=row([ci,f"{len(c['cities'])}/{len(c['ods'])}",2*(len(c['cities'])-1),fmt(max(c['road_km'])),f'{week}/{refs}','/'.join(map(str,counts)),f'0/{total}',sum(p['candidate'] for p in ps)])
    table('v3_structure.tex','Corridor structure and fixed observed supply','tab:formal_case_data','lrrrrlrr',['Case','Nodes/ODs','Segments','Road km','Week/ref.','Products G/D/K','Adj./fixed','K cand.'],rows,r'Counts are unique train numbers or observable stopping-coverage families, as indicated. Reference records are OD records; the number of unique trains is 147/185/190. Segments distinguish two schematic track types; physical rail kilometrage is unavailable. All reference departures are fixed. Seat capacities are maintained assumptions, not observations.')
    params=[
        ('A. Demand and calibration','','','',''),
        ('Class shares H/M/L',r'$s_k$','0.20/0.60/0.20','potential travelers','Stylized'),
        ('Participation',r'$\pi^{\mathrm t,*}$','0.85','each OD/class/period','Stylized'),
        ('Rail share',r'$r_w$','0.70/0.60/0.55/0.45','distance bands','Stylized'),
        ('Initial G/D/K load',r'$\lambda_t$','0.78/0.72/0.70','before common rescale','Lit.-anchored'),
        ('Reference maximum load','','0.92','after rescale','Stylized'),
        ('Cost/revenue ratio','','0.92','reference design','Stylized'),
        ('VOT H/M/L','','175.0/90.0/42.9','CNY per hour','Derived'),
        ('B. Preferences H/M/L','','','',''),
        ('Money',r'$\beta^{\mathrm c}_{k0}$','0.012/0.020/0.035',r'CNY$^{-1}$','Lit.-anchored'),
        ('In-vehicle',r'$\beta^{\mathrm{iv}}_k$','0.035/0.030/0.025',r'min$^{-1}$','Lit.-anchored'),
        ('Access',r'$\beta^{\mathrm{ac}}_k$','0.045/0.040/0.035',r'min$^{-1}$','Lit.-anchored'),
        ('Terminal wait',r'$\beta^{\mathrm{wt}}_k$','0.050/0.045/0.040',r'min$^{-1}$','Lit.-anchored'),
        ('Schedule',r'$\beta^{\mathrm{sc}}_k$','0.025/0.022/0.018',r'min$^{-1}$','Lit.-anchored'),
        ('Reliability',r'$\beta^{\mathrm{rel}}_k$','0.020/0.018/0.015',r'min$^{-1}$','Stylized'),
        ('Transfer',r'$\beta^{\mathrm{tr}}_k$','0.15/0.12/0.10','per transfer','Stylized'),
        ('Comfort',r'$\gamma^{\mathrm{com}}_k$','0.08/0.06/0.04','per index unit','Stylized'),
        ('Flexibility',r'$\gamma^{\mathrm{flex}}_k$','0.10/0.07/0.05','per index unit','Stylized'),
        ('Income elasticity',r'$\rho_k$','0.70/0.80/0.90','local constant elasticity','Lit.-anchored'),
        ('C. Nested-logit scales','','','',''),
        ('Seat / product',r'$\mu_{\mathrm{sc}}/\mu_{\mathrm{pr}}$','0.30/0.45','common across classes','Stylized'),
        ('Road / auto',r'$\mu_{\mathrm{road}}/\mu_{\mathrm{auto}}$','0.50/0.55','one auto alternative','Stylized'),
        ('Mode / participation',r'$\mu_k/\mu_0$','0.75/1.00','ordered scales','Stylized'),
        ('D. Supply, attributes, and costs','','','',''),
        ('G seats business/first/second',r'$\sigma_{sb}$','18/96/576','690 total','Stylized'),
        ('D seats first/second',r'$\sigma_{sb}$','72/480','552 total','Stylized'),
        ('K hard seat/hard/soft sleeper',r'$\sigma_{sb}$','768/528/72','1368 total','Stylized'),
        ('Seat comfort G; D; K','','5/4/3; 4/3; 2/3/4','seat order above','Stylized'),
        ('Rail flexibility G/D; K','','2; 1','booking attribute','Stylized'),
        ('Rail terminal wait','','10','minutes','Stylized'),
        ('Schedule parameter',r'$\vartheta$','15',r'min $\times$ departures/h','Derived'),
        ('Reliability G/D/K','','0.02/0.03/0.08','times running minutes','Stylized'),
        ('Background / cost share',r'$\bar X/\chi_s$','0/1','corridor accounting convention','Stylized'),
        ('Cycle time',r'$t_s^{\mathrm c}$',r'$2\max_wt_{ws}^{\mathrm{iv}}/60+1$','hours','Derived'),
        ('Restart cost candidate K',r'$c_s^{\mathrm f}$','0.10','parent fixed commitment','Stylized'),
        ('E. Regulation and market states','','','',''),
        ('Observed frequency',r'$N_{sh}$',r'$N^0_{sh}$','all observed G/D/K','Regulatory'),
        ('Fare menu G/D',r'$\Phi_s$','0.80:0.05:1.20','common across seats','Regulatory'),
        ('Fare menu K',r'$\Phi_s$','1','observed and candidate','Regulatory'),
        ('Load ceiling',r'$\bar\lambda$','0.95','alternative 1.00 in E5','Regulatory'),
        ('Loss budget',r'$B$','500','CNY thousand/day','Regulatory'),
        ('Retention / vulnerable class',r'$\underline\eta/\mathcal K^{\mathrm L}$',r'$0.95/\{\mathrm L\}$','fixed pre-shock denominator','Regulatory'),
        ('OD floor',r'$\underline N^{\mathrm{OD}}_{wh}$',r'$\min\{1,\sum_sa_{ws}N^0_{sh}\}$','period specific','Regulatory'),
        ('Incumbent G/D daily floor',r'$\underline N_s^{\mathrm{day}}$','1','redundant under fixed frequency','Regulatory'),
        ('Uniform income level change','',r'--7.56\%','mean log shock matched','Scenario'),
        ('Polarized H/M/L','',r'+2/--8/--15\%','log changes in utility','Scenario'),
        ('Electrification states','','none; A; AM low/high; all low/high','A=auto; AM includes van','Scenario'),
        ('Auto / MaaS / coach / van saving','','0.58/0.20/0.12/0.30','CNY per road km','Lit.-anchored'),
        ('Auto intensity / road pass-through','','0.50; 0.30/0.70','separate exposures','Scenario')]
    rows=''
    for cat,sym,value,unit,prov in params:
        rows+=r'\multicolumn{5}{l}{\textbf{'+cat+r'}}\\\addlinespace'+'\n' if not sym and not value else row([cat,sym,value,unit,prov])
    table('v3_parameters.tex','Calibration, supply assumptions, and market states','tab:calibration_parameters',r'p{.27\textwidth}p{.12\textwidth}p{.21\textwidth}p{.20\textwidth}p{.12\textwidth}',['Parameter','Symbol','Value','Meaning/unit','Provenance'],rows,r'Observed fields are limited to timetables, queried published fares, and route attributes. Product fares/running times and access medians are Derived. Preference magnitudes are anchored to the cited VOT literature, without claiming econometric identification. Costs and utility constants are calibrated separately by corridor; all coefficients and hashes are archived.',long=True)
    rows=''
    data=[('E1','Instrument value','Reference; partial reoptimizations','P0--P4','30 reused + 12'),('E2','Stress and feasibility','3 income states; 6 electrification states','P0--P4','540 + 102'),('E3','K-entry sensitivity','40 perturbations in 11 dimensions','P3/P4','480 + 12 confirm.'),('E4','Retention and budget','2 states; 5 floors; 4 budgets','P3/P4','480'),('E5','Numerics and calibration','8 configurations; 2 class-share shifts','P3','60'),('E6','Seat relativities','3 income states, no electrification','P3/P3-sb','18 + 18 comparators'),('E7','K-entry regimes','11 polarization; 7 electrification scales','P3/P4','924'),('X1/X2','Governance and equity','Saved decisions and same-state reference','Post-process','0')]
    for x in data: rows+=row(x)
    table('v3_experiments.tex','Experiments and archived design evaluations','tab:experiment_overview',r'lp{.17\textwidth}p{.34\textwidth}lp{.16\textwidth}',['ID','Question','Design','Policies','Records'],rows,r'Counts include both objectives and all three corridors. E1 reference records are reused from E2. The 102 additional E2 records remove the financial floor. E6 includes archived P3 comparators. Logical evaluations exceed independent searches because P2=P0 and P3=P1.')
    rows=r'\multicolumn{9}{l}{\textbf{Panel A. Objective values (CNY thousand/day)}}\\\midrule'+'\n'+row(['Case','Obj.','P0','P1','P2','P3','P4',r'$\Delta_{\mathrm{joint}}$',r'$\Delta_{\mathrm{incr}}$'])
    for x in A['reference']: rows+=row([x['case_id'],'P' if x['objective']=='profit' else 'W',*[fmt(x['values'][p]/1000) for p in ['P0','P1','P2','P3','P4']],fmt(x['joint_gain']/1000),fmt(x['joint_increment']/1000)])
    rows+=r'\midrule\multicolumn{9}{l}{\textbf{Panel B. Operating outcomes and constraint margins}}\\\midrule'+'\n'+row(['Case','Policy','G/D/K',r'$\bar\phi$',r'$\lambda^{\max}$',r'$\eta^{\mathrm L}$','F margin','C headroom',''])
    for ci,c in C.items():
        for pol,obj in [('P0','profit'),('P3','profit'),('P3','welfare')]:
            r=record(REF[ci],pol,obj); N=np.array(r['N']); tiers=np.array([p['tier'] for p in c['products']]); departures='/'.join(str(int(N[tiers==t].sum())) for t in ['G','D','K']); mean=float(np.sum(N*np.array(r['phi'])[:,:,0])/N.sum())
            rows+=row([ci,pol+('P' if obj=='profit' else 'W'),departures,fmt(mean,3),fmt(r['maxlf'],4),fmt(r['eta'],4),fmt((r['profit']+500000)/1000),fmt(.95-r['maxlf'],4),''])
    rows+=r'\midrule\multicolumn{9}{l}{\textbf{Panel C. P3 participation and rail share by class}}\\\midrule'+'\n'+row(['Case','Class','Part. P','Rail P','Part. W','Rail W','','',''])
    for ci in C:
        p=record(REF[ci],'P3','profit'); w=record(REF[ci],'P3','welfare')
        for k,cls in enumerate(['H','M','L']): rows+=row([ci,cls,fmt(p['class_trips'][k]/p['class_potential'][k],4),fmt(p['rail_by_class'][k]/p['class_trips'][k],4),fmt(w['class_trips'][k]/w['class_potential'][k],4),fmt(w['rail_by_class'][k]/w['class_trips'][k],4),'','',''])
    table('v3_reference.tex','Reference-state policy values, operations, and class composition','tab:baseline_policy_values','llrrrrrrr',['Case','Criterion','','','','','','',''],rows,r'P/W denote the commercial/welfare objective. Financial margins are profit plus B in CNY thousand/day; capacity headroom is $\bar\lambda-\lambda^{\max}$. The G/D/K counts include fixed observed K. Mean fare multipliers are departure weighted. Zero joint increments follow from the fixed-frequency restriction.',long=True)
    rows=''
    for i,e in enumerate(A['events']):
        trigger=e['trigger'].split('_k_cost_')[-1]; pats=', '.join(e['patterns']); rows+=row([e['case_id'],'P' if e['objective']=='profit' else 'W',trigger,'Gain',e['departures'],pats,e['channel']])
    table('v3_events.tex','Confirmed additional-K events in E3','tab:k_reopening_events',r'llllrp{.30\textwidth}l',['Case','Obj.','K cost factor','Role','Daily K','Candidate IDs','Channel'],rows,r'All six events are confirmed at eight rounds. Daily K is additional service, excluding all observed K. No E2 K-dependent recovery is found at the baseline budget. Trigger and descriptive event channel are distinct: a cost perturbation can induce an affordability or coverage response. CK07 in JX covers GZ--NC; exact OD incidences are in the archived inputs.',long=True)
    rows=r'\multicolumn{7}{l}{\textbf{Panel A. Governance gaps, feasible E2 P4 pairs}}\\\midrule'+'\n'+row(['Case','Pairs',r'$\Delta\Pi$ (k)',r'$\Delta\mathcal W$ (k)','Ratio','',''])
    for ci in C:
        rs=[x for x in A['governance'] if x['case_id']==ci]; g=rs[0]; rows+=row([ci,len(rs),fmt(g['profit_gap']/1000),fmt(g['welfare_gap']/1000),fmt(g['ratio'],3) if g['ratio'] is not None else '--','',''])
    rows+=r'\midrule\multicolumn{7}{l}{\textbf{Panel B. Budget sufficiency among 17 stressed cells/corridor}}\\\midrule'+'\n'+row(['Case','Policy','Fixable found','Budget range (M)','Unresolved','',''])
    for ci in C:
        for policy in ['P3','P4']:
            rs=[b for b in A['budgets'] if b['case_id']==ci and b['policy']==policy]; vals=[b['Bstar_upper_bound']/1e6 for b in rs if b['budget_fixable_found']]; rows+=row([ci,policy,len(vals),fmt(min(vals),2)+'--'+fmt(max(vals),2),sum(not b['budget_fixable_found'] for b in rs),'',''])
    rows+=r'\midrule\multicolumn{7}{l}{\textbf{Panel C. E5 deviations from reference P3}}\\\midrule'+'\n'+row(['Test','Feasible/6',r'Mean abs. \%',r'Max abs. \%','Max abs. k','Ranking',''])
    for test in ['grid025','grid10','rounds8','mu_sc_low','mu_sc_high','mu_pr_low','mu_pr_high','lambda1','lowheavy','highheavy']:
        rs=[r for r in A['robustness'] if r['test']==test]; good=[r for r in rs if r['feasible']]; vals=[abs(r['deviation_percent']) for r in good if r['deviation_percent'] is not None]
        rows+=row([test.replace('_',' '),f'{len(good)}/6',fmt(np.mean(vals),2) if vals else '--',fmt(max(vals),2) if vals else '--',fmt(max((abs(r['absolute_deviation'])/1000 for r in good),default=0),2),'fixed N',''])
    table('v3_governance.tex','Governance, sufficient budgets, and numerical sensitivity','tab:governance_robustness','llrrrrl',['','','','','','',''],rows,r'k/M denote CNY thousand/million per modeled day. With one feasible E2 pair per corridor, governance medians and ranges collapse to the reported values. Budgets are sufficient-budget upper bounds from best found no-floor profit designs; unresolved searches do not establish budget impossibility. Percentage deviations exclude zero base objectives and infeasible outputs. Scale sensitivities hold constants fixed; the resulting calibration fragility is reported, not excluded.',long=True)

def figure(n,caption,label,width=r'\textwidth'):
    return '\n'+r'\begin{figure}[htbp]\centering'+'\n'+r'\includegraphics[width='+width+']{fig/case_fig'+f'{n:02d}'+'.pdf}\n'+r'\caption{'+caption+r'}\label{'+label+r'}\end{figure}'+'\n'

def manuscript():
    source=(PAPER/'TRA-20261014-V2.tex').read_text(encoding='utf-8'); start=source.index(r'\section{Case Study and Experimental Design}'); head=source[:start]
    head=head.replace(r'\usepackage{longtable}',r'\usepackage{longtable,caption}')
    head=head.replace(r'\setstretch{1.5}',r'\setstretch{1.20}')
    # Keep the general model, but correct two institutional claims and adopt an
    # equivalent leaf-intercept normalization used by the calibrated application.
    old='This specification mirrors the floating-tariff regulatory regime of China Railway, in which dynamic yield management floats fares relative to the published benchmark on a per-train and per-period basis, while relativities across seat classes (such as the statutory ratio of first-class to second-class fares) remain regulated and fixed. Because seat-class relativities cannot be unilaterally adjusted to price-discriminate across traveler groups, the operator cannot rely on seat-level tariff divergence to counter value-of-time polarization. Accommodating polarized traveler segments therefore necessitates the coordinated reconfiguration of product portfolios (speed tiers G, D, and K) and their allocated departure frequencies.'
    new=r'This is a maintained tariff restriction for the counterfactual exercise, rather than a claim that seat-class ratios are universally statutory. High-speed/EMU fares and ordinary-train soft-seat and soft-sleeper fares have been delegated to railway enterprises, while basic ordinary-train hard-seat and hard-sleeper fares are subject to government price regulation \citep{NDRC2021RailFare,NDRC2016SoftFare}. In the main experiments, all K multipliers are conservatively fixed at one, including soft sleepers, because a common multiplier cannot vary the latter without varying the regulated hard-seat tariff. Fixed G/D seat relativities limit a possible response to polarization; whether this restriction makes the portfolio margin important is tested against seat-specific multipliers in Section~\ref{subsec:k_reopening}, rather than assumed.'
    assert old in head; head=head.replace(old,new)
    old=r'To achieve econometric identification, one constant is normalized to zero at each choice level: one reference detailed alternative in each auto and road nest, one reference seat class within each rail product, one reference product per class, one reference mode per class, and $\alpha^0_n=0$ for the outside option.'
    new=r'The constants require a consistent location normalization. For the counterfactual calibration, $\alpha^0_n=0$ and the explicit non-leaf constants $\alpha^{\mathrm t}_k$, $\alpha^{\mathrm m}_{k,m}$ and $\alpha^{\mathrm{pr}}_{k,s}$ are set to zero; their calibrated level shifts are absorbed into the segment-specific leaf constants $\alpha_{ni}$. This equivalent representation exploits translation invariance of the logsum and does not additionally set a reference leaf intercept to zero. It is an accounting normalization for reproducing target shares, rather than an econometric estimate.'
    assert old in head; head=head.replace(old,new)
    # Replace legacy numerical claims in abstract and contribution paragraph.
    old='Across three calibrated Chinese corridors, joint fare--frequency control raises reference-state daily profit by CNY 1.84--3.75 million and within-state welfare by CNY 1.92--3.81 million relative to the status quo. Across 108 corridor--state--objective groups, the joint policy restores feasibility in 52 groups in which the fixed status quo violates a financial or vulnerable-retention requirement. Conventional K-pattern availability restores another 10 groups, while confirmed reopening in the wider sensitivity analysis is concentrated in Wuhan--Changsha and the multi-node Jiangxi corridor rather than the mature Hangzhou--Nanjing market.'
    new='The application fixes the frequencies of all observed trains, separating the inherited network timetable from additional corridor-dedicated conventional service. In three calibrated Chinese corridors, reference-state common-fare adjustment raises daily profit by CNY 0--28.9 thousand and railway-centered welfare by CNY 0--5.3 thousand. Frequency-only and joint policies coincide with the fixed-design and fare-only policies, respectively. Of 54 corridor--state cells, only the three reference cells yield feasible designs at the baseline budget, and neither repricing nor additional K service restores the remaining cells. No-floor searches identify sufficient budgets in 45 cells under the incumbent policy and 46 with additional K. Six sensitivity events select extra K departures, all under lower K operating costs. Seat-specific fares offer a larger reference-state response, while scale sensitivity exposes the calibration dependence of the quantitative findings.'
    assert old in head; head=head.replace(old,new)
    old='Applied to three calibrated Chinese corridors, the framework shows that joint fare--frequency control raises reference-state daily profit by CNY 1.84--3.75 million, restores regulated feasibility in 52 of 108 corridor--state--objective groups in which the fixed status quo fails a financial or equity requirement, and reveals that the value of conventional service is state-contingent---concentrated in specific stressed corridors---rather than universal.'
    new='The application deliberately holds all observed train frequencies fixed. It therefore tests how much repricing, seat-relativity relaxation, and additional conventional service can achieve when the network timetable is inherited. Reference common-fare gains are modest (CNY 0--28.9 thousand/day in profit), the 54-cell stress matrix exposes financial and mobility shortfalls, and six sensitivity events select extra K departures under operating-cost reductions. These outcomes qualify the role of the available instruments rather than presupposing frequency rationalization or universal conventional-service value.'
    assert old in head; head=head.replace(old,new)
    roadmap='The remainder of this paper is organized as follows.'; i=head.index(roadmap); j=head.index('\n',i)
    head=head[:i]+r'The remainder of this paper is organized as follows. Section~\ref{sec:literature} reviews the literature, and Section~\ref{sec:model} formulates the model. Section~\ref{sec:case} presents the corridors, calibration, solution procedure, and experimental findings. Section~\ref{sec:conclusion} discusses the implications and limitations.'+head[j:]
    head=head.replace('and $y_s=0$ for conventional patterns when K is unavailable.','and $y_s=0$ for candidate conventional patterns when additional K is unavailable.')
    sec=r'''
\clearpage
\section{Case study}\label{sec:case}\label{sec:case_design}\label{sec:results}
The application evaluates the five research questions under an inherited network timetable. All observed trains, including G, D, and K, have fixed frequencies. This restriction changes the interpretation of instrument value: incumbent frequency adjustment is unavailable, whereas additional corridor-dedicated K service remains a portfolio decision. We first document the calibration and experiment design, then examine reference outcomes, shock transmission, portfolio entry, and regulatory and governance implications. All monetary outcomes are calibrated counterfactuals for one direction of travel per modeled day.

\subsection{Corridors, data, and calibration}\label{subsec:case_settings}\label{subsec:corridor_data}
\paragraph{Corridors and source boundaries.}
Hangzhou--Nanjing (HN) represents a mature high-speed market, Wuhan--Changsha (WC) a rail--road competitive market, and Ganzhou--Ji'an--Nanchang--Jiujiang (JX) a four-node corridor containing all six forward ODs, including Ganzhou--Nanchang. The institutional descriptions follow the cited line-opening and transport reports \citep{NinghangHSR2013,WuhanChangshaPopularOD2026,ChinaGovChanggan2019,NanchangGovChanggan2019}. The archived 12306 queries cover travel dates 3--9 August 2026, with Wednesday 5 August defining $z^0$; these are travel dates, not collection dates. The response metadata retain the earlier query timestamps. Amap distance, route-planning duration, toll, and station-access fields are routing snapshots, not observed passenger travel times or reliability \citep{ChinaRailway12306,AmapWebService2026}.

Observed fields are the dated train and fare responses and Amap attributes. Derived fields include unique-train counts, within-corridor stopping-coverage signatures, median running times and fares, and road-cost formulas. Train capacities, demand, utility constants, resource envelopes, cost allocation and background loads are maintained calibration assumptions. Income/electrification changes are scenarios; fare menus, budget and retention requirements are regulatory settings. National and city statistics provide context rather than demand identification. This distinction is consequential because the source files contain neither full-train endpoints nor actual trainset formations, rail kilometrage, corridor accounts, or through-passenger occupancy.
\input{tables/v3_structure.tex}

\paragraph{Products, segments, and fixed supply.}
Each observed product groups train numbers with the same G/D/K tier and exact coverage of the modeled ODs. Different observable stopping signatures remain separate products; unobserved intermediate stations are not inferred. All these products belong to $\mathcal S^{\mathrm{fix}}$, with $N_{sh}=N^0_{sh}$ in every experiment. Incumbent G/D products additionally belong to $\mathcal S^{\mathrm{inc}}$; their one-departure daily floors are redundant under this restriction. HN and WC each have one observed product per tier; JX has 21 observed coverage products. Each observed K coverage family also defines one \emph{additional} dedicated candidate with zero reference frequency, yielding 1/1/10 candidates. Candidate IDs CK01--CK10 identify extra services, rather than reopening the observed trains.

Two schematic segment chains separate the high-speed/EMU and conventional routes. Route incidence traverses the origin--destination span of a product, while passenger incidence traverses only the passenger's subpath. K uses the conventional chain; assigning D to the other chain is a stylized resource convention, not a verified train-path reconstruction. In-corridor road distances proxy operating length where rail kilometrage is absent; they are never labeled measured rail kilometers. Available paths equal the larger of 16 departures per hour times period duration and reference segment use plus four reserve paths. Round-trip cycles are twice the maximum observed product running time plus one hour; fleet hours cover rounded-up reference requirements and the declared candidate envelope. These choices make $z^0$ resource-feasible without purporting to reconstruct network timetables.

Background loads are set to $\bar X_{esbh}=0$ and corridor cost shares to $\chi_s=1$. These explicit accounting conventions are necessary because the archival data cannot identify either quantity; they do not establish that through-passenger loads are absent or that all network costs belong to the corridor. G, D and K seat capacities are fixed assumptions of 690, 552 and 1368, partitioned as in Table~\ref{tab:calibration_parameters}. Premium seats in the composition analysis mean G business/first and D first class; sleepers are reported within K, not classified as premium seats.
'''
    sec+=figure(3,'All observed reference departures are fixed, so the remaining extensive margin is additional conventional service. The lines are schematic track-type chains, not geographic or surveyed rail alignments. Supply labels give daily G/D/K trains; path envelopes follow the AM/day/PM/night order. JX arcs show the ten candidate coverage families, with patterns including GZ--NC accented.','fig:corridor_structure')
    sec+=r'''
\paragraph{Demand and utility calibration.}
The four periods are 06:00--09:00, 09:00--17:00, 17:00--20:00 and 20:00--06:00, lasting 3/8/3/10 hours. A unique train is assigned to the period of departure from its earliest modeled boarding city, providing a common product-period clock. For a product serving OD $w$, let $d_w$ be the observed road distance, $\omega_{ws}=a_{ws}/d_w$, and
\begin{equation}
 r_{ws}=\frac{\omega_{ws}}{\max_e\sum_{w'}\delta^{\mathrm{pax}}_{ew's}\omega_{w's}},\qquad
 T^0_{wsbh}=a\,N^0_{sh}\sigma_{sb}\lambda_{t(s)}r_{ws},\qquad
 \bar Q_{wkh}=\frac{s_k\sum_{s,b}T^0_{wsbh}}{0.85\,r_w}.
 \label{eq:case_demand_split}
\end{equation}
Here $s_k=0.20/0.60/0.20$, $\lambda_t=0.78/0.72/0.70$, and the common corridor rescale $a=0.92/0.78$ sets the busiest G segment to 0.92. The OD rail-share targets $r_w$ are 0.70/0.60/0.55/0.45 for road distances up to 350/500/800/beyond 800 km. Thus OD allocations account for shared segment occupancy, and period populations follow the observed period supply; no uniform temporal split is imposed. Road and auto receive 60\%/40\% of nonrail trips; coach, MaaS and van receive 75\%/22\%/3\% within road. These are stylized targets.

Nested constants reproduce the targets level by level. For child share $p_c$, setting $v_c=\Lambda_j+\mu_j\ln p_c$ inverts Eq.~\eqref{eq:nl_recursion}; applying this log-share relation from participation through modes, products and seats gives the calibrated leaf intercepts under the normalization in Section~\ref{sec:demand_model}. All three corridors reproduce participation to within $1.2\times10^{-16}$ and target rail flows to within $3\times10^{-11}$ trips; maximum reference loads are 0.92. Candidate constants inherit their observed parent family's seat preferences, with a per-departure product intercept adjustment $-\mu_{\mathrm{pr}}\ln N^0_{sh}$; empty parent periods borrow the nearest active period. Candidate demand therefore is an explicit transfer assumption, not estimated willingness to use an unobserved new service. Running and commitment costs are rescaled so that reference operating cost is 92\% of rail revenue. Candidate commitment costs equal 10\% of the parent's allocation. Every numerical coefficient is archived.
\input{tables/v3_parameters.tex}

\paragraph{Market states and regulation.}
Reference income has zero log change. Polarization assigns H/M/L income changes of +2/--8/--15\%. The uniform state matches its class-weighted mean \emph{log} change,
\begin{equation}
 \overline{\Delta y}=0.2\ln(1.02)+0.6\ln(0.92)+0.2\ln(0.85)=-0.078572,
 \qquad \exp(\overline{\Delta y})-1\simeq-0.0756.
 \label{eq:mean_matched_income}
\end{equation}
The comparison therefore matches a 7.56\% uniform level decline, rather than the arithmetic 7.4\% average decline. The six road states are none, auto only, auto plus MaaS/van with low/high pass-through, and all road alternatives with low/high pass-through. Auto exposure is 0.50 of the 0.58 CNY/km saving; passenger-fare pass-through is 0.30/0.70 of MaaS/coach/van savings of 0.20/0.12/0.30 CNY/km. E7 scales these composite savings while holding the high pass-through constant. The base settings are $B=500{,}000$ CNY/day, $\underline\eta=0.95$, $\mathcal K^{\mathrm L}=\{\mathrm L\}$ and $\bar\lambda=0.95$. OD-period floors are the smaller of one and observed departures, so zero-service periods do not make P0 infeasible by construction. G/D multipliers lie on 0.80:0.05:1.20. Both observed and candidate K use $\Phi_s=\{1\}$; extending this restriction to soft sleepers is a conservative common-tariff convention, not a statement that soft-sleeper fares are government-set.
'''
    sec+=figure(4,r'Equal mean income shocks have different class-specific VOT effects, while electrification changes road monetary costs through a separate channel. The WC alluvial carries class-colored reference trips through participation, modes, tiers and seats; its widths are thousand trips/day. The lower panels show VOT and endpoint road costs; filled/hollow markers denote none/all-high electrification. Seat labels 1--3 follow the order in Table~\ref{tab:calibration_parameters}.','fig:calibration_shocks')
    sec+=r'''
\subsection{Policy sets, experiments, and solution procedure}\label{subsec:solution_protocol}\label{subsec:policy_sets}\label{subsec:experiments}
\paragraph{Nested policy sets and feasibility.}
P0 fixes the observed design; P1 adjusts incumbent G/D common fares; P2 allows incumbent frequencies subject to $\mathcal S^{\mathrm{fix}}$; P3 combines these instruments with candidates off; and P4 adds the candidate K frequencies. Because every observed product is fixed, $\mathrm{P2}=\mathrm{P0}$ and $\mathrm{P3}=\mathrm{P1}$ as decision sets. These identities are retained as informative controls. P3-sb additionally allows G/D seat-specific multipliers; the K tariff remains fixed. It is a diagnostic relaxation of seat relativities, not a recommendation to change regulated basic tariffs.

Feasibility is independent of the commercial/welfare objective because the constraints coincide. E2 therefore reports 54 corridor--state cells, counting a policy feasible when either search supplies a feasible witness. Search-specific differences are recorded before witness closure; none is found in the main matrix. Failure to find a witness is reported as unresolved feasibility, rather than a mathematical infeasibility certificate. The experiment inventory in Table~\ref{tab:experiment_overview} retains the seven planned experiments, including redundant instrument comparisons imposed by fixed supply.
\input{tables/v3_experiments.tex}

\paragraph{Structured search.}
The Python 3.13/NumPy implementation evaluates the asymmetric seat--product nested logit in one pass. Starts include the reference design, uniform G/D multipliers 0.80 and 1.20, and admissible incumbents from nested policy sets and the counterpart objective. Candidate K frequencies are individually enumerated from zero to their declared period caps, equal to the larger of one and 1.5 times the observed parent's period departures rounded upward. Fare coordinates enumerate the whole permitted menu. Four alternating rounds are followed by exact radius-one blocks, with at most 20,000 combinations. Blocks pair successive eligible products within a period and successive periods within a product; a residual coordinate forms a singleton. Frequency and fare blocks remain distinct. Polishing stops on no strict improvement or after 16 passes. Feasible candidates outrank infeasible candidates; among the latter the normalized sum of finance, retention and load violations is minimized, then the objective breaks ties. Exact ties retain the incumbent/first enumerated design. Eight worker processes execute independent cells with single-thread numerical libraries.
'''
    sec+=figure(5,'A single demand pass supports repeated exact block screening and independent verification. The lanes separate experiment control, upper-level search, demand evaluation and constraint/audit operations. Dashed arrows indicate repeated search passes; the local stability check does not bound the global optimum.','fig:solution_workflow')
    sec+=r'''
\begin{table}[htbp]\centering\caption*{Algorithm 1. Structured search with fixed observed frequencies}
\begin{tabular}{@{}rp{.88\textwidth}@{}}
1 & Load the fingerprinted case, market state, policy restrictions and tariff grid.\\
2 & Fix all observed $N_{sh}=N^0_{sh}$ and all K multipliers to one.\\
3 & Screen the reference, boundary-fare and admissible nested/counterpart starts.\\
4 & Rank feasibility first, violation second if infeasible, and objective last.\\
5 & Enumerate each eligible candidate-frequency coordinate over its full bounds.\\
6 & Enumerate each fare coordinate over the permitted common or seat-specific grid.\\
7 & Repeat steps 5--6 for at most four rounds; stop early on no improvement.\\
8 & Pair successive eligible coordinates by period and by product; cap enumeration.\\
9 & Enumerate radius-one blocks; repeat until stable or 16 polishing passes.\\
10 & Retain the incumbent on ties and enforce nested-policy feasible-witness closure.\\
11 & Save decisions, outcomes, input/code hashes and search metadata.\\
12 & Independently re-evaluate the saved design and its prescribed local blocks.\\
\end{tabular}\end{table}

\paragraph{Verification and interpretation.}
An independent scalar implementation recomputes utility, every nesting level, flows, revenue, cost, welfare, retention and segment loads from saved decisions. Further checks cover modal conservation, fixed decisions and tariff menus, input fingerprints, and nested-policy dominance. All 2,622 main and no-financial-floor records pass; the maximum objective discrepancy is below $10^{-7}$ CNY and the flow-conservation discrepancy below $6\times10^{-11}$ trips. An independently reconstructed radius-one audit covers 453 unique feasible P3/P4 design--objective configurations and finds no improving block. E1 includes 12 partial reoptimizations, and six E3 events are confirmed with eight rounds. These checks establish numerical consistency and stability in the declared neighborhood, without certifying global optimality. The full 564-cell job list took approximately 254 seconds with eight workers; the archive separates logical design counts, duplicate policy identities, and actual search effort.

\subsection{Reference state: value and mechanics of control}\label{subsec:reference_results}
\paragraph{Policy-value attribution.}
Table~\ref{tab:baseline_policy_values} reports all reference policies. Reference profits are CNY 1,169.7, 1,914.3, and 1,527.9 thousand in HN, WC, and JX, determined by the calibrated operating ratio. P3 raises profit by 0/2.7/28.9 thousand and welfare by 0/0/5.3 thousand. The joint-control increment $\Delta_{\mathrm{incr}}=Z(\mathrm{P3})-\max\{Z(\mathrm{P1}),Z(\mathrm{P2})\}$ is exactly zero because P3 and P1 have the same available decisions. This is an instrument restriction, not evidence of economic independence between fare and frequency in the general model. Holding P3 frequencies and reoptimizing fares, or holding its fares and reoptimizing frequencies, reproduces the saved objective; the own/interaction attribution adds no value beyond fare-only adjustment.
\input{tables/v3_reference.tex}
'''
    sec+=figure(6,'Fixed observed timetables eliminate an independent frequency step in the reference policy ladder. Rows denote profit and welfare, columns HN/WC/JX; bars are CNY thousand/day. The fare step contains the entire P3 gain, while the joint and additional-K increments are zero. All corridors have zero adjustable reference departures.','fig:reference_policy_ladder')
    sec+=r'''
\paragraph{Operating mechanism and binding limits.}
All observed departures remain 118/18/11 in HN, 136/7/42 in WC and 100/37/53 in JX for G/D/K. P4 adds no reference K. The fare matrix therefore reports a repricing problem on fixed supply, not frequency rationalization. WC and JX profit designs use the limited headroom between 0.92 and 0.95; their maximum loads reach 0.9441 and 0.9499, while low-income retention remains 0.9997 and 0.9988. The JX welfare design instead has a maximum load of 0.9276 and retention 0.9999. Terminal waiting times do not change; frequency-derived schedule attributes can change only on additional K services, which are inactive here. The operating mechanism is therefore selective repricing within the inherited train plan; observed-service pruning is outside the corridor operator's authority.
'''
    sec+=figure(7,'Reference adjustments are confined to a small number of G/D fare cells. Rows are observed coverage products, columns AM/day/PM/night, with profit and welfare side by side. Hatching marks fixed frequencies; cell text is the common multiplier and color its deviation from one. Dashes denote inactive periods. All frequency changes are zero.','fig:reference_fare_frequency')
    sec+=r'''
\paragraph{OD and class outcomes.}
Panel C of Table~\ref{tab:baseline_policy_values} reports participation and rail share separately for H/M/L. The reference differences are small under the fixed timetable, although low-income participation in the profit design is slightly below the welfare counterpart. Figure~\ref{fig:jiangxi_od_policy_response} preserves the six JX markets and highlights GZ--NC. OD variation remains visible, but its magnitude indicates a limited redistribution of demand across the inherited capacity allocation: train allocations are fixed, and the observed variation is generated by differential product fares and substitution across available products.
'''
    sec+=figure(8,'JX OD outcomes differ modestly under common-fare adjustment on fixed supply. The upper/lower triangles display profit/welfare P3; color is the percentage change in rail trips from P0, and text is P3 thousand rail trips/day. The heavy-bordered GZ--NC cells identify the required market.','fig:jiangxi_od_policy_response',r'.68\textwidth')
    sec+=r'''
\subsection{Market shocks: transmission and regulated feasibility}\label{subsec:scenario_analysis}
\paragraph{Separate transmission channels.}
Figure~\ref{fig:shock_transmission} evaluates P0 under uniform income, polarized income, all-high electrification, and their combination. Mean-matched income states have different class-specific participation, rail, tier and premium-seat responses because $\rho_k\Delta y_{k\xi}$ enters monetary utility separately for each class. Income deterioration reduces low-income participation; cheaper road travel instead raises participation while diverting trips from rail. Thus retention, which counts all modes, need not deteriorate when rail revenue falls. Seat composition changes also reveal why retaining a product does not guarantee adequate capacity in its cheapest seat class.

The lower panels distinguish the threatened constraints. Every one of the 45 E2 cells with electrification violates P0's financial floor. The six no-electrification uniform/polarized cells violate finance, vulnerable retention and seat capacity simultaneously. The three reference cells satisfy all requirements. Cheaper road alternatives partly offset the participation effect of income deterioration, but compound the financial loss. The sign difference is a demand-accounting result within the calibrated model, not an estimate of actual EV-induced mode diversion.
'''
    sec+=figure(9,'Income shocks threaten vulnerable participation, whereas electrification can improve all-mode participation while worsening railway finance. Top: class-colored percentage-point changes under fixed P0, arranged by four shocks and five metrics. Bottom: P0 retention and financial margin across the six road states, with one line per income state. Dashed lines mark the regulatory floors; monetary margins are CNY thousand/day.','fig:shock_transmission')
    sec+=r'''
\paragraph{Feasibility and minimum sufficient instruments.}
Across the 54 cells, only the three reference cells have a feasible witness under any of P0--P4 at $B=0.5$ million/day. Neither P3 recoveries nor K-dependent P4 recoveries are found. Figure~\ref{fig:minimum_policy} records the failed constraints and the minimum sufficient policy set. Because P1=P3 and P0=P2, an independent joint-control gain cannot emerge, even where repricing improves a least-violation design. Those improvements are not reported as feasible policy values. The result supports a narrower operational conclusion: holding the entire observed timetable fixed can make corridor regulation financially demanding, and adding conventional service alone does not recover the declared stressed cells at this budget. It does not prove that no globally feasible design exists in the searched policy sets.
'''
    sec+=figure(10,'The baseline budget supports the three reference cells, while searches find no feasible stressed-cell design. Each corridor facet crosses three income and six electrification states. Light tiles identify P0-sufficient cells; dark tiles indicate unresolved P4 feasibility. F/R/C/N denote the P0 financial, retention, capacity and operational failures. Feasibility is pooled across objectives over 54 cells.','fig:minimum_policy')
    sec+=r'''
\subsection{Portfolio reconfiguration and selective conventional service}\label{subsec:k_reopening}
\paragraph{Portfolios and the seat-relativity test.}
Observed G/D/K shares cannot adjust because every observed product is fixed. The E2 P4 records select no additional K departures, including their least-violation designs in stressed states. Figure~\ref{fig:portfolio_seat_test} therefore displays the inherited portfolio and distinguishes unresolved records by hatching. E6 relaxes seat relativities within G/D while holding the same train counts and K tariff. Only the reference states admit feasible P3/P3-sb comparisons; uniform and polarized states have no feasible pair. Reference seat-specific gains are therefore reported in CNY thousand, avoiding division by a zero P3 gain in HN and the WC welfare problem. Additional profit gains are 0/5.9/16.6 thousand in HN/WC/JX; additional welfare gains are 0/0/5.3 thousand. Thus seat relativities constrain three of the six reference comparisons, without establishing a universally important seat-pricing margin. The failed stressed comparisons do not identify how that gain evolves under polarization.
'''
    sec+=figure(11,'Inherited portfolios are unchanged in E2, while seat-specific pricing exposes a foregone within-train adjustment margin. Top panels show G/D/K departure shares under reference/uniform/polarized income with none/high electrification; numbers are total departures and hatching marks unresolved feasibility. Bottom: the feasible P3-sb minus P3 objective gains in CNY thousand/day; crosses indicate no feasible comparison.','fig:portfolio_seat_test')
    sec+=r'''
\paragraph{K-entry regimes and confirmed events.}
E7 crosses polarization scales 0--1.7 with electrification multipliers 0--1.5. Polarization multiplies the log-income vector, so the low-income level decline at scale 1.7 is $\exp[1.7\ln(0.85)]-1$, about 24.1\%, rather than a linear percentage extrapolation. The grid contains 231 corridor--state cells. Seven yield feasible P3/P4 witnesses (three HN, two WC, two JX); in the other 224, no feasible P4 is found. No grid cell displays an objective-improving or feasibility-restoring K entry at baseline costs. Objective-independent feasibility regimes are pooled before plotting; the profit/welfare columns consequently agree for unresolved and recovery classifications.

E3 nevertheless identifies six confirmed entries among 240 corridor--objective perturbation comparisons: one HN welfare, one JX profit, and four JX welfare cases. All are objective improvements under reductions in K operating cost, with no feasibility-restoration event. The cost factors perturb both observed and candidate K; the incremental entry comparison holds that factor fixed between P3 and P4. They add 2--51 daily K departures; WC contributes none. Cost reductions can therefore induce entry even in the mature HN corridor, while the effect remains concentrated in JX. Table~\ref{tab:k_reopening_events} records each trigger and pattern. These results concern additional dedicated service alongside fixed observed K, not withdrawal and reopening of those trains.
\input{tables/v3_events.tex}
'''
    sec+=figure(12,'Additional K is inactive on the baseline phase grid but can enter under K operating-cost reductions. Top: the 11-by-7 polarization/electrification grid; grey denotes feasible K-inactive cells and dark denotes no feasible P4 found. Orange/blue would denote objective-improving/feasibility-restoring entry. Open markers identify the four E2 reference/polarized and none/all-high states that lie on these axes; other E2 vectors do not. Bottom: confirmed E3 events decompose own revenue, incumbent revenue change and activation cost; dots mark net profit change, in CNY thousand/day. Welfare entry can occur with negative net profit change.','fig:k_phase_events')
    sec+=r'''
\paragraph{Activation channels.}
For the comparison between a feasible no-additional-K design and a feasible P4 design, railway profit changes satisfy
\begin{equation}
 \Delta\Pi=\mathcal R_{\mathrm{new\ K}}+
 \Delta\mathcal R_{\mathrm{inc}}-
 \sum_{s\in\mathcal S_{\mathrm{new}}}\left[c_s^{\mathrm f}+\sum_h\chi_sN_{sh}(c_s^{\mathrm{run}}+c_s^{\mathrm{km}}\ell_s)\right].
 \label{eq:k_activation_threshold}
\end{equation}
The second term measures incumbent cannibalization together with any incumbent repricing. Because the observed train counts are fixed, the incremental operating cost belongs entirely to the new services. Entry is commercially beneficial only when the revenue terms exceed activation cost; welfare additionally includes consumer surplus. The JX profit event at a 0.10 K-cost factor gains CNY 43.7 thousand/day after about 385.0 thousand own revenue, 309.3 thousand incumbent revenue loss and 31.9 thousand activation cost. The welfare events sacrifice profit while increasing traveler surplus, illustrating why profit and welfare activation conditions cannot be conflated.

The event rule assigns coverage when a selected pattern serves the OD-period with the largest vulnerable-trip shortfall or an otherwise uncovered OD-period, affordability when own-market revenue is the dominant positive component, and otherwise cost for cost-only triggers. Under this descriptive rule one event is coverage and five affordability, although all six are triggered by the cost dimension. Trigger provenance and demand channel are therefore both retained. No feasibility-restoration event admits a profit decomposition here; if such an event occurred, its retention and financial margins would be compared to the least-violation P3 record instead.

\subsection{Mobility guarantees and governance}\label{subsec:regulation}
\paragraph{Cost of retention and compensating budgets.}
E4 evaluates five retention floors between 0.900 and 1.000, four budgets between zero and CNY 2 million, and P3/P4 at the reference and polarized/all-high states. The reference curves coincide across budgets because the saved designs remain profitable. The stressed-state grid has no feasible design, even at the largest declared budget; no stressed retention-cost curve is inferred from infeasible objectives. Figure~\ref{fig:retention_budget_equity} explicitly marks this missing feasible frontier instead of drawing a flat line.

Removing the financial floor and maximizing profit subject to the remaining requirements gives $B^*=\max\{0,-\widehat\Pi\}$ for a globally solved problem. Here the saved no-floor profit design supplies an implementable sufficient-budget \emph{upper bound} on that minimum. P3 provides such a design in 45 of the 51 stressed E2 cells; P4 does so in 46. Sufficient budgets are CNY 4.98--6.33 million in HN, 10.24--12.72 million in WC and 7.22--8.23 million in JX for P3. P4 additionally finds a JX no-electrification income-downturn design at about CNY 4.53 million. Thus a budget can recover many financial-only cells, while one further saved recovery requires both an instrument and a larger budget. The remaining searches fail retention/capacity or do not locate an admissible witness; they are not certified as non-budget-fixable.
'''
    sec+=figure(13,'A larger financial allowance is often necessary under fixed observed supply, while the equity diagnostic divergence is absent among feasible saved designs. Top left: reference retention-cost curves; the stressed grid has no feasible curve within CNY 0--2 million. Top right: sufficient-budget upper bounds from P3/P4 no-floor designs, with unresolved counts in the margin. Bottom: changes in worst-case cost ratio and vulnerable retention relative to same-state P0 for feasible saved records; color identifies policy.','fig:retention_budget_equity')
    sec+=r'''
\paragraph{What retention and cost ratios detect.}
X2 pre-specifies the worst OD-period ratio $\max_{wh}G_{wh}$, with the demand-weighted mean as a check, and compares each design to P0 in the same state and calibration. Among 2,520 main saved records, 57 (2.26\%) have both a lower worst-case cost ratio and lower vulnerable retention; the rank correlation between the two changes is $-0.346$. All these divergence cases are infeasible. Among the 494 feasible records, the quadrant is empty and the correlation is 0.149. These are descriptive shares over the archived experiment menu, including repeated policy identities, not population frequencies. The unresolved JX E3 commercial P3 comparison with K running times multiplied by 0.90 lowers the worst cost ratio by 0.00415 and retention by 0.00216, with approximately 125 additional vulnerable nontravelers and 418 fewer vulnerable rail trips; the remaining difference is modal diversion. Because logit gives positive participation probabilities, the discrepancy operates through composition and switching rather than literal disappearance of a demand segment. The experiment therefore illustrates a diagnostic possibility but supplies no feasible-policy example of it.

\paragraph{Commercial versus welfare governance.}
Only one E2 cell per corridor supports the governance comparison. The transfer needed to compensate the welfare design's lower railway profit is CNY 0/2.7/16.7 thousand/day in HN/WC/JX; the corresponding welfare improvement over the commercial design is 0/10.4/47.6 thousand. For WC and JX the transfer-to-gain ratios are 0.259 and 0.351; HN's 0/0 ratio is left undefined. Figure~\ref{fig:governance_plane} uses consumer-surplus change on the vertical axis, so rail profit is counted only once. A compensation amount is an accounting gap at the saved designs, not an incentive-compatible contract derived from a strategic subsidy game.
'''
    sec+=figure(14,'The reference governance gap is concentrated in traveler surplus rather than train-count reallocation. Filled/hollow markers denote commercial/welfare P4 designs in each feasible E2 cell, connected as pairs. Both axes are CNY thousand/day; the vertical coordinate is consumer-surplus change relative to same-state P0. Light diagonals indicate equal railway-centered welfare. Only the reference state is feasible in each corridor.','fig:governance_plane')
    sec+=r'''
\paragraph{Numerical and calibration sensitivity.}
Table~\ref{tab:governance_robustness} separates implementable comparisons from unresolved runs. Eight rounds leave the six base P3 objectives unchanged. The 0.025 grid increases JX welfare by about CNY 6.95 thousand, while the 0.10 grid reduces JX profit by about CNY 3.06 thousand; zero base welfare values are not used as percentage denominators. Share shifts and a 1.00 load ceiling provide further sensitivity evidence. The scale tests deliberately hold calibrated intercepts fixed while varying $\mu_{\mathrm{sc}}$ or $\mu_{\mathrm{pr}}$ by 0.05. Twenty of the 24 scale-test records have no feasible design, demonstrating calibration fragility rather than supporting parameter-invariant findings. These tests perturb both substitution and the fitted reference logsums; they should not be interpreted as re-estimated demand models. The fixed-frequency policy identities are structural, while fare gains, K-entry events, budgets and governance gaps remain calibration-dependent.
\input{tables/v3_governance.tex}

\section{Discussion and conclusion}\label{sec:conclusion}
\begin{table}[htbp]\centering\caption{Principal findings under fixed observed frequencies}\label{tab:key_findings}
\begin{tabular}{@{}p{.36\textwidth}p{.57\textwidth}@{}}\toprule
Finding & Evidence and scope\\\midrule
Inherited timetables restrict instruments & P2=P0 and P3=P1; common-fare reference profit gains are 0--28.9 thousand CNY/day.\\
Shocks threaten different obligations & 45 P0 cells fail finance; six further cells fail finance, retention and capacity.\\
Additional K is conditional & No baseline E2 recovery; six E3 gain events, all under K cost reductions.\\
Money and operating instruments interact & Sufficient no-floor budgets found in 45 P3 cells and 46 P4 cells.\\
Seat and calibration assumptions matter & Reference seat-specific pricing adds value; 20/24 fixed-intercept scale tests lack feasibility.\\\bottomrule
\end{tabular}\end{table}

The framework links railway product availability, integer departures and tariff menus to elastic participation, mode choice, train-product choice and seat choice. Class-specific income changes and road electrification act through distinct monetary-utility channels. The case study implements a deliberately restrictive governance boundary: every observed train frequency is fixed by the inherited network timetable, while extra dedicated K services can be added. The resulting P0=P2 and P1=P3 identities prevent attribution of frequency-rationalization gains to a corridor operator without authority to alter the observed timetable.

At the reference state, common G/D repricing yields modest gains: CNY 0--28.9 thousand/day in railway profit and 0--5.3 thousand in railway-centered welfare. In the 54-cell stress matrix only the three reference cells yield feasible designs at the CNY 0.5 million loss allowance. Financial-only failures dominate electrification states, while no-electrification income downturns additionally threaten low-income retention and seat capacity. No baseline K-dependent recovery is found. The wider sensitivity experiment instead confirms six additional-service events under lower K operating costs, including an HN welfare event and five JX events. Conventional service consequently remains conditional, with operating-cost reductions sufficient to induce entry in a small subset of the sensitivity menu.

The regulatory implications concern instrument authority as well as budget size. A higher budget supports many saved designs that meet retention and capacity after the financial floor is removed; a further JX case requires both additional K and a sufficient budget. A budget is therefore not a substitute for every missing operating instrument, and the absence of a witness under a heuristic is not an impossibility proof. The reference welfare design requires a profit transfer of about CNY 2.7 thousand in WC and 16.7 thousand in JX. Relaxing G/D seat relativities offers a further adjustment margin, qualifying any assertion that portfolio redesign is inherently necessary to accommodate polarized travelers.

These findings inherit substantial evidence limitations. Passenger volumes, seat counts, utility constants and costs are calibrated rather than estimated from traveler choices, formations or accounts. Through-passenger loads and corridor cost shares are unidentified and set to explicit conventions; rail operating lengths use road-distance proxies, and the two track-type resource chains are stylized. Their financial and capacity implications should be revisited with full train routes, physical rail distances and segment occupancy. Candidate preferences are transferred from observed K families, so their entry values remain sensitive to that extrapolation. Holding constants fixed in scale tests exposes the fragility of fitted reference shares, and no mechanism-level robustness to arbitrary demand parameters is claimed.

The model contains no crowding disutility beyond the planned 0.95 load ceiling, no tactical seat rationing, and no strategic road-supplier response. Adding departures can change both crowding and competitor behavior in ways the present scenarios omit. Daily fleet hours relax simultaneous vehicle circulation, and product coverage is reconstructed only within the modeled cities. Finally, exact demand evaluation, scalar verification and local block stability do not supply a global-optimality or global-infeasibility certificate. Future work should estimate the demand system, identify network cost and capacity allocation, model circulation and road responses, and compare corridor-level authority with genuine timetable reconfiguration under richer data.

\bibliography{TRA-references,TRA-v3-policy-references}
\end{document}
'''
    backup=PAPER/'archive'/'before_v3_experiments_20261014'; backup.mkdir(parents=True,exist_ok=True)
    original=PAPER/'TRA-20261014-V3.tex'
    if original.exists() and not (backup/original.name).exists(): shutil.copy2(original,backup/original.name)
    write('TRA-20261014-V3.tex',head+sec)

if __name__=='__main__':
    tables(); manuscript()
    for n in [3,4,6,7,8,9,10,11,12,13,14]: (ROOT/f'fig{n:02d}.py').write_text(f'from figures import main\nmain({n})\n',encoding='utf-8')
    print('V3 and six empirical tables written.')
