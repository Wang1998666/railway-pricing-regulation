"""Extended elasticity anchors with the unchanged slope/intercept recalibration."""
from common import *
from analyze_round5 import operations
from concurrent.futures import ProcessPoolExecutor,as_completed
import csv,collections

def calibration(ci,anchor):
    m=engine(dict(case=ci,spec={'slope':anchor/.8}));ph=np.ones((m.S,4,3));b=m.evaluate(m.N0,ph,True);eps=1e-4;weights=[];ders=[]
    for s in np.flatnonzero(m.adjustable):
        for h in range(4):
            if not m.N0[s,h]:continue
            qs=[]
            for sign in [-1,1]:
                p=ph.copy();p[s,h]=np.exp(sign*eps);qr=m.evaluate(m.N0,p,True)['qr'][0];qs.append(qr[:,:,h,s].sum(axis=(0,2)))
            weights.append(b['qr'][0,:,:,h,s].sum(axis=(0,2)));ders.append((np.log(qs[1])-np.log(qs[0]))/(2*eps))
    weights=np.array(weights);ders=np.array(ders);own=float((weights*ders).sum()/weights.sum());pooled=[];allrail=[]
    for sign in [-1,1]:
        p=ph.copy();p[m.adjustable]*=np.exp(sign*eps);pooled.append(m.evaluate(m.N0,p,True)['qr'][0].sum(axis=(0,2,3,4)))
        allrail.append(m.evaluate(m.N0,ph*np.exp(sign*eps),True)['qr'][0].sum(axis=(0,2,3,4)))
    flow_error=float(np.max(abs(b['qr'][0]-np.array(m.c['target_rail']))));load=float(b['maxlf'][0]);assert abs(own+anchor)<=.01 and flow_error<1e-6 and abs(load-.88)<1e-8
    return dict(case_id=ci,anchor=-anchor,own_GD_weighted=own,pooled_GD_by_class=((np.log(pooled[1])-np.log(pooled[0]))/(2*eps)).tolist(),all_rail_by_class=((np.log(allrail[1])-np.log(allrail[0]))/(2*eps)).tolist(),flow_max_error=flow_error,reference_load=load)

def task(ci,anchor,cap):
    m=engine(dict(case=ci,spec={'slope':anchor/.8,'fare_cap':cap,'eta':.95}))
    warm=reference(ci)['records']+[r for g in groups('E16') if g['job']['case']==ci for r in g['records']];ex=Exact(m,warm) if ci!='JX' else None;outs=[]
    for obj in ['profit']+(['welfare'] if cap==1.2 else []):
        path=HERE/'exp4'/'runs'/f'{ci}_{anchor:.2f}_{cap:.2f}_{obj}.json'
        out=read(path) if path.exists() else run(m,obj,warm,exact=ex,strong=False);dump(path,out);outs.append(out)
        if out['record']:warm.append(out['record'])
        print('EXP4',ci,anchor,cap,obj,out['status'],round(out['seconds'],2),flush=True)
    return outs

def main():
    assert read(HERE/'step0_status.json')['passed'];outdir=HERE/'exp4';outdir.mkdir(exist_ok=True)
    calibrations=[calibration(ci,a) for ci in ['HN','WC','JX'] for a in [1.2,1.5]];dump(outdir/'calibration.json',calibrations)
    outputs=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(task,ci,a,c) for ci in ['HN','WC','JX'] for a in [1.2,1.5] for c in [1.1,1.2,1.3]]):outputs+=f.result()
    rows=[]
    for out in outputs:
        c=out['config'];m=engine(c);r=out['record'];row=dict(case_id=c['case'],anchor=-c['spec']['slope']*.8,cap=c['spec']['fare_cap'],objective=c['objective'],status=out['status'],seconds=out['seconds'],design_hash=out['design_hash'],git_commit=out['git_commit'],config_sha256=out['config_sha256'],solver=out['solver'])
        if r:
            op=operations(m,r);row.update(profit_gain=(r['profit']-m.state_profit)/1000,delta_W=r['welfare']/1000,L_retention=r['eta'],mean_GD_multiplier=op['fare'],cap_cell_share=op['cap_cells']/op['active_cells'],cap_departure_share=op['cap_departure_fraction'],G_departures=op['tier_departures'][0],D_departures=op['tier_departures'][1],K_departures=op['tier_departures'][2],scalar_error=out['scalar_error'])
        rows.append(row)
    with (outdir/'elasticity_ext.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
    old=[]
    for g in groups('E16'):
        m=engine(g['job'])
        for obj in ['profit','welfare']:
            r=record(g,'P3',obj);op=operations(m,r);old.append(dict(case_id=m.c['id'],anchor=-g['job']['anchor'],cap=g['job']['cap'],objective=obj,profit_gain=(r['profit']-m.state_profit)/1000,delta_W=r['welfare']/1000,mean_GD_multiplier=op['fare'],status='optimal' if r['meta'].get('certificate') else 'search'))
    analysis=dict(status_counts=dict(collections.Counter(r['status'] for r in rows)),commercial_negative=all(r['delta_W']<0 for r in rows if r['objective']=='profit' and 'delta_W' in r),commercial_below_cap=[r for r in rows if r['objective']=='profit' and r.get('mean_GD_multiplier',1e10)<r['cap']-1e-8],rows=rows,old_rows=old)
    dump(outdir/'analysis.json',analysis)
    lines=['# EXP-4 wider elasticity range','',str(analysis['status_counts']),'','All money: thousand CNY/day. Reference flows and peak load pass for all six recalibrations.','',f"Commercial ΔW negative at every new anchor/cap: {analysis['commercial_negative']}.",'','| Corridor | Anchor | Cap | Objective | Profit gain | ΔW | Mean multiplier | Cap cell share | Retention | Status |','|---|---|---|---|---|---|---|---|---|---|']
    lines += [f"| {r['case_id']} | {r['anchor']:.2f} | {r['cap']:.2f} | {r['objective']} | {r.get('profit_gain',float('nan')):.1f} | {r.get('delta_W',float('nan')):.1f} | {r.get('mean_GD_multiplier',float('nan')):.4f} | {r.get('cap_cell_share',float('nan')):.3f} | {r.get('L_retention',float('nan')):.6f} | {r['status']} |" for r in sorted(rows,key=lambda r:(r['case_id'],r['anchor'],r['cap'],r['objective']))]
    (outdir/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__':main()
