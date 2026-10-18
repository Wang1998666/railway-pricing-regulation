"""Regression checks for distinct tariff domains and guarded result projection."""
import numpy as np
from model import ROOT,dump
from run_round5 import engine,statekey,transfer

def main():
    checks=[]
    for ci in ['HN','WC','JX']:
        keys=[statekey(engine({'case':ci,'spec':{'fare_cap':cap}})) for cap in [1.1,1.2,1.3]];assert len(set(keys))==3
        m=engine({'case':ci,'spec':{'fare_cap':1.1}});N=m.N0.copy();phi=np.ones((m.S,4,3));valid=m.record(N,phi,'profit','P3');transfer(m,valid,'profit','P3')
        rejected=[]
        for value in [1.2,1.012]:
            ph=phi.copy();ph[m.adjustable]=value;r=m.record(N,ph,'profit','P3')
            try:transfer(m,r,'profit','P3')
            except AssertionError:rejected.append(value)
            else:raise AssertionError((ci,'invalid tariff projection accepted',value))
        assert statekey(engine({'case':ci,'id':'metadata_a'}))==statekey(engine({'case':ci,'id':'metadata_b'}))
        checks.append(dict(case=ci,distinct_fare_cap_keys=keys,valid_projection=True,rejected_tariffs=rejected,metadata_only_reuse=True))
    dump(ROOT/'domain_key_verification.json',dict(passed=True,checks=checks));print('Complete-domain regression checks passed',len(checks),'corridors')

if __name__=='__main__':main()
