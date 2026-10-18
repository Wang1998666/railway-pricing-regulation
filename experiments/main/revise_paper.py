"""Revision requested on 14 October: partial authority, informative plots, compact tables."""
import ast,json,re,shutil
from pathlib import Path
import numpy as np
from model import ROOT,Model
from analyze import groups,record,pair_feasible
from write_paper import figure

PAPER=ROOT.parent
A=json.loads((ROOT/'analysis.json').read_text(encoding='utf-8'))
C={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']}
REF={ci:next(g for g in groups('E2') if g['job']['id']==f'{ci}_reference_none') for ci in C}
def fmt(v,d=1): return f'{v:.{d}f}'
def row(v): return ' & '.join(map(str,v))+r' \\'+'\n'
def write(p,s): (PAPER/p).write_text(s,encoding='utf-8')
def panel(title,cols,header,rows):
    cols=re.sub(r'p\{([^}]+)\}',lambda m:r'>{\raggedright\arraybackslash}p{'+m[1]+'}',cols)
    return r'\par\noindent\textbf{'+title+r'}\par\smallskip'+'\n'+r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}'+cols+r'@{}}\toprule'+'\n'+row(header)+r'\midrule'+'\n'+rows+r'\bottomrule\end{tabular*}\par\medskip'+'\n'
def table(name,caption,label,body,note='',continued=False):
    s=r'\begin{table}[htbp]\centering'+('\n'+r'\ContinuedFloat' if continued else '')+'\n'+r'\caption{'+caption+'}'+('' if continued else r'\label{'+label+'}')+'\n'+r'\begin{minipage}{.95\textwidth}\fontsize{8}{10}\selectfont\setstretch{1.0}\setlength{\tabcolsep}{2pt}\renewcommand{\arraystretch}{1.10}'+'\n'+body+r'\par\noindent\fontsize{8}{9.5}\selectfont '+note+'\n'+r'\end{minipage}\end{table}'+'\n'
    write('tables/'+name,s)

