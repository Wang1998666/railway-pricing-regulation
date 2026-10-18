"""Reproduce exact Pareto-filter equivalence on random and tied columns."""
import time
import numpy as np
from model import ROOT,dump
from pareto_kernel import skyline
from exact_single_od import skyline_reference

def main():
    seed=20261015;rng=np.random.default_rng(seed);tests=0
    for sample in range(100):
        a=rng.normal(size=(int(rng.integers(16,1025)),10))
        if sample%2:a=np.round(a,1)
        a[::7,6:9]=0. # Include exact ties and zero outcomes.
        for objective in ['profit','welfare']:
            assert np.array_equal(skyline(a,objective),skyline_reference(a,objective)),(sample,objective)
            tests+=1
    # Adversarial profit/participation tradeoff retains every column.
    a=np.zeros((289,10));a[:,6]=np.arange(289);a[:,8]=-a[:,6]
    times={};repeats=100
    for name,fn in [('old',skyline_reference),('new',skyline)]:
        start=time.perf_counter()
        for _ in range(repeats):assert len(fn(a,'profit'))==len(a)
        times[name]=time.perf_counter()-start
    result=dict(passed=True,tests=tests,seed=seed,benchmark_columns=len(a),benchmark_repeats=repeats,old_seconds=times['old'],new_seconds=times['new'],speedup=times['old']/times['new'])
    dump(ROOT/'pareto_kernel_verification.json',result);print(result)

if __name__=='__main__':main()
