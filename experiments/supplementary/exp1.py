"""Refined cap/floor grid using unchanged V3 exact enumeration and masters."""
from common import *
import csv, collections
from concurrent.futures import ProcessPoolExecutor,as_completed
from analyze_round5 import operations
FLOORS=[.98,.985,.99,.995,.999,.9995,1.]
CAPS=[1.,1.05,1.1,1.15,1.2]

def task(ci,cap):
    warm=reference(ci)['records']+[r for g in groups('E9') if g['job']['case']==ci for r in g['records']]
    m=engine(dict(case=ci,spec={'fare_cap':cap,'eta':.98}));ex=Exact(m,warm);outputs=[]
    for obj,eta in [('profit',eta) for eta in FLOORS]+([('welfare',eta) for eta in [.999,1.]] if cap in [1.05,1.2] else []):
        m.spec={'fare_cap':cap,'eta':eta};m.eta_floor=eta
        path=HERE/'exp1'/'runs'/f'{ci}_{cap:.2f}_{eta:.4f}_{obj}.json'
        if path.exists():out=read(path)
        else:
            out=run(m,obj,warm,exact=ex);dump(path,out)
        if out['record']:
            # Model records retain a live spec dictionary; snapshot each case.
            out['record']['spec']=dict(m.spec);ex.seeds.append(out['record'])
        outputs.append(out);print('EXP1',ci,cap,eta,obj,out['status'],round(out['seconds'],2),flush=True)
    return outputs

def analyze(outputs):
    rows=[]
    for out in outputs:
        c=out['config'];r=out['record'];m=engine(c)
        row=dict(case_id=c['case'],cap=c['spec']['fare_cap'],floor=c['spec']['eta'],objective=c['objective'],status=out['status'],seconds=out['seconds'],design_hash=out['design_hash'],git_commit=out['git_commit'],config_sha256=out['config_sha256'],solver=out['solver'])
        if r:
            op=operations(m,r);row.update(profit_gain=(r['profit']-m.state_profit)/1000,delta_U=(r['U']-m.state_U)/1000,delta_W=r['welfare']/1000,L_retention=r['eta'],floor_binding=r['eta']-m.eta_floor<1e-6,mean_GD_multiplier=op['fare'],cap_cells=op['cap_cells'],active_cells=op['active_cells'],G_departures=op['tier_departures'][0],D_departures=op['tier_departures'][1],K_departures=op['tier_departures'][2],scalar_error=out['scalar_error'])
        rows.append(row)
    commercial=[r for r in rows if r['objective']=='profit'];summary={}
    for ci in ['HN','WC']:
        rr=[r for r in commercial if r['case_id']==ci];p=read(HERE/'step0_runs'/f'{ci}_welfare.json')['record']
        for a in rr:
            a['nondominated']=not any(b['profit_gain']>=a['profit_gain']-1e-8 and b['delta_W']>=a['delta_W']-1e-8 and (b['profit_gain']>a['profit_gain']+1e-8 or b['delta_W']>a['delta_W']+1e-8) for b in rr)
            a['welfare_optimum_share']=a['delta_W']/(p['welfare']/1000)
        old=[a for path in (ROUND6/'grid').glob(ci+'*.json') for a in read(path)['rows']]
        get=lambda c,e:next(a for a in rr if a['cap']==c and a['floor']==e)
        def dominate(target):return [a for a in rr if a['floor']<1 and a['profit_gain']>=target['profit_gain']-1e-8 and a['delta_W']>=target['delta_W']-1e-8]
        summary[ci]=dict(distinct_new=len(set(a['design_hash'] for a in rr)),distinct_v3=len(set(design_hash(a['record']) for a in old)),
          binding_threshold={str(c):next((a['floor'] for a in rr if a['cap']==c and a['floor_binding']),None) for c in CAPS},
          frontier=[a for a in rr if a['nondominated']],dominate_strict=dominate(get(1.2,1.)),dominate_joint=dominate(get(1.05,1.)),
          welfare_optimum_retention=p['eta'],floors_admitting_welfare_optimum=[e for e in FLOORS if e<=p['eta']+1e-9],selected=[get(c,e) for c in [1.2,1.05] for e in [.995,.999,.9995,1.]])
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/'exp1'/'grid.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    dump(HERE/'exp1'/'analysis.json',summary)
    lines=['# EXP-1 refined grid','',str(dict(collections.Counter(r['status'] for r in rows))),'','All money: thousand CNY/day, one direction. The welfare benchmark is central cap 1.20.']
    for ci,s in summary.items():
        lines += ['',f'## {ci}',f"Distinct designs: {s['distinct_new']}/35 refined points; {s['distinct_v3']}/30 V3 points.",f"First sampled binding floors (null means no sampled floor is binding): {s['binding_threshold']}.",f"Floors admitting the central welfare optimum at cap 1.20: {s['floors_admitting_welfare_optimum']}.",f"Sub-unit commercial designs weakly dominating cap 1.20/floor 1.00: {len(s['dominate_strict'])}; dominating cap 1.05/floor 1.00: {len(s['dominate_joint'])}.",'','| Cap | Floor | Profit gain | ΔW | L retention |','|---|---|---|---|---|']
        lines += [f"| {a['cap']:.2f} | {a['floor']:.4f} | {a['profit_gain']:.1f} | {a['delta_W']:.1f} | {a['L_retention']:.8f} |" for a in s['selected']]
    lines += ['','Binding uses the requested post-integer-solution tolerance of 1e-6; a stricter floor can change the optimal discrete design while the constraint remains numerically slack. Full sampled frontier and welfare shares are in analysis.json and grid.csv.']
    (HERE/'exp1'/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    assert read(HERE/'step0_status.json')['passed'],'Step 0 must pass first'
    outputs=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(task,ci,c) for ci in ['HN','WC'] for c in CAPS]):outputs+=f.result()
    analyze(outputs)
if __name__=='__main__':main()
