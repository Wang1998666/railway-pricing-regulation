"""Publication figures from V4 outputs; preserve V3 panels and local insets."""
from common import *
import csv
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
plt.rcParams.update({'font.family':'Arial','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none','mathtext.fontset':'cm'})

def fig13():
    a=read(HERE/'exp1'/'analysis.json');fig,axes=plt.subplots(2,1,figsize=(8.5,9),layout='constrained')
    for ax,ci in zip(axes,['HN','WC']):
        rr=[r for r in a[ci]['selected']]
        with (HERE/'exp1'/'grid.csv').open(encoding='utf-8-sig') as f:
            rr=[dict(case_id=r['case_id'],cap=float(r['cap']),floor=float(r['floor']),profit_gain=float(r['profit_gain']),delta_W=float(r['delta_W'])) for r in csv.DictReader(f) if r['case_id']==ci and r['objective']=='profit']
        # Original cap-only endpoints are contextual references, outside the 35-point count.
        old=[r for p in (ROUND6/'grid').glob(ci+'*.json') for r in read(p)['rows'] if r['floor']==.95]
        caponly=[dict(case_id=ci,cap=r['cap'],floor=.95,profit_gain=r['profit_gain']/1000,delta_W=r['welfare']/1000) for r in old]
        allpoints=rr+caponly;points={}
        for r in allpoints:points.setdefault((round(r['profit_gain'],6),round(r['delta_W'],6)),[]).append(r)
        front=sorted(set((r['profit_gain'],r['delta_W']) for r in a[ci]['frontier']))
        ax.plot(*np.array(front).T,c='#374151',ls='--',lw=1,zorder=1)
        for (x,y),items in points.items():
            caprefs=[r for r in items if r['floor']==.95];floors=[r for r in items if r['cap']==1.2]
            cat=0 if caprefs else 1 if floors else 2;color=['#236DA6','#D57917','#199783'][cat];marker=['o','D','X'][cat]
            ax.scatter(x,y,c=color,marker=marker,s=45 if cat<2 else 33,edgecolors='white',linewidths=.5,zorder=4)
            if caprefs:
                cap=min(r['cap'] for r in caprefs);ax.annotate(f'{cap:.2f}',(x,y),xytext=(-15,-15) if ci=='HN' and cap==1 else (0,-17),textcoords='offset points',ha='center',fontsize=8,color=color)
        get=lambda c,e:next(r for r in rr if r['cap']==c and r['floor']==e)
        strict=get(1.2,1.);joint=get(1.05,1.)
        standout=get(1.2,.999 if ci=='HN' else .9995)
        ax.annotate(f"floor {standout['floor']:.4f}".rstrip('0'),(standout['profit_gain'],standout['delta_W']),xytext=(25,25) if ci=='HN' else (40,5),textcoords='offset points',fontsize=8,color='#B4620A',arrowprops=dict(arrowstyle='-',lw=.6,color='#B4620A'))
        ax.annotate('floor 1.00',(strict['profit_gain'],strict['delta_W']),xytext=(30,-15) if ci=='HN' else (-24,-36),textcoords='offset points',fontsize=8,color='#B4620A',arrowprops=dict(arrowstyle='-',lw=.6,color='#B4620A'))
        ax.annotate('cap 1.05 + floor 1.00',(joint['profit_gain'],joint['delta_W']),xytext=(-25,39) if ci=='HN' else (40,-66),textcoords='offset points',fontsize=8,color='#087F70',arrowprops=dict(arrowstyle='-',lw=.6,color='#087F70'))
        ref=reference(ci);w=record(ref,'P3','welfare');p0=record(ref,'P0','profit')
        ax.scatter((w['profit']-p0['profit'])/1000,w['welfare']/1000,marker='*',s=155,c='#9D3159',edgecolors='white',linewidths=.6,zorder=6)
        ax.axhline(0,c='#999999',lw=.6);ax.set_title(ci+' | proven-optimal P3 regulation outcomes',loc='left',fontweight='bold')
        ax.set_xlabel('Profit gain over P0 (thousand CNY/day)');ax.set_ylabel('Welfare change from P0 (thousand CNY/day)');ax.grid(alpha=.15);ax.margins(x=.12,y=.18)
        ins=ax.inset_axes([.59,.65,.36,.27]);ins.set_title('Strict floor: local detail',fontsize=8)
        for r,c,mk,label in [(strict,'#D57917','D','cap 1.20'),(joint,'#199783','X','cap 1.05')]:
            ins.scatter(r['profit_gain'],r['delta_W'],c=c,marker=mk,s=28)
            ins.annotate(label,(r['profit_gain'],r['delta_W']),xytext=(-4,-14) if label=='cap 1.20' else (5,7),textcoords='offset points',fontsize=7.5,ha='right' if label=='cap 1.20' else 'left',color=c)
        ins.margins(x=1.2,y=.7);ins.tick_params(labelsize=7);ins.xaxis.set_major_locator(MaxNLocator(3));ins.yaxis.set_major_locator(MaxNLocator(3));ins.grid(alpha=.15)
    handles=[Line2D([],[],marker=m,color=c,lw=0,label=l,markersize=6) for m,c,l in [('o','#236DA6','Cap alone (floor 0.95; baseline reference)'),('D','#D57917','Floor alone (cap 1.20)'),('X','#199783','Additional joint outcome'),('*','#9D3159','Central welfare optimum')]]+[Line2D([],[],color='#374151',ls='--',label='Refined sampled nondominated envelope',lw=1)]
    fig.legend(handles=handles,loc='outside lower center',ncol=2,frameon=False,fontsize=8.5)
    for ext in ['pdf','png','svg']:fig.savefig(HERE/'exp1'/f'fig13_cap_floor_frontier_v4.{ext}',dpi=240)
    plt.close(fig)

