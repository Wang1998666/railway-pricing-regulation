"""Exact two/three-dimensional dominance screening in O(n log n)."""
import numpy as np
def skyline(a,obj):
    score=a[:,6] if obj=='profit' else a[:,6]+a[:,7];order=np.lexsort((-a[:,8],-score,-a[:,6]))
    if obj=='profit':
        L=a[order,8];previous=np.r_[-np.inf,np.maximum.accumulate(L)[:-1]];return a[order[L>previous]]
    levels=np.unique(a[:,8]);tree=np.full(len(levels)+1,-np.inf);keep=[]
    for idx in order:
        rank=len(levels)-np.searchsorted(levels,a[idx,8]);pos=rank;best=-np.inf
        while pos>0:best=max(best,tree[pos]);pos-=pos&-pos
        if best>=score[idx]:continue
        keep.append(idx);pos=rank
        while pos<len(tree):tree[pos]=max(tree[pos],score[idx]);pos+=pos&-pos
    return a[keep]
