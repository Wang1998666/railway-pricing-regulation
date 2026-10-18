"""Reuse computations only after validating their complete saved decision domain."""
import json,time
from pathlib import Path
import numpy as np
from model import ROOT,dump
from run_round5 import collect,engine,statekey,transfer,hashes

def main():
    start=time.perf_counter();groups,states,mapping,cc,ak=collect();expected={s['key']:s for s in states};archive=ROOT/'archive_before_domain_key_fix_20261015';source=archive/'states';staging=ROOT/'states_complete_domain';staging.mkdir(exist_ok=True);migrated=[];unused=[];maximum=0.
    for path in source.glob('*.json'):
        g=json.loads(path.read_text(encoding='utf-8'));original=engine(g['job']);key=statekey(original)
        if key not in expected:unused.append(path.stem);continue
        target=expected[key];policies=target['policies'];lookup={(r['policy'],r['objective']):r for r in g['records']}
        if not all((p,o) in lookup for p in policies for o in ['profit','welfare']):unused.append(path.stem);continue
        m=engine(target['job']);records=[]
        for pol in policies:
            for obj in ['profit','welfare']:
                r=lookup[(pol,obj)];nr=transfer(m,r,obj,pol);error=max(abs(nr[k]-r[k]) for k in ['profit','U','welfare','maxlf','eta']);assert error<1e-5,(path.stem,key,error);maximum=max(maximum,error);assert nr['feasible']==r['feasible'];records.append(nr)
        g.update(key=key,job=target['job'],policies=policies,records=records,domain_key_version=2,previous_domain_key=path.stem,domain_migration_numeric_error=error)
        if m.c['id'] in ['HN','WC']:g['certificates']=[dict(policy=r['policy'],objective=r['objective'],certificate=r['meta'].get('certificate',False),infeasible=r['meta'].get('infeasibility_certificate',False),upper=r['meta'].get('upper_bound'),gap=r['meta'].get('certificate_gap')) for r in records if r['policy'] not in ['P0','P3-sb']]
        else:g['certificates']=[]
        g.setdefault('source_hashes_at_solve',g['source_hashes']);g['source_hashes']=hashes();g['cache_reuse_reason']='Complete-domain migration: saved-job fare cap, menu and frequency bounds checked; original numerical evaluation unchanged.'
        assert not (staging/(key+'.json')).exists(),('duplicate migrated key',key);dump(staging/(key+'.json'),g);migrated.append(dict(old=path.stem,new=key,case=m.c['id'],fare_cap=m.fare_cap))
    cap_keys={}
    for ci in ['HN','WC','JX']:
        keys=[statekey(engine({'case':ci,'spec':{'fare_cap':cap}})) for cap in [1.1,1.2,1.3]];assert len(set(keys))==3;cap_keys[ci]=keys
    # Both resolved absolute move targets remain inside this experiment workspace.
    old=ROOT/'states';retired=archive/'state_directory_at_switch';assert old.resolve().is_relative_to(ROOT.resolve()) and retired.resolve().is_relative_to(ROOT.resolve()) and staging.resolve().is_relative_to(ROOT.resolve());assert not retired.exists()
    old.rename(retired);staging.rename(old)
    missing=sorted(set(expected)-{x['new'] for x in migrated});dump(ROOT/'domain_key_migration.json',dict(passed=True,groups=len(groups),complete_domain_states=len(states),migrated_states=len(migrated),states_to_solve=len(missing),missing=missing,unused=unused,migrated=migrated,fare_cap_regression_keys=cap_keys,maximum_numeric_error=maximum,seconds=time.perf_counter()-start));print('DOMAIN MIGRATION',len(migrated),'reused',len(missing),'new',len(states),'total; maximum error',maximum,flush=True)

if __name__=='__main__':main()
