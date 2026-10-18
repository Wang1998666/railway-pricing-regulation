"""Final HN label-position adjustment using unchanged certified grid values."""
import sys,csv
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'experiments'/'main'))
import numpy as np
from analyze import groups,record
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
                ax.annotate(f'{cap:.2f}',(x,y),xytext=(-15,-14) if ci=='HN' and cap==1. else (0,-17),textcoords='offset points',ha='right' if ci=='HN' and cap==1. else 'center',fontsize=9,color=color)
            elif flooronly:
                floor=max(r['floor'] for r in items if np.isclose(r['cap'],1.2))
                offset=(22,-6) if ci=='HN' and floor==1. else ((9,26) if ci=='WC' and floor==1. else (9,8))
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
    for ext in ['pdf','png']:fig.savefig(HERE.parent/'visualization'/'main_figures'/f'round6_frontier.{ext}',dpi=240)
    plt.close(fig)
if __name__=='__main__':
    with (HERE.parent/'experiments'/'policy_grid'/'cap_floor_frontier.csv').open(encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    for r in rows:
        for k in ['cap','floor','profit_gain','welfare']:r[k]=float(r[k])
        r['nondominated']=r['nondominated']=='True'
    plot(rows)
