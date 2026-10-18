"""Mandatory fresh V3 baseline regression. No new experiment runs here."""
from common import *
import csv
from run_round5 import collect, statekey

TARGETS={
 'HN':dict(commercial=(1585.2,-398.9,.9811),welfare=(None,562.2,None),strict=(569.9,388.9,None),tight=(None,521.0,None),moderate=(1180.7,-84.7,None),freeze=(535.4,480.9,None)),
 'WC':dict(commercial=(1788.8,-709.7,.9882),welfare=(852.5,769.6,.999754),strict=(757.0,730.4,None),tight=(None,734.0,None),moderate=(1510.8,-345.2,None),freeze=(692.8,683.5,None)),
 'JX':dict(commercial=(1598.4,-941.2,.9932),welfare=(None,833.7,None),strict=(267.8,249.7,None),moderate=(964.4,-401.9,None))}
CONFIGS=dict(commercial=(1.2,.95,'profit'),welfare=(1.2,.95,'welfare'),strict=(1.2,1.,'profit'),tight=(1.05,1.,'profit'),moderate=(1.1,.95,'profit'),freeze=(1.,.95,'profit'))

def main():
    dump(HERE/'provenance.json',provenance());rows=[]
    _,states,_,_,_=collect()
    v3_states={s['key']:s for s in states}
    for ci,targets in TARGETS.items():
        ref=reference(ci)
        for label,expected in targets.items():
            cap,eta,obj=CONFIGS[label];m=engine(dict(case=ci,spec={'fare_cap':cap,'eta':eta}))
            # Reuse the unchanged V3 collector's complete state-specific seeds.
            # E16 includes the cap-1.10 JX incumbent omitted by the first runner.
            saved_state=v3_states.get(statekey(m))
            warm=saved_state['warm'] if saved_state else ref['records']+[r for g in groups('E9') if g['job']['case']==ci for r in g['records']]
            path=HERE/'step0_runs'/f'{ci}_{label}.json'
            out=read(path) if path.exists() else run(m,obj,warm,strong=label in ['commercial','welfare'])
            dump(path,out);r=out['record']
            actual=(r['profit']/1000-m.state_profit/1000,r['welfare']/1000,r['eta']) if r else (None,)*3
            for metric,e,a in zip(['profit_gain','delta_W','L_retention'],expected,actual):
                if e is None:continue
                tol=.0001 if metric=='L_retention' else .1
                ok=a is not None and abs(a-e)<=tol and out['status'] in ['optimal','search'] and out['scalar_error'] is not None
                row=dict(case_id=ci,case=label,metric=metric,expected=e,actual=a,tolerance=tol,passed=ok,status=out['status'],seconds=out['seconds'],design_hash=out['design_hash'],git_commit=out['git_commit'],config_sha256=out['config_sha256'],solver=out['solver'],scalar_error=out['scalar_error'])
                rows.append(row);print('PASS' if ok else 'FAIL',ci,label,metric,'expected',e,'actual',a,flush=True)
            with (HERE/'step0_regression.csv').open('w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    passed=all(r['passed'] for r in rows)
    dump(HERE/'step0_status.json',dict(passed=passed,checks=len(rows),failures=[r for r in rows if not r['passed']]))
    print('STEP0', 'PASS' if passed else 'FAIL: STOP ALL NEW EXPERIMENTS',flush=True)
if __name__=='__main__':main()
