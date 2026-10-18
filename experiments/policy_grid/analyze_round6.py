"""Independent grid verification, publication scope ledger and frontier plot."""
import sys,json,csv,collections,hashlib,platform,importlib.metadata as im
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'main';sys.path.insert(0,str(BASE))
import numpy as np
from model import Model,dump
from analyze import groups,record
from verify import scalar
from run_round6 import check

def main():
    rows=[]
    for p in sorted((HERE/'grid').glob('*.json')):
        g=json.loads(p.read_text(encoding='utf-8'));assert g['complete']
        for a in g['rows']:
            # Snapshot mutable model metadata at each recorded floor.
            a['record']['spec']={'fare_cap':a['cap'],'eta':a['floor']}
            m=Model(json.loads((BASE/'inputs'/f"{a['case_id']}.json").read_text(encoding='utf-8')),spec=a['record']['spec'])
            a['independent_error']=check(m,a['record'])
            assert a['record']['meta']['certificate']
            rows.append(a)
        dump(p,g)
    assert len(rows)==60
    summary={};frontier=[]
    for ci in ['HN','WC']:
        rr=[r for r in rows if r['case_id']==ci]
        for r in rr:
            r['nondominated']=not any(s['profit_gain']>=r['profit_gain']-1e-5 and s['welfare']>=r['welfare']-1e-5 and (s['profit_gain']>r['profit_gain']+1e-5 or s['welfare']>r['welfare']+1e-5) for s in rr)
        get=lambda cap,floor:next(r for r in rr if np.isclose(r['cap'],cap) and np.isclose(r['floor'],floor))
        summary[ci]={k:get(c,f) for k,c,f in [('freeze',1.,.95),('cap105',1.05,.95),('floor100',1.2,1.),('joint105_100',1.05,1.),('joint100_100',1.,1.),('central',1.2,.95)]}
        frontier.extend(r for r in rr if r['nondominated'])
        # Domain nesting implies no tighter feasible domain can raise optimum profit.
        for a in rr:
            for b in rr:
                if a['cap']<=b['cap'] and a['floor']>=b['floor']:
                    assert a['record']['profit']<=b['record']['profit']+.01
    with (HERE/'cap_floor_frontier.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['case_id','cap','floor','profit_gain','welfare','U_change','departures','fare','nondominated','independent_error'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    prior=json.loads((BASE/'round5_analysis.json').read_text(encoding='utf-8'));opens={(r['state'],r['policy'],r['objective']) for r in prior['unresolved_certification']}
    ledger=[]
    for p in sorted((BASE/'runs').glob('*/*.json')):
        g=json.loads(p.read_text(encoding='utf-8'))
        for r in g['records']:
            if (g.get('state_key'),r['policy'],r['objective']) in opens:
                ledger.append(dict(experiment=g['job']['experiment'],job=g['job']['id'],state=g['state_key'],case_id=r['case_id'],policy=r['policy'],objective=r['objective'],feasible=r['feasible'],value=r['objective_value'],master_status=r['meta'].get('master_status'),scope='feasible witness' if r['feasible'] else 'no feasible witness; unresolved'))
    with (HERE/'reported_open_scope.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
    missing=[]
    for g in groups('E7'):
        if not any(r['feasible'] for r in g['records'] if r['policy']=='P4'):
            missing.append(dict(job=g['job'],P3_status='certified infeasible' if all(r['meta'].get('infeasibility_certificate') for r in g['records'] if r['policy']=='P3') else 'open',P4_status='certified infeasible' if all(r['meta'].get('infeasibility_certificate') for r in g['records'] if r['policy']=='P4') else 'time-limited; no feasible witness'))
    env=json.loads((BASE/'environment.json').read_text(encoding='utf-8'));env.update(cpu='AMD Ryzen 7 4800H with Radeon Graphics',physical_cores=8,logical_processors=16,physical_memory_bytes=16505966592,os_caption='Windows 11 Pro',os_architecture='64 bit',coptpy=im.version('coptpy'),highs='1.12.0',round5_workers=8,round6_workers=4,solver_threads_per_worker=1,blas_threads_per_worker=1,lp_time_limit_seconds=30,ordinary_mip_time_limit_seconds=[120,180],priority_mip_time_limit_seconds=600,copt_relative_gap=0,copt_absolute_gap_scaled=1e-9,copt_feasibility_tolerance=1e-9,copt_dual_tolerance=1e-9,certificate_gap_CNY_per_day=.01)
    dump(HERE/'environment.json',env)
    variants=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((HERE/'variants').glob('*.json'))]
    for g in variants:
        from run_round5 import engine
        for r in g['records']:check(engine(g['job']),r)
    dump(HERE/'independent_verification.json',dict(passed=True,grid_records=60,variant_records=4,accounting_max_error=max(r['independent_error'] for r in rows),checks=['scalar demand/accounting/retention/load','integer and authority bounds','fixed K','fleet and paths','OD service and daily incumbents','finance and participation','fare bands and menu','common fares and policy membership','nested-domain profit ordering'],source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'run_round6.py',BASE/'verify.py']}))
    dump(HERE/'round6_analysis.json',dict(grid_points=len(rows),grid_certificates=60,independent_max_error=max(r['independent_error'] for r in rows),summary=summary,frontier=frontier,open_job_occurrences=len(ledger),open_feasible_occurrences=sum(r['feasible'] for r in ledger),open_experiments=dict(collections.Counter(r['experiment'] for r in ledger)),missing_broad=missing,variants=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((HERE/'variants').glob('*.json'))]))
    plot(rows)
    print('GRID verified',len(rows),'maxerr',max(r['independent_error'] for r in rows))
    for ci,ss in summary.items():
        print(ci,{k:(round(r['profit_gain']/1000,1),round(r['welfare']/1000,1),r['departures'],round(r['fare'],4)) for k,r in ss.items()})

