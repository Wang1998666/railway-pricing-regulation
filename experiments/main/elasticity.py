"""Central log derivatives without optimization; old versus reviewed calibration."""
import json,copy,importlib.util
import numpy as np
from scipy.special import logsumexp
from model import ROOT,Model,dump

def quantities(r):
    return np.array(r['qr']).sum(axis=(0,2,3,4)),np.array(r['Q']).sum(axis=(0,2)),np.array(r['qr']).sum(axis=(0,2,4))

def run():
    source=ROOT.parent/'experiments_v3_revision2'/'verify.py'; module=importlib.util.spec_from_file_location('legacy_scalar',source); legacy=importlib.util.module_from_spec(module); module.loader.exec_module(legacy)
    reports=[]; eps=1e-4
    for ci in ['HN','WC','JX']:
        c=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')); S=len(c['products']); N=np.array([p['N0'] for p in c['products']]); one=np.ones((S,4,3))
        for version in ['before','reviewed']:
            m=Model(c); cc=c if version=='before' else m.c
            # scalar accepts an already calibrated input; strip duplicate money adjustment.
            def ev(phi=one,dy=None,auto=0.):
                cp=copy.deepcopy(cc)
                if auto:
                    for r in cp['road']: r[0][0]*=np.exp(auto)
                return legacy.scalar(cp,N,phi,'reference' if dy is None else 'diagnostic','none',{} if dy is None else {'dy':[dy]*3})
            zero=ev(); q,t,p=quantities(zero); minus=ev(one*np.exp(-eps)); plus=ev(one*np.exp(eps)); qm=quantities(minus)[0]; qp=quantities(plus)[0]
            own=(np.log(qp)-np.log(qm))/(2*eps); agg=(np.log(qp.sum())-np.log(qm.sum()))/(2*eps)
            am=quantities(ev(auto=-eps))[0]; ap=quantities(ev(auto=eps))[0]; cross=(np.log(ap)-np.log(am))/(2*eps)
            tm=quantities(ev(dy=-eps))[1]; tp=quantities(ev(dy=eps))[1]; inc=(np.log(tp)-np.log(tm))/(2*eps)
            products=[]
            for s,prod in enumerate(c['products']):
                if prod['candidate']: continue
                pm=one.copy(); pp=one.copy(); pm[s]*=np.exp(-eps); pp[s]*=np.exp(eps)
                low=quantities(ev(pm))[2][:,s]; high=quantities(ev(pp))[2][:,s]
                products.append(dict(id=prod['id'],elasticity=((np.log(high)-np.log(low))/(2*eps)).tolist(),aggregate=float((np.log(high.sum())-np.log(low.sum()))/(2*eps))))
            reports.append(dict(case_id=ci,version=version,rail_own=own.tolist(),rail_own_aggregate=float(agg),rail_auto_cross=cross.tolist(),trip_income=inc.tolist(),products=products,coefficient_scale=1 if version=='before' else cc['coefficient_scale'],occupancy=1 if version=='before' else cc['occupancy']))
    dump(ROOT/'elasticities.json',reports)
    print(json.dumps([{k:v for k,v in r.items() if k!='products'} for r in reports],indent=2))

if __name__=='__main__': run()
