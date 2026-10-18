"""Compare COPT against independently certified single-OD objectives."""
import json,time,numpy as np
from model import ROOT,dump
from run_round5 import engine,statekey
from exact_single_od import Exact
from verify import scalar
def main():
    checks=[];start=time.perf_counter()
    for ci in ['HN','WC']:
        m=engine({'case':ci});old=json.loads((ROOT/'states'/(statekey(m)+'.json')).read_text(encoding='utf-8'));ex=Exact(m,old['records'])
        for pol in ['P1','P2','P4','P3']:
            for obj in ['profit','welfare']:
                prior=next(r for r in old['records'] if r['policy']==pol and r['objective']==obj);result=ex.solve(pol,obj);assert result and result['success'],(ci,pol,obj,result);r=result['record'];delta=r[obj]-prior[obj];assert abs(delta)<.01
                a=scalar(m.c,np.array(r['N']),np.array(r['phi']),m.income,m.electric,m.spec);assert abs(a['profit']-r['profit'])<1e-5;checks.append(dict(case=ci,policy=pol,objective=obj,delta=delta,gap=result['gap'],backend=result['backend']))
        m=engine({'case':ci,'spec':{'eta':1.}});ex=Exact(m,old['records'])
        for obj in ['profit','welfare']:
            result=ex.solve('P3',obj);assert result and result['success'],(ci,'strict',obj,result);r=result['record'];checks.append(dict(case=ci,policy='P3 strict',objective=obj,value=r[obj],gap=result['gap'],backend=result['backend']))
            if ci=='WC':assert abs(r[obj]-{'profit':2587992.770154532,'welfare':734109.92385}[obj])<.01
            if ci=='HN' and obj=='welfare':assert abs(r[obj]-562172.20594)<.01
        print('COPT checked',ci,flush=True)
    dump(ROOT/'copt_verification.json',dict(passed=True,checks=checks,seconds=time.perf_counter()-start));print('COPT verification complete',len(checks),flush=True)
if __name__=='__main__':main()