def tables():
    rows=''
    for ci,c in C.items():
        m=Model(c); ps=c['products']; counts=[sum(p['tier']==t and not p['candidate'] for p in ps) for t in ['G','D','K']]
        rows+=row([ci,f'{len(c["cities"])}/{len(c["ods"])}',2*(len(c['cities'])-1),fmt(max(c['road_km'])),str({'HN':1124,'WC':1297,'JX':3464}[ci])+'/'+str({'HN':160,'WC':185,'JX':494}[ci]),'/'.join(map(str,counts)),f'{int((m.N0-m.Nmin).sum())}/{int(m.Nmin.sum())}',sum(p['candidate'] for p in ps)])
    table('v3_structure.tex','Corridor structure and operating authority','tab:formal_case_data',panel('Reference supply and modeled coverage','lrrrrlrr',['Case','Nodes/ODs','Segments','Road km','Week/ref.','G/D/K families','Adj./prot.','K cand.'],rows),'Week/ref. counts OD query records; unique reference trains number 147/185/190. Adjustable/protected counts apply integer rounding within each G/D product--period, with all observed K protected. Seat capacities and resource chains are calibration assumptions. Road km gives the longest modeled OD, not measured railway length.')
    tree=ast.parse((ROOT/'write_paper.py').read_text(encoding='utf-8'))
    func=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='tables')
    params=ast.literal_eval(next(x.value for x in func.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='params' for t in x.targets)))
    changes={
      'Observed frequency':('G/D adjustment share',r'$\theta$','0.50','0.25/0.75 in E5','Scenario'),
      'Incumbent G/D daily floor':('Incumbent G/D daily floor',r'$\underline N_s^{\mathrm{day}}$','1','positive daily service','Regulatory')}
    params=[changes.get(p[0],p) for p in params]
    params.insert(next(i for i,p in enumerate(params) if p[0]=='Fare menu G/D'),('Observed K frequency',r'$N_{sh}$',r'$N^0_{sh}$','fixed in all policies','Regulatory'))
    split=next(i for i,p in enumerate(params) if p[0].startswith('D. Supply'))
    for part,ps in enumerate([params[:split],params[split:]]):
        rows=''
        for cat,sym,val,unit,prov in ps:
            if not sym and not val: rows+=r'\multicolumn{5}{l}{\textbf{'+cat+r'}}\\\addlinespace'+'\n'
            else: rows+=row([cat,sym,val,unit,prov])
        body=panel('Calibration and assumptions' if part==0 else 'Supply, regulation, and states',r'p{.26\linewidth}p{.13\linewidth}p{.21\linewidth}p{.22\linewidth}p{.12\linewidth}',['Parameter','Symbol','Value','Meaning/unit','Source type'],rows)
        table('v3_parameters'+('' if part==0 else '_continued')+'.tex','Calibration, supply assumptions, and market states'+(' (continued)' if part else ''),'tab:calibration_parameters',body,'Preference magnitudes are literature-anchored; no econometric identification is claimed. Timetables and quoted fares are observed; access medians and costs are derived or calibrated. Full coefficients are archived. The exploratory E8 budget is 14 million CNY/day; E9 and E10 grids are described in the text.',continued=bool(part))
    rows=''
    designs=[('E1','Instrument attribution','Reference plus fixed-fare/fixed-frequency reoptimizations','P0--P4','30 reused + 12'),('E2','Stress and feasibility','3 income states; 6 road states','P0--P4','540 + 102'),('E3','K-entry sensitivity','40 perturbations in 11 dimensions','P3/P4','480'),('E4','Retention and budget','2 states; 5 floors; 4 budgets','P3/P4','480'),('E5','Numerics and authority','Grid, rounds, scales, loads, shares; 0/25/75\% authority','P3','78'),('E6','Seat relativities','3 income states, no electrification','P3/P3-sb','36'),('E7','Original phase grid','11 polarization; 7 road-saving scales','P3/P4','924'),('E8','Governance extension','E2 states; budget 14 million/day','P3/P4','216'),('E9','Retention boundary','Fine reference floors; quarter-polarized income','P3/P4','156'),('E10','K-entry boundary','7 K cost factors; 7 weak road-saving scales','P3/P4','588')]
    for d in designs: rows+=row(d)
    table('v3_experiments.tex','Planned experiments and targeted extensions','tab:experiment_overview',panel('Experiment inventory',r'lp{.19\linewidth}p{.39\linewidth}lp{.15\linewidth}',['ID','Question','Design','Policies','Records'],rows),'Counts include both objectives and three corridors. E2 adds 102 no-financial-floor profit records. E1 reference records are reused. E8--E10 are targeted extensions; all original E2--E7 grids, including null responses and unresolved searches, remain in the archive. No policy identities are used to skip frequency searches at the 50\% baseline.')
    rows=''
    for x in A['reference']:
        rows+=row([x['case_id'],x['objective'][0].upper(),*[fmt(x['values'][p]/1000) for p in ['P0','P1','P2','P3','P4']],fmt(x['joint_gain']/1000),fmt(x['joint_increment']/1000)])
    body=panel('A. Objective values and gains (CNY thousand/day)','llrrrrrrr',['Case','Obj.','P0','P1','P2','P3','P4','Joint gain','Joint incr.'],rows)
    rows=''
    for ci,c in C.items():
        tiers=np.array([p['tier'] for p in c['products']])
        for pol,obj in [('P0','profit'),('P3','profit'),('P3','welfare')]:
            r=record(REF[ci],pol,obj); N=np.array(r['N']); ph=np.array(r['phi'])[:,:,0]; gd=tiers!='K'; mean=float((N[gd]*ph[gd]).sum()/N[gd].sum())
            rows+=row([ci,pol+obj[0].upper(),'/'.join(str(int(N[tiers==t].sum())) for t in ['G','D','K']),fmt(mean,3),fmt(r['maxlf'],4),fmt(r['eta'],4),fmt((r['profit']+500000)/1000),fmt(.95-r['maxlf'],4)])
    body+=panel('B. Operations and constraint margins','lllrrrrr',['Case','Policy','G/D/K',r'$\bar\phi_{GD}$',r'$\lambda^{\max}$',r'$\eta^{L}$','F margin','C headroom'],rows)
    rows=''
    for ci in C:
        p=record(REF[ci],'P3','profit'); w=record(REF[ci],'P3','welfare')
        for k,cl in enumerate(['H','M','L']): rows+=row([ci,cl,fmt(p['class_trips'][k]/p['class_potential'][k],4),fmt(p['rail_by_class'][k]/p['class_trips'][k],4),fmt(w['class_trips'][k]/w['class_potential'][k],4),fmt(w['rail_by_class'][k]/w['class_trips'][k],4)])
    body+=panel('C. P3 participation and rail share by class','llrrrr',['Case','Class','Participation P','Rail share P','Participation W','Rail share W'],rows)
    table('v3_reference.tex','Reference-state policy values, operations, and class composition','tab:baseline_policy_values',body,'P/W denote the commercial/welfare objective. Joint gain is P3 minus P0; joint increment is P3 minus the better of P1 and P2. Financial margin is profit plus the 500-thousand budget; capacity headroom is 0.95 minus maximum seat load. Mean G/D fares are departure weighted.')
    rows=''
    for e in A['events']:
        factor=e['trigger'].split('_k_cost_')[-1]
        rows+=row([e['case_id'],e['objective'][0].upper(),factor,e['departures'],', '.join(e['patterns']),fmt(e['profit_change']/1000)])
    table('v3_events.tex','Additional-K events in the operating-cost sensitivity','tab:k_reopening_events',panel('E3 entries alongside fixed observed K',r'llrrp{.38\linewidth}r',['Case','Obj.','K cost factor','New K/day','Candidate IDs',r'$\Delta\Pi$ (k)'],rows),'All events improve the searched objective and are rechecked with eight rounds. K cost factors apply to observed and candidate K alike. New K/day excludes observed K; profit changes compare P4 to P3 under the same cost factor. These are conditional entry events, not baseline feasibility recoveries.')
    rows=''
    for ci in C:
        rs=[r for r in A['governance'] if r['case_id']==ci]; pp=[r['profit_gap']/1000 for r in rs]; ww=[r['welfare_gap']/1000 for r in rs]
        rows+=row([ci,len(rs),fmt(np.median(pp)),fmt(min(pp))+'--'+fmt(max(pp)),fmt(np.median(ww)),fmt(min(ww))+'--'+fmt(max(ww))])
    body=panel('A. Governance gaps in feasible E8 P4 pairs (CNY thousand/day)','lrrrrr',['Case','Pairs','Profit median','Profit range','Welfare median','Welfare range'],rows)
    rows=''
    for ci in C:
        for pol in ['P3','P4']:
            rs=[r for r in A['budgets'] if r['case_id']==ci and r['policy']==pol]; vals=[r['Bstar_upper_bound']/1e6 for r in rs if r['budget_fixable_found']]
            rows+=row([ci,pol,len(vals),fmt(min(vals),2)+'--'+fmt(max(vals),2),sum(not r['budget_fixable_found'] for r in rs)])
    body+=panel('B. Sufficient budgets among 17 stressed E2 cells per corridor','llrrr',['Case','Policy','Witnesses','Budget range (million)','Unresolved'],rows)
    rows=''
    for test in ['grid025','grid10','rounds8','mu_sc_low','mu_sc_high','mu_pr_low','mu_pr_high','lambda1','lowheavy','highheavy','authority0','authority25','authority75']:
        rs=[r for r in A['robustness'] if r['test']==test]; good=[r for r in rs if r['feasible']]; vals=[abs(r['deviation_percent']) for r in good if r['deviation_percent'] is not None]
        rows+=row([test.replace('_',' '),f'{len(good)}/6',fmt(np.mean(vals),2) if vals else '--',fmt(max(vals),2) if vals else '--',fmt(max([abs(r['absolute_deviation'])/1000 for r in good],default=0),2)])
    body+=panel('C. E5 objective deviations from reference P3','lrrrr',['Test','Feasible/6','Mean abs. \%','Max abs. \%','Max abs. thousand'],rows)
    table('v3_governance.tex','Governance, sufficient budgets, and numerical sensitivity','tab:governance_robustness',body,'E8 uses a 14-million budget, distinct from the baseline 0.5 million. Budgets in B are implementable sufficient-budget upper bounds from best-found no-floor designs. Unresolved searches are not impossibility certificates. Scale tests keep calibrated intercepts fixed. Authority tests change the G/D adjustment share; observed K remains fixed.')