def plot(rows):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import MaxNLocator
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(2,1,figsize=(8.2,9.0),layout='constrained')
    for ax,ci in zip(axes,['HN','WC']):
        rr=[r for r in rows if r['case_id']==ci];points={}
        for r in rr:
            key=(round(r['profit_gain'],3),round(r['welfare'],3));points.setdefault(key,[]).append(r)
        front=sorted({(round(r['profit_gain']/1000,6),round(r['welfare']/1000,6)) for r in rr if r['nondominated']})
        ax.plot(*np.array(front).T,color='#374151',lw=1,ls='--',zorder=1)
        for key,items in points.items():
            caponly=any(np.isclose(r['floor'],.95) for r in items);flooronly=any(np.isclose(r['cap'],1.2) for r in items)
            cat=0 if caponly else 1 if flooronly else 2
            color=['#236DA6','#D57917','#199783'][cat];marker=['o','D','X'][cat]
            x,y=np.array(key)/1000;ax.scatter(x,y,c=color,marker=marker,s=65 if cat<2 else 45,edgecolors='white',linewidths=.7,zorder=4)
            if caponly:
                cap=min(r['cap'] for r in items if np.isclose(r['floor'],.95))
                ax.annotate(f'{cap:.2f}',(x,y),xytext=(0,-17),textcoords='offset points',ha='center',fontsize=9,color=color)
            elif flooronly:
                floor=max(r['floor'] for r in items if np.isclose(r['cap'],1.2))
                offset=(9,26) if ci=='WC' and floor==1. else (9,8)
                ax.annotate(f'floor {floor:.2f}',(x,y),xytext=offset,textcoords='offset points',fontsize=9,color=color)
        joint=next(r for r in rr if np.isclose(r['cap'],1.05) and np.isclose(r['floor'],1.))
        ax.annotate('cap 1.05 + floor 1.00',(joint['profit_gain']/1000,joint['welfare']/1000),xytext=(55,-36) if ci=='HN' else (30,-68),textcoords='offset points',fontsize=9,color='#087F70',arrowprops={'arrowstyle':'-','color':'#087F70','lw':.6})
        ref=next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none');w=record(ref,'P3','welfare');p0=record(ref,'P0','profit')
        ax.scatter((w['profit']-p0['profit'])/1000,w['welfare']/1000,marker='*',s=190,c='#9D3159',edgecolors='white',linewidths=.7,zorder=5)
        ax.axhline(0,c='#999999',lw=.7);ax.set_title(ci+'  |  certified P3 regulation outcomes',loc='left',fontweight='bold',fontsize=11)
        ax.set_xlabel('Profit gain over P0 (CNY thousand/day)');ax.set_ylabel('Welfare change from P0 (CNY thousand/day)');ax.grid(alpha=.15);ax.margins(x=.12,y=.16)
        ins=ax.inset_axes([.56,.63,.40,.30]);ins.set_title('Strict floor: local detail',fontsize=9)
        strict=next(r for r in rr if np.isclose(r['cap'],1.2) and np.isclose(r['floor'],1.))
        for r,c,mk,label in [(strict,'#D57917','D','cap 1.20'),(joint,'#199783','X','cap 1.05')]:
            x,y=r['profit_gain']/1000,r['welfare']/1000;ins.scatter(x,y,c=c,marker=mk,s=35,zorder=3)
            ins.annotate(label,(x,y),xytext=(4,-15 if label=='cap 1.20' else 7),textcoords='offset points',fontsize=9,ha='left' if label=='cap 1.05' else 'right',color=c)
        ins.margins(x=.6,y=.55);ins.xaxis.set_major_locator(MaxNLocator(nbins=3));ins.yaxis.set_major_locator(MaxNLocator(nbins=3));ins.tick_params(labelsize=8.5);ins.grid(alpha=.15)
    handles=[Line2D([],[],marker=m,color=c,lw=0,label=l,markersize=7) for m,c,l in [('o','#236DA6','Cap alone (floor 0.95)'),('D','#D57917','Floor alone (cap 1.20)'),('X','#199783','Additional joint outcome'),('*','#9D3159','Welfare optimum')]]
    handles.append(Line2D([],[],color='#374151',ls='--',label='Sampled nondominated envelope',lw=1))
    fig.legend(handles=handles,loc='outside lower center',ncol=2,frameon=False,fontsize=10)
    for ext in ['pdf','png']:fig.savefig(HERE.parents[1]/'visualization'/'main_figures'/f'round6_frontier.{ext}',dpi=240)
    plt.close(fig)
if __name__=='__main__':main()
