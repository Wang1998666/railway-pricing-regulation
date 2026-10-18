"""Read-only factual checks and extraction of existing cost-split results."""
from common import *
import csv,re,collections

def csvout(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['file','line','text']);w.writeheader();w.writerows(rows)

def main():
    assert read(HERE/'step0_status.json')['passed'];R3=HERE.parents[1];lines=['# V4 factual checks','', 'Evidence paths below use the functional archive layout. Historical manuscript references remain provenance only.'];stats={}
    lines += ['','## 1. Demand sizing (V4 line 597)','The statement is approximately correct but hides the construction. `TRA-R2/main/calibration.py:9–33` first allocates target seat flows by inverse OD road distance, normalizes by maximum subpath occupancy, and scales each tier by 0.78/0.72/0.70 relative to G and by the 0.88 reference load. Potential demand is target rail flow divided by 0.85 and the distance-band target rail share, allocated 0.20/0.60/0.20 to H/M/L. Class participation targets are 0.90/0.85/0.80, class rail shares are shifted by +0.04/0/−0.045, and iterative proportional fitting balances class/product/seat targets. This is calibrated demand, not observed ticket demand.','Suggested wording: “Potential demand is constructed from tier-scaled reference seat flows, allocated across ODs using normalized inverse road-distance weights, and divided by the target aggregate rail share and a 0.85 participation scaling factor; class-specific flows and intercepts are then balanced to reproduce the 0.88 peak load.”']
    vans={}
    for ci in ['HN','WC','JX']:
        m=engine(dict(case=ci));z=m.evaluate(m.N0,np.ones((m.S,4,3)),True);Q=z['Q'][0];pm=z['mode_probs'][0];qvan=Q*pm[...,1]*m.road_probs[...,2]
        vans[ci]=dict(fares=m.road[:,3,0].tolist(),van_trips=float(qvan.sum()),share_all_realized=float(qvan.sum()/Q.sum()),share_road=float(qvan.sum()/(Q*(1-pm[...,0])).sum()))
    stats['van']=vans
    lines += ['','## 2. Business-van fare (V4 line 602)',f"Model interpretation is a passenger's monetary cost: there is no van-occupancy divisor (`model.py:93–104`; only private-auto cost is divided by occupancy in `calibration.py:57`). The HN value is {vans['HN']['fares'][0]:.1f} CNY, not an observed per-seat quote. The source rules are `TRA-V7/TRA-V7_REUSABLE_R1_KINCUMBENT_20260812/cases/formal/hangzhou_nanjing/raw_data/hangzhou_nanjing_road_cost_rules.json:18–23`: max(50, 2.2 × distance_km + 0.4 × duration_min). The associated road_passenger.csv row gives 279.388 km, 202.117 min and 695.50 CNY. No cited tariff source or explicit seat/vehicle unit is recorded in those rules. Consequently the model's per-person use can be confirmed, but the real-world quote unit cannot.",f"Reference van shares of realized trips: HN {vans['HN']['share_all_realized']*100:.4f}%, WC {vans['WC']['share_all_realized']*100:.4f}%, JX {vans['JX']['share_all_realized']*100:.4f}%. Van has 3% within shared-road modes and 1.8% within all road trips by construction (`calibration.py:63–73`).",'Suggested wording: “Business-van monetary costs are stylized model assumptions, calculated at 2.2 CNY/km plus 0.4 CNY/min with a 50-CNY minimum and applied per traveler; they are not verified per-seat tariffs.” The author should confirm the intended tariff unit before interpreting it empirically.']
    head={}
    cc=read(BASE/'constant_cost_grid.json')['groups']
    for ci in ['HN','WC','JX']:
        gg=[g for g in cc if g['job']['case']==ci and g['job']['spec']['lambda']==.95 and g['job']['spec']['variable_share']==.7]
        def value(load):
            g=next(g for g in gg if g['job']['spec']['ref_load']==load);m=engine(g['job']);r=record(g,'P3','profit');return r['profit']-m.state_profit
        m=engine(dict(case=ci));head[ci]=(value(.85)-value(.92))/7/m.N0.sum()/1000
    stats['headroom']=head
    lines += ['','## 3. Headroom (V4 line 650)',f"Endpoint difference, not a regression slope: [gain(load 0.85) − gain(load 0.92)] / 7 / observed_departures / 1000. Computed values: {head}. The ceiling is 0.95, variable-cost share 0.70, and total reference cost is held at the load-0.88 anchor. Evidence: `write_round3.py:124–128`; `constant_cost_grid.json`.",'Suggested wording: “Across the 0.85–0.92 reference-load endpoints, the average increase in commercial P3 profit gain per percentage point of spare capacity is 0.886/1.025/0.315 thousand CNY/day per observed departure.”']
    freeze={}
    for ci in ['HN','WC']:
        r=read(HERE/'step0_runs'/f'{ci}_freeze.json')['record'];p2=record(reference(ci),'P2','profit');m=engine(dict(case=ci));n=np.array(r['N']);ph=np.array(r['phi']);active=(n>0)&m.adjustable[:,None]
        freeze[ci]=dict(N_identical=bool(np.array_equal(n,p2['N'])),all_active_fares_one=bool(np.all(abs(ph[active]-1)<1e-9)),same_y_u=bool(np.array_equal(n>0,np.array(p2['N'])>0)),design_hash_freeze=design_hash(r),design_hash_P2=design_hash(p2))
    stats['freeze']=freeze
    lines += ['','## 4. Fare freeze versus P2 (V4 line 662)',json.dumps(freeze,indent=2),'Evidence: fresh `step0_runs/*_freeze.json` versus V3 `runs/E2/*_reference_none.json`, profit P2. Suggested wording: “At cap 1.00 and floor 0.95, commercial P3 coincides with commercial P2 in train activation, departures and active fares; no active G/D product-period prices below 1.00.”']
    ex1=read(HERE/'exp1'/'analysis.json');stats['distinct_grid']={ci:dict(v3=ex1[ci]['distinct_v3'],v4=ex1[ci]['distinct_new']) for ci in ['HN','WC']}
    lines += ['','## 5. Distinct grid designs (V4 lines 669–670)',f"V3: HN {ex1['HN']['distinct_v3']}/30; WC {ex1['WC']['distinct_v3']}/30. Refined V4: HN {ex1['HN']['distinct_new']}/35; WC {ex1['WC']['distinct_new']}/35. Identity hashes y/u derived from N, integer N and full fare arrays; no rounding of numerical outcomes is used as a design identifier. Evidence: `exp1/analysis.json` and `TRA-R2/policy_grid/grid/*.json`.",'Suggested wording: “The 30 sampled cap–floor points correspond to 11 distinct HN designs and 10 distinct WC designs.”']
    counts={};e11=groups('E11')
    for ss in [True,False]:
        out={ci:dict(states=0,P0=0,P4=0,unresolved_P4=0) for ci in ['HN','WC','JX']}
        for ci in out:
            for income in ['reference','uniform','polarized']:
                for xi in [0.,.05,.1,.2,.35,.5,.75,1.]:
                    e='none' if xi==0 else 'all_high';spec={'electric_scale':xi,'same_state':ss and income!='reference'};m=engine(dict(case=ci,income=income,electric=e,spec=spec));z=m.record(m.N0,np.ones((m.S,4,3)),'profit','P0');d=out[ci];d['states']+=1;d['P0']+=int(z['feasible'])
                    pool=groups('E2') if ss or income=='reference' else e11
                    g=next(g for g in pool if g['job']['case']==ci and g['job']['income']==income and abs(g['job']['spec'].get('electric_scale',0)-xi)<1e-9 and g['job']['electric']==e and not g['job']['spec'].get('road_contrast'))
                    rr=[r for r in g['records'] if r['policy']=='P4'];feas=any(m.record(np.array(r['N']),np.array(r['phi']),'profit','P4')['feasible'] for r in rr);d['P4']+=int(feas);d['unresolved_P4']+=int(not feas and not all(r['meta'].get('infeasibility_certificate') for r in rr))
        counts['same_state' if ss else 'absolute_reference']=out
    stats['floor_counts']=counts
    lines += ['','## 6. Floor definitions in 72 moderate states (V4 line 723)',json.dumps(counts,indent=2),'Evidence: `run_experiments.py:26–31,57–58`, `model.py:106–119`, V3 E2 (same-state) and E11 (absolute-reference) outputs. Reference-income states use the identical denominator under both definitions. P4 means at least one independently re-evaluated feasible saved design across objectives; JX is search evidence.']
    lines += ['','## 7. 92% cost ratio (V4 line 610)','The ratio is hard-coded as `totalcost=.92*refrev` in `calibration.py:91`; older input construction also rescales costs at `build_inputs.py:145`. The code/config contains no cited source for 92%. It is an assumption, with 70% variable and 30% retained commitments at the central setting.','Suggested wording: “We assume total reference operating cost equal to 92% of reference rail revenue and split it into 70% variable departure costs and 30% retained product commitments.”']
    m=engine(dict(case='JX'));w=read(HERE/'step0_runs'/'JX_welfare.json')['record'];profit=(w['profit']-m.state_profit)/1000;stats['JX_welfare_profit_gain']=profit
    lines += ['','## 8. JX welfare-P3 profit change (V4 line 643)',f"{profit:.6f} thousand CNY/day relative to same-state P0. This is {'positive' if profit>0 else 'negative'}, based on the fresh search rerun and independent scalar check in `step0_runs/JX_welfare.json`. Suggested wording: “The welfare benchmark also raises operator profit in all three corridors.”" if profit>0 else f"{profit:.6f} thousand CNY/day; V4 correctly limits the positive-profit claim to HN/WC."]
    refs=[];wording=[]
    for p in sorted((R3/'tables'/'supplementary').glob('*.tex')):
        for no,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
            if re.search(r'\b(?:Table|Figure|Fig\.)[\s~]*\d+',line):refs.append(dict(file=str(p),line=no,text=line))
            for hit in re.finditer(r'\b(?:certified|certify|witness\w*)\b',line,re.I):wording.append(dict(file=str(p),line=no,column=hit.start()+1,word=hit.group(),text=line))
    scripts=list(BASE.glob('*fig*.py'))+[ROUND6/'analyze_round6.py']+list((R3/'editorial').glob('*fig*.py'))+list((R3/'visualization'/'case_figures').glob('*.py'))
    for p in sorted(set(scripts)):
        for no,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
            for hit in re.finditer(r'\b(?:certified|certify|witness\w*)\b',line,re.I):wording.append(dict(file=str(p),line=no,column=hit.start()+1,word=hit.group(),text=line))
    csvout(HERE/'checks_hardcoded_refs.csv',refs);csvout(HERE/'checks_wording.csv',wording)
    lines += ['','## 9. Hard-coded table/figure numbers',f"{len(refs)} occurrences in the current TRA-R3/tables/*.tex. The governance note already uses Table~\\ref{{tab:baseline_policy_values}}. Complete inventory: `checks_hardcoded_refs.csv`.",'','## 10. Certified/certify/witness wording',f"{len(wording)} individual occurrences are inventoried with the matched word, column, complete line text, file and line number in `checks_wording.csv`. Scope: every current R3 table and the V3 round5 figure generators, active round6 Fig. 13 generator, round7 Fig. 17 generator, and current R3 redrawing scripts; historical archived/replaced engines are excluded. New table copies and figure generators use the requested terminology."]
    dump(HERE/'checks_data.json',stats);(HERE/'checks.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
    ex5=[]
    for ci in ['HN','WC','JX']:
        for share in [.5,.9]:
            g=next(g for g in cc if g['job']['case']==ci and g['job']['spec']['ref_load']==.88 and g['job']['spec']['lambda']==.95 and g['job']['spec']['variable_share']==share);m=engine(g['job']);r=record(g,'P3','welfare');err=check(m,r)
            ex5.append(dict(case_id=ci,variable_share=share,P0_departures=int(m.N0.sum()),welfare_P3_departures=int(np.array(r['N']).sum()),profit_gain=(r['profit']-m.state_profit)/1000,delta_W=r['welfare']/1000,status='optimal' if r['meta'].get('certificate') else 'search',scalar_error=err,design_hash=design_hash(r)))
    (HERE/'exp5').mkdir(exist_ok=True);dump(HERE/'exp5'/'results.json',ex5)
    (HERE/'exp5'/'summary.md').write_text('# EXP-5 existing cost-split welfare designs\n\nExtracted from V3 constant_cost_grid.json; no optimization was needed. Money: thousand CNY/day.\n\n'+json.dumps(ex5,indent=2)+'\n\nThe over-supply interpretation should be limited to the cost splits where welfare P3 actually withdraws departures; these are calibrated rather than observed efficiency estimates.\n',encoding='utf-8')
if __name__=='__main__':main()