def manuscript():
    source=(PAPER/'archive'/'before_visual_revision_20261014'/'TRA-20261014-V3.tex').read_text(encoding='utf-8')
    head=source[:source.index(r'\clearpage'+'\n'+r'\section{Case study}')]
    head=head.replace(r'\usepackage{longtable,caption}',r'\usepackage{caption}')
    head=head.replace(r'\usepackage{caption}',r'\usepackage{caption,placeins}')
    head=head.replace('through-services with frequencies fixed at', 'services under fixed-frequency obligations at')
    head=head.replace('Aggregate traveler benefit is evaluated', r'Applications may also place explicitly protected services in $\mathcal S^{\mathrm{fix}}$ without identifying them as through-services. Aggregate traveler benefit is evaluated')
    abstract='The application protects half of each observed G/D product--period supply and fixes observed K frequencies. Joint fare--frequency control raises reference daily profit by CNY 282--472 thousand and railway-centered welfare by CNY 192--418 thousand in three calibrated Chinese corridors. Joint control improves on the better single instrument in two corridors, while additional conventional entry remains conditional. Only the three reference cells have feasible witnesses in the 54-cell stress matrix at the baseline loss allowance; no-floor searches identify sufficient budgets for 45 stressed cells under incumbent control and 46 with additional K. Refined cost and competition grids reveal selective K entry, and an expanded-budget comparison separates commercial and welfare designs. The results show how operating authority, financial support and vulnerable-trip guarantees jointly condition the preferred portfolio.'
    head=re.sub(r'The application fixes the frequencies of all observed trains,.*?(?=\n\\end\{abstract\})',lambda m:abstract,head,flags=re.S)
    intro='The application gives the corridor operator limited authority: half of each observed G/D product--period supply is protected and all observed K frequencies remain fixed. Reference joint-control profit gains are CNY 282--472 thousand/day, with positive gains over the better single instrument in WC and JX. The stress matrix, targeted entry grids and budget extensions distinguish effective operating responses from cases requiring greater financial support. They also reveal feasible designs in which a lower realized-traveler cost ratio accompanies lower vulnerable participation, motivating an explicit trip-retention requirement.'
    head=re.sub(r'The application deliberately holds all observed train frequencies fixed\..*?(?=\n\nThe remainder)',lambda m:intro,head,flags=re.S)
    anchor='The policy sets compared in Section~'
    at=head.index(anchor)
    head=head[:at]+r'Where a protected departure quota is positive, period operation $u_{sh}=1$ is imposed and the corresponding lower bound includes that quota; products in $\mathcal S^{\mathrm{fix}}$ retain their exact reference frequencies. '+head[at:]
    sec=r'''
\clearpage
\section{Case study}\label{sec:case}\label{sec:case_design}\label{sec:results}
The application examines fare, frequency and portfolio decisions under limited corridor-level authority. The baseline permits adjustments to 50\% of each observed G/D product--period supply, subject to integer rounding, while all observed K departures remain fixed. Additional dedicated K services form a separate decision margin. The original stress experiments are retained; targeted extensions resolve entry, retention and governance boundaries that were poorly distinguished by the coarse grids. All monetary outcomes are calibrated counterfactuals for one direction of travel per modeled day.

\subsection{Corridors, data, and calibration}\label{subsec:case_settings}\label{subsec:corridor_data}
\paragraph{Geography and source boundaries.}
Hangzhou--Nanjing (HN) represents a mature high-speed market, Wuhan--Changsha (WC) a rail--road competitive market, and Ganzhou--Ji'an--Nanchang--Jiujiang (JX) a four-node corridor containing all six forward ODs, including Ganzhou--Nanchang. Context follows the cited transport reports \citep{NinghangHSR2013,WuhanChangshaPopularOD2026,ChinaGovChanggan2019,NanchangGovChanggan2019}. Archived 12306 queries cover travel dates 3--9 August 2026, with Wednesday 5 August defining the reference design; metadata preserve the earlier query timestamps. Amap distance, duration, toll and access fields are routing snapshots rather than realized passenger travel times \citep{ChinaRailway12306,AmapWebService2026}.

Figure~\ref{fig:corridor_structure} restores the archived road trajectories on their geographic basemaps. Blue railway lines supply geographic context from Natural Earth and, in JX, mapped OpenStreetMap geometry \citep{NaturalEarthRailroads,OSMRailwayMap}. These generalized network lines are not reconstructed paths of individual observed trains and do not identify which services are through trains. Train and car icons distinguish the transport modes; the accompanying supply cards report assumed seats and protected/adjustable departures.
\input{tables/v3_structure.tex}

\paragraph{Products and operating authority.}
Observed products group train numbers with the same tier and exact coverage of the modeled ODs. Distinct stopping-coverage signatures remain distinct; missing intermediate stations and full-train endpoints are not inferred. HN and WC each have one observed family per tier; JX has 21 observed coverage products. Each observed K family also supplies a zero-reference-frequency additional candidate, yielding 1/1/10 candidates. These are extra dedicated services alongside observed K, rather than withdrawal and reopening of the observed trains.

The 50\% authority scenario protects the reference G/D count multiplied by 0.50 and rounded upward within each product and period. The upper bound is the reference count plus half that count rounded downward, with at least two permitted departures in a G/D period. Thus a zero-reference period can gain up to two departures. Every observed G/D product retains at least one daily departure, and OD-period service floors remain in force. Observed K frequencies and all K fare multipliers are fixed. This aggregate quota is a maintained planning scenario, not evidence identifying particular train numbers as adjustable. The sensitivity analysis considers 25\%, 75\% and zero G/D authority using the same rounding rule; zero authority restores the fully inherited timetable.

Two schematic resource chains separate high-speed/EMU and conventional use. Route incidence follows a product's full in-corridor span, whereas passenger incidence follows its passenger subpath. D assignment to the high-speed/EMU chain is a stylized convention. Road distances proxy operating length where railway kilometrage is absent. Path envelopes equal the larger of 16 departures per hour times period duration and reference use plus four reserve paths. Round-trip cycles equal twice the maximum observed running time plus one hour; fleet-hour envelopes cover the reference timetable and the declared candidate allowance. These are strategic resource assumptions rather than a vehicle-circulation reconstruction.

Background occupancy is set to zero and corridor cost shares to one because neither can be identified in the archival files. Capacities of 690/552/1368 seats for G/D/K are assumed formations. Observed data therefore comprise dated train and fare responses and routing attributes; demand, formations, resource envelopes, costs and utility constants are calibrated. This boundary is material for interpreting financial and capacity outcomes.
'''
    sec+=figure(3,r'Geographic road trajectories, railway context, and modeled supply. Red lines reproduce archived Amap road geometry from the preceding manuscript; blue dashed lines show the mapped railway network, not individual train paths. Icons distinguish railway and road modes. Road labels use the current input distance of the longest OD; seats are assumed formation capacities summed over reference departures. Teal/hatched bars distinguish adjustable/protected reference departures under integer 50\% G/D quotas and fixed observed K. Basemap attribution: OpenStreetMap contributors and CARTO.','fig:corridor_structure')
    sec+=r'''
\paragraph{Demand and utility calibration.}
The periods 06:00--09:00, 09:00--17:00, 17:00--20:00 and 20:00--06:00 last 3/8/3/10 hours. A unique train is assigned by its earliest modeled boarding city. Reference passengers are allocated across a product's served ODs in inverse proportion to road distance, with the weights normalized by the busiest shared segment. Departure counts and assumed seats are multiplied by initial G/D/K loads of 0.78/0.72/0.70 and a common rescale of 0.92 divided by 0.78. This sets the maximum reference segment load to 0.92 without double counting passengers on multi-OD paths. Potential travelers follow class shares 0.20/0.60/0.20, participation 0.85, and OD rail-share targets 0.70/0.60/0.55/0.45 in distance bands up to 350/500/800/beyond 800 km. Period populations follow observed supply. Road and auto receive 60\%/40\% of nonrail trips; coach, MaaS and van receive 75\%/22\%/3\% within road.

Nested constants are calibrated recursively from these target shares, absorbing non-leaf level shifts into leaf intercepts under the normalization in Section~\ref{sec:demand_model}. The reference participation and rail-flow targets are reproduced to numerical precision. Candidate preferences are transferred from their observed K parent, adjusting the product constant for the parent's reference departure count; an empty parent period borrows the nearest active period. These are explicit extrapolations rather than estimates of demand for unobserved new services. Reference running and commitment costs are jointly rescaled to 92\% of rail revenue; candidate restart commitments equal 10\% of the parent's fixed allocation. Table~\ref{tab:calibration_parameters} records the coefficients and their provenance.
\input{tables/v3_parameters.tex}
\input{tables/v3_parameters_continued.tex}

\paragraph{Market states and regulation.}
Reference income has zero log change. Polarization assigns H/M/L level changes of +2/--8/--15\%. The class-weighted mean log change is --0.078572, so the matched uniform level decline is 7.56\%, rather than the arithmetic 7.4\%. The six road states are none, auto only, auto plus MaaS/van with low/high pass-through, and all road alternatives with low/high pass-through. Auto exposure is 0.50 of a 0.58 CNY/km saving; fare pass-through is 0.30/0.70 of MaaS/coach/van savings of 0.20/0.12/0.30 CNY/km. The initial budget is 500,000 CNY/day, vulnerable-trip retention is 0.95, and the seat-load ceiling is 0.95. OD-period floors equal the smaller of one and observed departures. G/D common multipliers range from 0.80 to 1.20 in steps of 0.05. The fixed K tariff also covers soft sleepers as a conservative common-multiplier convention, rather than a claim that all sleeper fares are government-set.
'''
    sec+=figure(4,r'Equal mean income shocks have different class-specific VOT effects, while electrification changes road monetary costs through a separate channel. The WC alluvial carries class-colored reference trips through participation, modes, tiers and seats; widths are thousand trips/day. Lower panels show VOT and endpoint road costs; filled/hollow markers denote none/all-high electrification. Seat labels 1--3 follow Table~\ref{tab:calibration_parameters}.','fig:calibration_shocks')
    sec+=r'''
\subsection{Policy sets, experiments, and solution procedure}\label{subsec:solution_protocol}\label{subsec:policy_sets}\label{subsec:experiments}
\paragraph{Policies and experiment domains.}
P0 fixes the reference design. P1 adjusts G/D common fares at reference frequencies. P2 adjusts G/D frequencies within the authority bounds at reference fares. P3 combines these instruments with candidates off; P4 additionally permits dedicated K departures. P3-sb relaxes G/D seat relativities while retaining the same frequency bounds and K tariff. At 50\% authority, P2 and P3 are independent searches rather than copies of P0 and P1. Only the zero-authority control has the structural identities P2=P0 and P3=P1.

The original E1--E7 inventory is retained. Three extensions clarify boundaries instead of changing the reference calibration to produce visual differences. E8 repeats the 54 market states at a deliberately generous 14-million daily budget; this exploratory envelope was selected to exceed the preceding fully fixed-timetable no-floor requirements. E9 uses reference retention floors 0.98/0.99/0.995/1.00/1.0025/1.005 at the baseline budget, and quarter-strength polarized log-income shocks with floors 0.90/0.92/0.94/0.95/0.96/0.98/1.00 at the expanded budget. E10 crosses K cost factors 0.10/0.25/0.40/0.55/0.70/0.85/1.00 with road-saving intensities 0/0.02/0.04/0.06/0.08/0.12/0.20, retaining reference income, high pass-through and the baseline budget. K cost factors apply to observed and candidate K alike. These extensions are diagnostic and do not replace the original coarse stress results.
\input{tables/v3_experiments.tex}

\paragraph{Search and verification.}
The vectorized Python implementation evaluates the nested demand system in one pass. Starts comprise the reference, boundary tariffs, reduced/increased G/D supply, admissible nested-policy solutions and the counterpart objective. Each eligible frequency coordinate enumerates its full integer bounds; each fare coordinate enumerates its entire grid. Four alternating rounds are followed by exact radius-one blocks pairing adjacent eligible products or periods, with at most 20,000 combinations per block and 16 polishing passes. Candidate K caps equal the larger of one and 1.5 times the parent's period departures rounded upward. Feasible designs outrank infeasible designs; the normalized violation sum ranks unresolved candidates before the objective. Exact ties retain the incumbent.
'''
    sec+=figure(5,'The solution and verification workflow, with distinct experiment, search, demand and audit lanes. Solid arrows transmit data and response measures; dashed arrows return search feedback; dotted arrows identify the verification path. Protected G/D supply and fixed observed K enter the authority screen before optimization. The audit establishes consistency and stability in the declared neighborhood, without a global-optimality certificate.','fig:solution_workflow')
    v=json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))
    local=json.loads((ROOT/'local_audit.json').read_text(encoding='utf-8')) if (ROOT/'local_audit.json').exists() else None
    assert local is not None and not local['failures'], 'Complete local audit before manuscript generation'
    conf=json.loads((ROOT/'E3_confirmations.json').read_text(encoding='utf-8')); assert all(x['confirmed'] for x in conf)
    sec+='\nAn independent scalar implementation recomputes all nested utilities, flows, revenue, cost, welfare, retention and seat loads. All '+f'{v["records"]:,}'+r' saved main and no-financial-floor records pass, with maximum profit/welfare discrepancies below $10^{-7}$ CNY and conservation error below $9\times10^{-11}$ trips. The independently reconstructed local audit covers '+f'{local["unique_feasible_design_objectives"]:,}'+r' unique feasible P3/P4 design--objective configurations and '+f'{local["checked_candidates"]:,}'+r' block candidates without an improving move. Twelve E1 partial reoptimizations and '+str(len(conf))+r' E3 event confirmations use eight rounds. The 813 jobs required approximately 18 minutes with eight workers. Failure to find a feasible witness remains unresolved feasibility, not an impossibility certificate. Feasibility is pooled across objectives because both use the same constraints; no pre-closure search discrepancy is found in E2.'+'\n'
    sec+=r'''
\subsection{Reference state: value and mechanics of control}\label{subsec:reference_results}
\paragraph{Instrument value.}
Reference profits are CNY 1,169.7/1,914.3/1,527.9 thousand/day in HN/WC/JX under the calibrated operating ratio. P3 increases profit by 313.4/472.1/282.4 thousand and railway-centered welfare by 301.4/418.0/192.4 thousand. The joint gain over the better single instrument is zero in HN, 23.4/22.1 thousand in WC under profit/welfare objectives, and 29.3/5.3 thousand in JX. HN is therefore a genuine frequency-driven case: common repricing adds no further value at the searched reference optimum. WC and JX exhibit a useful joint margin. Additional K has zero reference increment in all three corridors, which is retained as a substantive null result rather than concealed by plotting choices.

The E1 partial reoptimizations hold one instrument at its optimized P3 value while reoptimizing the other. All twelve reproduce the joint objective, so the residual interaction beyond these conditioned own effects is zero in the reference tests. A positive joint increment over P1/P2 therefore establishes the value of access to both instruments relative to their reference-conditioned alternatives, rather than proving a nonzero structural complementarity term.
\input{tables/v3_reference.tex}
'''
    sec+=figure(6,'Reference policy gains relative to P0, in CNY thousand/day. Fare-only, frequency-only, joint and additional-K policies are compared on increment axes so large inherited profit levels do not obscure instrument effects. Labels report actual gains and the joint increment over the better single instrument. Equal HN frequency/joint bars and equal P3/P4 bars are actual outcomes.','fig:reference_policy_ladder')
    sec+=r'''
\paragraph{Frequency, fares, and class composition.}
Figure~\ref{fig:reference_fare_frequency} identifies exactly which observed G/D families and periods change. Protected quotas preserve baseline coverage while permitted departures are rationalized or reallocated. This can reduce operating cost, but also increases schedule displacement in reduced-frequency periods. Near-binding seat loads restrict the scope of further cuts: the three profit designs reach maximum loads of 0.9488/0.9481/0.9494 and vulnerable retention of 0.9998/0.9992/0.9984. The welfare objectives produce different fare and departure combinations in WC and JX, while observed K remains unchanged. Table~\ref{tab:baseline_policy_values} separates participation from rail share, so modal diversion is not confused with exclusion from travel.
'''
    sec+=figure(7,'Changed product--period decisions in reference P3. Color denotes the departure change from P0; each cell gives that signed change and the common fare multiplier. Rows include the union of products changed under either objective; entirely unchanged products, including fixed K, are omitted. Dashes identify inactive periods. The figure exposes frequency and price reallocations instead of repeating unchanged supply cells.','fig:reference_fare_frequency')
    sec+=r'''
The JX OD comparison retains all six markets rather than aggregating the corridor into an endpoint OD. Different stopping coverage allows frequency and fare changes to redistribute demand unevenly, including the Ganzhou--Nanchang market. These changes depend on the assumed OD allocation and transferred preferences; they should not be interpreted as observed traffic changes.
'''
    sec+=figure(8,'JX rail demand under joint frequency and fare control. Upper/lower triangles show profit/welfare P3; color gives the percentage change in rail trips from P0 and text reports thousand rail trips/day. Heavy borders identify Ganzhou--Nanchang.','fig:jiangxi_od_policy_response',r'.68\textwidth')
    sec+=r'''
\subsection{Market shocks: transmission and regulated feasibility}\label{subsec:scenario_analysis}
\paragraph{Separate demand channels.}
Uniform and polarized income states have the same mean log shock but different class-specific monetary sensitivities. Income deterioration reduces vulnerable participation; cheaper road alternatives can raise all-mode participation while diverting demand and revenue from rail. The P0 diagnostic consequently separates participation, rail share, tier composition and premium-seat use. Premium seats mean G business/first and D first, with K sleepers reported separately. Every one of the 45 electrification cells violates P0's financial floor; the six no-electrification income-downturn cells violate finance, retention and capacity together. The three reference cells meet all requirements.
'''
    sec+=figure(9,'Shock transmission under the same fixed reference design. Top: class-colored percentage-point changes in participation, rail and product/seat composition for four shock combinations. Bottom: retention and financial margins across the six road states, with one line per income state. Dashed lines mark the regulatory requirements. Monetary margins are CNY thousand/day.','fig:shock_transmission')
    sec+=r'''
\paragraph{Baseline feasibility and sufficient budgets.}
At the 0.5-million daily budget, the three reference cells remain the only feasible E2 cells under P0--P4. Partial frequency authority improves the operating choices but does not by itself resolve the declared large shocks. Objective values of least-violation outputs are not treated as feasible policy gains. To distinguish a financial shortfall from other failures, the no-financial-floor searches retain all remaining constraints and maximize profit. A saved admissible design then supplies an implementable sufficient-budget upper bound; it is not a globally minimized subsidy requirement.

Such witnesses are found in 45 of the 51 stressed cells under P3 and 46 under P4. The P3 sufficient budgets range from 0.62--1.50 million in HN, 3.19--5.58 million in WC, and 3.14--4.16 million in JX. These requirements are substantially below those in the preceding fully inherited timetable experiment, reflecting the value of G/D authority in reducing operating commitments. P4 additionally supplies a JX income-downturn witness, with its largest saved requirement about 4.30 million. Unresolved no-floor searches can reflect retention/capacity limitations or search failure; they do not establish that budget increases are inherently ineffective.
'''
    sec+=figure(10,'Sufficient-budget upper bounds across the original stress matrix, in CNY million/day. Rows compare P3 and P4; each facet crosses three income and six road states. Numbers are the loss allowances supporting saved no-floor profit designs. Zero marks the reference cell; question marks indicate that no admissible no-floor witness was found. The original baseline budget remains 0.5 million, and colored tiles are not claims of feasibility at that budget.','fig:minimum_policy')
    sec+=r'''
\subsection{Portfolio reconfiguration and selective conventional service}\label{subsec:k_reopening}
\paragraph{Operating-cost and seat-pricing margins.}
The reference P4 portfolio contains no extra K, but its response to operating cost is heterogeneous. In E3, lowering the common K cost factor to 0.10 induces five extra daily K departures in HN under both objectives. JX adds 30 under profit and 51 under welfare; welfare entries persist at factors 0.25/0.50/0.75 with 18/9/2 extra departures. WC selects none over this cost grid. The resulting thresholds are more informative than repeating unchanged reference portfolios across shock states. E6 separately compares common and seat-specific G/D multipliers under identical frequency authority. Only reference states admit feasible paired comparisons in that original income grid; failed stressed comparisons are not assigned seat-pricing gains.

Seat-specific pricing adds no reference profit value in HN or WC, but adds 14.3 thousand CNY/day in JX. Welfare increments are zero in HN, 2.4 thousand in WC and 15.0 thousand in JX. Fixed seat relativities therefore constrain a subset of cases; they do not make portfolio entry universally necessary.
'''
    sec+=figure(11,'Conditional portfolio and seat-pricing responses. Top: additional K departures against the common observed/candidate K operating-cost factor, with solid/dashed lines distinguishing profit/welfare. Zero WC entry is retained. Bottom: feasible reference objective gains over P0 with common versus seat-specific G/D multipliers under the same frequency bounds.','fig:portfolio_seat_test')
    sec+=r'''
\paragraph{Entry boundaries and event accounting.}
The original E7 polarization--electrification grid remains largely outside the baseline feasible region: 414 of its 462 objective-specific comparisons are unresolved. It nevertheless finds two JX welfare-entry cells at baseline K costs and a road-saving intensity of 0.25, with polarization scales of zero and 0.17 and gains of 48.2 and 17.3 thousand CNY/day. E10 instead resolves the weaker competitive shocks and operating-cost dimension implicated by E3. It reveals a narrow low-cost entry band in HN, a broader JX welfare-entry region than the commercial region, and continued absence of WC entry. Thus a flat WC result is itself a corridor-specific finding, while the refined domain reveals genuine variation elsewhere. Classifications pool feasibility witnesses across objectives, then compare objective values under the same state; they are search-based regimes rather than exact global phase boundaries.
\input{tables/v3_events.tex}
'''
    sec+=figure(12,'K-entry regimes on the targeted E10 grid and profit accounting for all seven E3 events. Top: K cost factors 0.10/0.25/0.40/0.55/0.70/0.85/1.00 crossed with road-saving intensities 0/0.02/0.04/0.06/0.08/0.12/0.20, at reference income and baseline budget. Numbers in selected gain cells are objective increments in CNY thousand/day. Bottom: new-K revenue, incumbent revenue change, negative new-K cost and incumbent cost saving; dots mark net profit changes. Profit and welfare decisions can have different entry regions.','fig:k_phase_events')
    sec+=r'''
With adjustable G/D supply, entry profit accounting must include incumbent cost changes as well as cannibalization. For the HN 0.10-cost event, new K earns 281.6 thousand CNY/day, incumbent revenue falls by 420.1 thousand, new K costs 31.1 thousand, and incumbent operating cost falls by 347.7 thousand. The net gain is 178.0 thousand. Omitting the incumbent cost saving would reverse this commercial interpretation. In JX, some welfare entries increase traveler surplus despite a negative railway-profit increment. Cost factors are therefore reported as experimental triggers, while the separate revenue and cost components explain how the selected portfolio works. Extra service is not universally justified by low fares or coverage alone.

\subsection{Mobility guarantees and governance}\label{subsec:regulation}
\paragraph{Retention thresholds and equity diagnostics.}
The original E4 floors between 0.90 and 1.00 and budgets up to 2 million have little effect when the constraint is slack or the shocked state remains unresolved. E9 zooms into the reference retention threshold instead. Floors below the attained retention leave the objective unchanged; demanding full reference participation at 1.00 imposes a visible sacrifice. Floors above one deliberately test recovery beyond the pre-shock count and can become unresolved. The quarter-polarized extension shows the feasible-search boundary directly, rather than connecting unchanged objective values into an uninformative flat curve. Neither a repeated point nor a missing witness is converted into an artificial trend.
'''
    sec+=figure(13,'Retention thresholds and equity responses. Top left: P3 objective sacrifice relative to the first feasible tested reference floor, with profit/welfare distinguished by solid/dashed lines. Crosses indicate unresolved points, not extrapolated costs. Top right: quarter-polarized feasibility by corridor and policy at the 14-million budget; Y denotes a witness and ? an unresolved search. Bottom: nonzero changes in worst-case cost ratio and vulnerable retention relative to same-state P0 among feasible saved designs. Repeated coordinates are aggregated and marker area increases with multiplicity; coincident origins are counted explicitly.','fig:retention_budget_equity')
    eq=A['equity_stats']; all_=eq['all_saved']; feas=eq['feasible_only']; ex=feas['example']
    sec+='\nAcross '+f'{all_["n"]:,}'+r' main saved designs, '+str(all_['divergence_n'])+' ('+fmt(100*all_['divergence_share'],2)+r'\%) lower both the worst-case realized-traveler cost ratio and vulnerable retention. Among '+f'{feas["n"]:,}'+' feasible records, '+str(feas['divergence_n'])+' ('+fmt(100*feas['divergence_share'],2)+r'\%) exhibit this divergence. These are descriptive counts over an experiment menu with repeated decisions, not population frequencies. A feasible WC reference frequency-only welfare design lowers the worst cost ratio by 0.00262 and retention by 0.000485, with about 19 additional vulnerable nontravelers and 64 fewer vulnerable rail trips. Both retention values remain above the 0.95 requirement. The example shows why a favorable realized-traveler diagnostic need not imply stronger potential-traveler mobility, even for an admissible operating plan.'+'\n'
    sec+=r'''
\paragraph{Commercial and welfare governance.}
E8 supplies 49 feasible paired P4 comparisons: 16 in HN, 16 in WC and 17 in JX. Comparing each commercial design with its welfare counterpart under the same state and budget avoids confusing between-state shocks with governance. All HN pairs coincide. WC has a nonzero reference tradeoff but coincident shocked-state designs; JX exhibits broad variation, with profit compensation reaching 215.1 thousand CNY/day and welfare gains reaching 175.3 thousand across different cells. The reference WC gap is 9.0 thousand profit for 14.1 thousand welfare; JX's is 17.1 thousand for 35.5 thousand. A compensation amount is an accounting gap, not an incentive-compatible subsidy contract. The generous E8 budget is an explicit diagnostic envelope and is not substituted for baseline regulatory feasibility.
'''
    sec+=figure(14,'Governance gaps under the expanded E8 budget of 14 million CNY/day. Each point is a feasible within-state P4 pair: the horizontal coordinate is profit compensation and the vertical coordinate is welfare gain from adopting the welfare design. Colors distinguish income states and shapes road states. Repeated zero-gap states are counted; HN coincidence is retained as a finding. Independent facet scales expose variation without large inherited objective levels; the shared legend is outside all panels.','fig:governance_plane')
    sec+=r'''
\paragraph{Authority and calibration sensitivity.}
Table~\ref{tab:governance_robustness} compares the 25\%, 50\% and 75\% G/D authority cases alongside the zero-authority control. The latter recovers the limited fare-only gains of the preceding experiment, whereas partial authority permits substantial cost and schedule responses. More authority is a larger feasible set, but the archived numerical comparisons remain heuristic solutions. Eight rounds reproduce the baseline P3 objectives. Fare-grid refinement and load/share perturbations quantify other sensitivities. Sixteen of 24 fixed-intercept scale-test records lack a feasible witness: changing nest scales without recalibration also changes fitted shares and cannot establish structural robustness. The substantive conclusions concern conditional instrument value and constraint interactions, with magnitudes dependent on the declared calibration.

Relative to the 50\% authority baseline, 25\% authority lowers profit by 23.0/165.7/24.4 thousand CNY/day in HN/WC/JX. Increasing authority to 75\% leaves HN unchanged and adds 61.3/44.6 thousand in WC/JX. This distinguishes an exhausted local adjustment margin in HN from additional scope in the other corridors, rather than attributing all repeated points to weak demand sensitivity.
\input{tables/v3_governance.tex}

\FloatBarrier
\section{Discussion and conclusion}\label{sec:conclusion}
The framework links product availability, integer departures and discrete fare menus to elastic participation, mode, product and seat choice. Income polarization and road electrification enter through separate monetary-utility channels, and vulnerable-trip retention is evaluated against a fixed potential-traveler reference. In the application, limited authority over G/D frequencies generates substantial operating gains while fixed observed K preserves inherited conventional supply. Reference joint control raises profit by 282--472 thousand CNY/day and welfare by 192--418 thousand; it improves on the better single instrument in WC and JX, whereas HN remains frequency driven.

Operating authority is insufficient to absorb every market shock under the baseline financial allowance. The 54-cell matrix retains only three feasible reference cells, while no-floor searches supply sufficient budgets in 45 stressed P3 cells and 46 P4 cells. More permissive budgets clarify the governance comparison but must be distinguished from affordable baseline policies. Additional conventional entry is selective: low operating costs induce HN and JX service, JX welfare entry extends beyond its commercial region, and WC remains inactive on the tested grids. With G/D adjustments, incumbent operating-cost changes are essential to interpreting the profitability of entry.

Retention and realized-traveler cost ratios need not move together. Feasible examples improve the latter while slightly reducing vulnerable participation, supporting a direct mobility constraint instead of relying solely on post-trip diagnostics. Reference retention sacrifices become visible near a floor of one; slack constraints and unresolved strong shocks should be reported as such rather than presented as smooth policy frontiers. Governance gaps also differ by corridor: coincident HN designs and heterogeneous JX tradeoffs are both informative.

The evidence remains a calibrated strategic exercise. Passenger volumes, formations, costs, utility constants and authority quotas are assumed rather than estimated from traveler choices or operating accounts. Full routes, through occupancy and cost allocation are unidentified; road distances proxy operating length and resource chains are schematic. Mapped railway geometry provides geographic context and does not resolve these data gaps. Candidate preferences are transferred from observed K families. Fixed-intercept scale tests reveal calibration fragility. The model also omits tactical rationing, explicit crowding utility, detailed trainset circulation and strategic road-supplier response. Exact demand evaluation and independent scalar/local audits establish computational consistency, without global optimality or infeasibility certificates. Richer train, passenger and cost data are needed to estimate the demand system and assess whether these conditional portfolio and governance mechanisms hold in operational planning.

\bibliography{TRA-references,TRA-v3-policy-references,TRA-v3-map-references}
\end{document}
'''
    write('TRA-20261014-V3.tex',head+sec)
    write('TRA-v3-map-references.bib',r'''@misc{NaturalEarthRailroads,
 author={{Natural Earth}}, title={Railroads: 1:10m Cultural Vectors},
 year={2026}, howpublished={\url{https://www.naturalearthdata.com/downloads/10m-cultural-vectors/railroads/}},
 note={Public-domain generalized railway geometry; accessed 14 October 2026}}
@misc{OSMRailwayMap,
 author={{OpenStreetMap contributors}}, title={OpenStreetMap railway geometry and attribution},
 year={2026}, howpublished={\url{https://www.openstreetmap.org/copyright}},
 note={Jiangxi geometry retrieved through Overpass on 14 October 2026; Open Database License}}
''')

if __name__=='__main__':
    tables(); manuscript()
    for n in [3,6,7,10,11,12,13,14]: (ROOT/f'fig{n:02d}.py').write_text(f'from revision_figures import figure{n:02d}\nfigure{n:02d}()\n',encoding='utf-8')
    shutil.copy2(ROOT/'revised_case_fig05.tex',PAPER/'fig'/'case_fig05.tex')
    shutil.copy2(ROOT/'revised_case_fig05.pdf',PAPER/'fig'/'case_fig05.pdf')
    shutil.copy2(ROOT/'revised_case_fig05.tex',ROOT/'case_fig05.tex')
    shutil.copy2(ROOT/'revised_case_fig05.pdf',ROOT/'case_fig05.pdf')
    import fitz
    doc=fitz.open(PAPER/'fig'/'case_fig05.pdf'); doc[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(PAPER/'fig'/'case_fig05.png')
    print('Manuscript and compact 95%-width tables generated.')
