"""Forward-only decomposition of the original Fig. 15 feasible library."""
from common import *
import csv,collections

def metrics(m,n,ph,refQ,vot):
    z=m.evaluate(n,ph,True);Q=z['Q'][0];pm=z['mode_probs'][0];qr=z['qr'][0]
    access=np.array(m.c['access']); rt=m.runtime
    eff=n.copy()
    for s,p in m.parent.items():eff[p]+=n[s];eff[s]=0
    sc=15*np.array([3,8,3,10])[None,:]/np.maximum(eff,1)
    if m.displacement_cap is not None:sc=np.minimum(sc,m.displacement_cap)
    # Attributes: monetary, in-vehicle, access, wait, schedule, reliability, transfers.
    attrs=np.zeros((m.W,4,m.S,3,7))
    attrs[...,0]=m.fare[:,None,:,:]*ph.transpose(1,0,2)[None]+access[:,None,None,None,1]
    attrs[...,1]=rt[:,None,:,None];attrs[...,2]=access[:,None,None,None,0];attrs[...,3]=10
    attrs[...,4]=sc.T[None,:,:,None]
    attrs[...,5]=rt[:,None,:,None]*np.array([{'G':.02,'D':.03,'K':.08}[t] for t in m.tier])[None,None,:,None]
    ratio=m.beta[:,:7]/m.beta[:,0,None]
    railown=np.einsum('whsbj,kj->wkhsb',attrs,ratio)
    railcommon=np.einsum('whsbj,j->whsb',attrs,vot)
    monetary=attrs[...,0]
    rq=np.divide(qr,Q[:,:,:,None,None],out=np.zeros_like(qr),where=Q[:,:,:,None,None]>0)
    own=(rq*railown).sum(axis=(3,4));gc=(rq*railcommon[:,None]).sum(axis=(3,4));cash=(rq*monetary[:,None]).sum(axis=(3,4))
    roadown=np.einsum('wij,kj->wki',m.road[:,:,:7],ratio);roadcommon=m.road[:,:,:7]@vot
    for values,dest in [(roadown,own),(np.broadcast_to(roadcommon[:,None],roadown.shape),gc),(np.broadcast_to(m.road[:,None,:,0],roadown.shape),cash)]:
        dest+=pm[...,1]*(m.road_probs*values[:,:,None,1:]).sum(axis=-1)+pm[...,2]*values[:,:,None,0]
    mean=(Q*own).sum(axis=1)/Q.sum(axis=1);G=own/mean[:,None]
    assert np.max(abs(G.max(axis=1)-z['G'][0]))<1e-10
    fixedmean=(refQ*own).sum(axis=1)/refQ.sum(axis=1)
    commonmean=(Q*gc).sum(axis=1)/Q.sum(axis=1)
    maximum=G.max(axis=1);ties=np.isclose(G,maximum[:,None,:],atol=1e-10,rtol=0);shares=ties/ties.sum(axis=1,keepdims=True)
    worst=np.isclose(maximum,maximum.max(),atol=1e-10,rtol=0)
    return dict(Gmax=float(maximum.max()),Gfix=float((own/fixedmean[:,None]).max()),Lcommon=float((gc[:,2]/commonmean).max()),Lcash=float((Q[:,2]*cash[:,2]).sum()/Q[:,2].sum()),Ltrips=float(Q[:,2].sum()),cell_shares=shares.sum(axis=(0,2)).tolist(),cells=m.W*4,worst_shares=(shares.transpose(0,2,1)[worst].mean(axis=0)).tolist(),Q=Q,scalar_profit=float(z['profit'][0]))