def fig17():
    import figures_round5 as src
    a=read(HERE/'exp4'/'analysis.json');combined=a['old_rows']+a['rows']
    def capture(fig,name):
        assert name=='calibration_dependence'
        for j,(ax,ci) in enumerate(zip(fig.axes[::2],['HN','WC','JX'])):
            ax.clear()
            for cap,ls,mk in [(1.1,':','^'),(1.2,'-','o'),(1.3,'--','s')]:
                rr=sorted([r for r in combined if r['case_id']==ci and r['objective']=='profit' and r['cap']==cap],key=lambda r:abs(r['anchor']))
                ax.plot([abs(r['anchor']) for r in rr],[r['delta_W'] for r in rr],c=src.CC[ci],ls=ls,marker=mk,ms=3)
            ax.axhline(0,c='#777',lw=.6);ax.axvline(.8,c='#999',lw=.6,ls='--')
            ax.set(title=f"({chr(97+j)}) {ci} ({'proven optimal' if ci!='JX' else 'search'})",xlabel='Own-product elasticity magnitude',ylabel='Commercial ΔW\n(thousand CNY/day)' if j==0 else '',xticks=[.6,.8,1.,1.2,1.5]);ax.grid(alpha=.12)
        fig.set_size_inches(8.5,6.6)
        from matplotlib.text import Text
        for t in fig.findobj(Text):t.set_fontfamily('Arial')
        for j,ax in enumerate(fig.axes[1::2]):ax.set_title(f'({chr(100+j)}) Baseline sensitivity ranges',fontsize=9)
        for ax in fig.axes:
            ax.tick_params(labelsize=8);ax.title.set_fontsize(9);ax.xaxis.label.set_fontsize(8);ax.yaxis.label.set_fontsize(8)
        for ext in ['pdf','png','svg']:fig.savefig(HERE/'exp4'/f'fig17_calibration_dependence_v4.{ext}',dpi=240)
        plt.close(fig)
    src.save=capture;src.calibration_dependence()

if __name__=='__main__':fig13();fig17()
