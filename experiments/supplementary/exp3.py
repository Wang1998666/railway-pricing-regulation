"""Cross-evaluate saved seat-pricing incumbents before any additional search."""
from common import *
import csv,math
from run_round5 import collect,statekey

def main():
    assert read(HERE/'step0_status.json')['passed'];outdir=HERE/'exp3';outdir.mkdir(exist_ok=True)
    _,states,_,_,_=collect();seeds={s['key']:s['warm'] for s in states};rows=[];final=[]
    for ci in ['HN','WC','JX']:
        gs={income:next(g for g in groups('E6') if g['job']['case']==ci and g['job']['income']==income) for income in ['uniform','polarized']}
        for income,other in [('uniform','polarized'),('polarized','uniform')]:
            eval_start=time.perf_counter()
            g=gs[income];m=engine(g['job']);old=record(g,'P3-sb','profit');common=record(g,'P3','profit');cross=record(gs[other],'P3-sb','profit')
            nr=m.record(np.array(cross['N']),np.array(cross['phi']),'profit','P3-sb');err=check(m,nr) if nr['feasible'] else None
            independent=scalar(m.c,np.array(nr['N']),np.array(nr['phi']),m.income,m.electric,m.spec)
            cross_error=max(abs(independent['profit']-nr['profit']),abs(independent['maxlf']-nr['maxlf']),float(np.max(abs(independent['Q']-np.array(nr['Q'])))))
            assert cross_error<1e-5
            r=old;trigger=(nr['feasible'] and nr['profit']>old['profit']+.01) or old['profit']<common['profit']-.01
            if trigger:
                out=run(m,'profit',seeds[statekey(m)]+[nr,common],pol='P3-sb');dump(outdir/f'{ci}_{income}_search.json',out);r=out['record']
                assert r['profit']>=max(old['profit'],common['profit'],nr['profit'] if nr['feasible'] else -1e100)-.01
            check(m,r)
            n=np.array(r['N']);p=np.array(r['phi']);means=[]
            for b in range(3):
                active=(n>0)&m.adjustable[:,None]&(m.seats[:,b,None]>0);means.append(float((n[active]*p[:,:,b][active]).sum()/n[active].sum()) if active.any() else None)
            counts=[math.prod(int(m.Nmax[s,h]-m.Nmin[s,h]+1) for s in np.flatnonzero(m.adjustable))*17**int((m.seats[m.adjustable]>0).sum()) for h in range(4)] if ci!='JX' else None
            row=dict(case_id=ci,target_state=income,source_state=other,cross_feasible=nr['feasible'],cross_profit=nr['profit']/1000,cross_gain=(nr['profit']-m.state_profit)/1000,cross_floor=nr['eta'],cross_max_load=nr['maxlf'],cross_finance_margin=(nr['profit']+m.budget)/1000,cross_structural=nr['structural'],cross_scalar_error=abs(independent['profit']-nr['profit']),old_seat_profit=old['profit']/1000,final_seat_profit=r['profit']/1000,common_profit=common['profit']/1000,seat_increment=(r['profit']-common['profit'])/1000,search_rerun=trigger,number_changed=abs(r['profit']-old['profit'])>.01,mean_seat_0=means[0],mean_seat_1=means[1],mean_seat_2=means[2],H_premium_share=r['premium_by_class'][0]/r['rail_by_class'][0],design_hash=design_hash(r),status='search',git_commit=git())
            row.update(cross_scalar_error=cross_error,cross_design_hash=design_hash(nr),config_sha256=hashlib.sha256(json.dumps(g['job'],sort_keys=True).encode()).hexdigest(),evaluation_seconds=time.perf_counter()-eval_start,solver='V3 search incumbent; forward scalar evaluation',cross_fleet_utilization=max(nr['fleet_utilization']))
            rows.append(row);final.append(dict(config=g['job'],cross_record=nr,final_record=r,common_record=common,raw_seat_combinations_per_period=counts));print('EXP3',ci,income,'cross feasible',nr['feasible'],'rerun',trigger,flush=True)
    dump(outdir/'designs.json',final)
    with (outdir/'cross_eval.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    changes={ci:{'common_uniform_to_polarized':next(r for r in rows if r['case_id']==ci and r['target_state']=='polarized')['common_profit']-next(r for r in rows if r['case_id']==ci and r['target_state']=='uniform')['common_profit'],'seat_uniform_to_polarized':next(r for r in rows if r['case_id']==ci and r['target_state']=='polarized')['final_seat_profit']-next(r for r in rows if r['case_id']==ci and r['target_state']=='uniform')['final_seat_profit']} for ci in ['HN','WC','JX']}
    dump(outdir/'analysis.json',dict(rows=rows,changes=changes,changed=any(r['number_changed'] for r in rows)))
    (outdir/'summary.md').write_text('# EXP-3 cross-evaluation\n\nMoney: thousand CNY/day. All seat designs and JX common designs are search results; HN/WC common designs retain V3 proofs.\n\n'+json.dumps(dict(rows=rows,changes=changes),indent=2)+'\n\nThe optional seat-specific exact solve was not attempted. The existing exact engine supports two common product fares only; extending it to seat-specific enumeration would require a new engine. Raw candidate counts are saved in designs.json; no claim about counts after dominance filters is made. Cross-state feasibility, finance, load, fleet and retention are independently recomputed. Common-pricing incumbents are included in the V3 seeds.\n',encoding='utf-8')
if __name__=='__main__':main()