def main():
    started=time.perf_counter()
    assert read(HERE/'step0_status.json')['passed'];outdir=HERE/'exp2';outdir.mkdir(exist_ok=True)
    library=[a for a in read(BASE/'equity_unique.json') if a['feasible']];assert len(library)==1842
    cache={};rows=[];cell=np.zeros(3);worst=np.zeros(3);totalcells=0;maxerr=0
    for i,a in enumerate(library):
        eval_start=time.perf_counter()
        key=json.dumps([a['case_id'],a['income'],a['electric'],a['spec']],sort_keys=True)
        if key not in cache:
            m=engine(dict(case=a['case_id'],income=a['income'],electric=a['electric'],spec=a['spec']))
            ref=engine(dict(case=a['case_id']));weights=ref.qbar.sum(axis=(0,2));vot=np.average(ref.beta[:,:7]/ref.beta[:,0,None],axis=0,weights=weights)
            refQ=m.evaluate(m.N0,np.ones((m.S,4,3)),True)['Q'][0];b=metrics(m,m.N0,np.ones((m.S,4,3)),refQ,vot);cache[key]=(m,vot,refQ,b)
        m,vot,refQ,b=cache[key];n=np.array(a['N'],float);ph=np.array(a['phi']);v=metrics(m,n,ph,refQ,vot)
        independent=scalar(m.c,n,ph,m.income,m.electric,m.spec)
        err=max(abs(independent['profit']-v['scalar_profit']),np.max(abs(independent['Q']-v['Q'])));assert err<1e-5;maxerr=max(maxerr,float(err))
        assert abs((v['Gmax']-b['Gmax'])-a['dG'])<1e-9
        row=dict(design_id=i,case_id=a['case_id'],source_job=a['id'],income=a['income'],electric=a['electric'],config_sha256=hashlib.sha256(key.encode()).hexdigest(),design_hash=design_hash(a),git_commit=git(),status='forward evaluation',dG=a['dG'],deta=a['deta'],delta_L_trips=v['Ltrips']-b['Ltrips'],Gfix=v['Gfix'],delta_Gfix=v['Gfix']-b['Gfix'],L_common_ratio=v['Lcommon'],delta_L_common_ratio=v['Lcommon']-b['Lcommon'],L_monetary_CNY=v['Lcash'],delta_L_monetary_CNY=v['Lcash']-b['Lcash'],common_VOT_CNY_hour=vot[1]*60,scalar_error=err)
        for k,c in enumerate(['H','M','L']):row['argmax_worst_'+c]=v['worst_shares'][k];row['argmax_cells_'+c]=v['cell_shares'][k]/v['cells']
        row.update(evaluation_seconds=time.perf_counter()-eval_start,solver='none: V3 forward evaluator',feasible_in_original_library=True)
        rows.append(row);cell+=v['cell_shares'];worst+=v['worst_shares'];totalcells+=v['cells']
        if (i+1)%200==0:print('EXP2',i+1,flush=True)
    def quadrants(metric):
        x=np.array([r[metric] for r in rows]);y=np.array([r['deta'] for r in rows]);return {f'{sx:+d},{sy:+d}':int(((x*sx>1e-7)&(y*sy>1e-7)).sum()) for sx in [-1,1] for sy in [-1,1]}|{'on_axis':int(((abs(x)<=1e-7)|(abs(y)<=1e-7)).sum())}
    ll=[r for r in rows if r['dG']<-1e-7 and r['deta']<-1e-7];assert len(ll)==341
    stats=dict(n=len(rows),lower_left=len(ll),common_VOT_CNY_hour=sorted(set(round(r['common_VOT_CNY_hour'],10) for r in rows)),
      argmax_cells=dict(zip(['H','M','L'],cell/totalcells)),argmax_worst=dict(zip(['H','M','L'],worst/len(rows))),
      lower_left_L_exit_share=sum(r['delta_L_trips']<-1e-7 for r in ll)/len(ll),lower_left_H_argmax_share=float(np.mean([r['argmax_worst_H'] for r in ll])),
      lower_left_fixed_not_falling=sum(r['delta_Gfix']>=-1e-7 for r in ll)/len(ll),quadrants={k:quadrants(k) for k in ['dG','delta_L_common_ratio','delta_L_monetary_CNY','delta_Gfix']},scalar_max_error=maxerr)
    dump(outdir/'analysis.json',stats)
    dump(outdir/'run_manifest.json',dict(git_commit=git(),library_sha256=sha(BASE/'equity_unique.json'),script_sha256=sha(Path(__file__)),status='forward evaluation; no optimization',design_count=len(rows),seconds=time.perf_counter()-started,scalar_max_error=maxerr,common_VOT_CNY_hour=97.5714285714))
    with (outdir/'library_diagnostics.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    text=['# EXP-2 cost-ratio diagnostics','',json.dumps(stats,indent=2),'',
      'Aggregation matches Fig. 15: Gmax is the maximum over OD-period cells of the maximum class generalized cost divided by the realized-trip-weighted class mean in that cell. L common-VOT burden is the maximum OD-period L ratio; monetary burden is the L-trip-weighted daily mean across OD-periods. Changes use each design\'s same-state P0.',
      'The common in-vehicle VOT is population-weighted at the central unperturbed reference state and held fixed across every library configuration. Access, wait, schedule, reliability and transfer valuations use the corresponding population-weighted central reference coefficients; this gives every class the same attribute valuations while retaining their evaluated choices. Ties split attribution equally. Canonical library designs pool parent/candidate K; feasibility is the original library\'s union over tested configurations, not a new policy-feasibility claim.',
      'Verdict: '+('Both low-income participation loss and high-VOT-class burdens are present; the fixed-weight comparison quantifies when changing participation weights is necessary for the reported cost-ratio fall.' if stats['lower_left_H_argmax_share']>0 else 'Low-income participation loss is present; class and fixed-weight results identify the cost-ratio mechanism.')]
    (outdir/'summary.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')
if __name__=='__main__':main()
