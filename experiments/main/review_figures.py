"""Static scientific figures with consistent calibrated costs and sampled boundaries."""
import json,collections
from functools import lru_cache
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from model import ROOT,Model,INCOMES
from analyze import groups,record,pair_feasible
import figures as old
import revision_figures as rev

CIS=['HN','WC','JX']; COLORS=['#17324D','#438EB0','#C78326']; OBJS=['profit','welfare']
plt.rcParams.update({'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7.5,'ytick.labelsize':7.5,'axes.spines.top':False,'axes.spines.right':False})
@lru_cache(maxsize=1)
def load():
    a=json.loads((ROOT/'review_analysis.json').read_text(encoding='utf-8')); c={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in CIS}; refs={ci:next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none') for ci in CIS}; return a,c,refs
old.load=load; rev.load=load
def save(fig,n):
    out=ROOT.parents[1]/'visualization'/'main_figures'; out.mkdir(exist_ok=True); fig.savefig(out/f'case_fig{n:02d}.pdf',bbox_inches='tight'); fig.savefig(out/f'case_fig{n:02d}.png',dpi=220,bbox_inches='tight'); plt.close(fig)
@lru_cache(maxsize=1)
def g2(): return groups('E2')
def e2(ci,inc,x): return next(g for g in g2() if g['job']['case']==ci and g['job']['income']==inc and not g['job']['spec'].get('road_contrast') and abs(g['job']['spec']['electric_scale']-x)<1e-9)

def figure04():
    a,c,refs=load(); fig=plt.figure(figsize=(6.61,5.8),layout='constrained'); gs=fig.add_gridspec(2,2,height_ratios=[1.4,1]); ax=fig.add_subplot(gs[0,:]); r=record(refs['WC'],'P0','profit'); m=Model(c['WC']); raw=m.evaluate(m.N0,np.ones((m.S,4,3)),True); qr=raw['qr'][0]; Q=np.array(r['Q']); pm=np.array(r['mode_probs']); pop=np.array(r['class_potential'])/1000; trips=np.array(r['class_trips'])/1000; tiers={t:np.array(r['tier_by_class'][t])/1000 for t in ['G','D','K']}; total=pop.sum()
    modes={name:(Q*pm[:,:,:,i]).sum(axis=(0,2))/1000 for i,name in enumerate(['Rail','Road','Auto'])}
    stages=[{'H':np.array([pop[0],0,0]),'M':np.array([0,pop[1],0]),'L':np.array([0,0,pop[2]])},{'Travel':trips,'No travel':pop-trips},modes,tiers,{}]
    for t in ['G','D','K']:
        for b in range(3):
            vals=qr[:,:,:,m.tier==t,b].sum(axis=(0,2,3))/1000
            if vals.sum()>0: stages[-1][f'{t}-{b+1}']=vals
    positions=[]
    for j,stage in enumerate(stages):
        ypos=0.; pos={}
        for name,vals in stage.items():
            pos[name]=[]
            for k,v in enumerate(vals): pos[name].append(ypos); ax.add_patch(Rectangle((j-.035,ypos),.07,v,facecolor=COLORS[k],edgecolor='white',lw=.2)); ypos+=v
            ax.text(j+.06,ypos-sum(vals)/2,name,va='center',fontsize=6.5); ypos+=total*.04
        positions.append(pos)
    links=[]
    for k,name in enumerate(['H','M','L']): links.extend([(0,name,'Travel',k,trips[k]),(0,name,'No travel',k,pop[k]-trips[k])])
    for name,vals in stages[2].items(): links.extend((1,'Travel',name,k,v) for k,v in enumerate(vals))
    for name,vals in stages[3].items(): links.extend((2,'Rail',name,k,v) for k,v in enumerate(vals))
    for name,vals in stages[4].items(): links.extend((3,name[0],name,k,v) for k,v in enumerate(vals))
    outgoing={}; incoming={}
    for j,src,dst,k,v in links:
        sk=(j,src,k); dk=(j+1,dst,k); old._band(ax,j+.035,j+1-.035,positions[j][src][k]+outgoing.get(sk,0),positions[j+1][dst][k]+incoming.get(dk,0),v,COLORS[k]); outgoing[sk]=outgoing.get(sk,0)+v; incoming[dk]=incoming.get(dk,0)+v
    ax.set(xlim=(-.2,4.8),ylim=(-total*.1,total*1.2)); ax.invert_yaxis(); ax.axis('off'); ax.set_title('(a) WC: class-specific composition; aggregate participation .85 / rail .70',loc='left')
    bx=fig.add_subplot(gs[1,0])
    for j,state in enumerate(['reference','uniform','polarized']):
        vot=60*np.array([.035,.03,.025])/(np.array([.012,.02,.035])*np.exp(-np.array([.7,.8,.9])*INCOMES[state])); bx.scatter(vot,np.arange(3)+j*.13,label=state,marker=['o','s','^'][j],s=25)
    bx.set(xscale='log',yticks=np.arange(3)+.13,yticklabels=['H','M','L'],xlabel='Value of time (CNY/h)',title='(b) VOT ratios preserved'); bx.invert_yaxis(); bx.legend(fontsize=6.5,frameon=False)
    cx=fig.add_subplot(gs[1,1])
    for j,ci in enumerate(CIS):
        mm=Model(c[ci]); w=int(np.argmax(mm.c['road_km'])); base=np.array(mm.c['road'])[w,:,0]; km=mm.c['road_km'][w]; high=base-km*np.array([.58*.5/mm.c['occupancy'],.12*.7,.2*.7,.3*.7]); yy=np.arange(4)+j*.17
        for i in range(4): cx.plot([high[i],base[i]],[yy[i]]*2,c=COLORS[j],lw=1)
        cx.scatter(base,yy,c=COLORS[j],s=15,label=f'{ci} ({km:.0f} km)'); cx.scatter(high,yy,facecolor='white',edgecolor=COLORS[j],s=15)
    cx.set(yticks=np.arange(4)+.17,yticklabels=['Auto','Coach','MaaS','Van'],xlabel='Cost per traveler (CNY)',title='(c) Longest OD; filled x=0 / hollow x=1'); cx.legend(fontsize=6.2,frameon=False); save(fig,4)

def figure06():
    a,c,refs=load(); fig,axs=plt.subplots(2,3,figsize=(6.61,4.3),layout='constrained')
    for i,obj in enumerate(OBJS):
        for j,ci in enumerate(CIS):
            ax=axs[i,j]; r=next(r for r in a['reference'] if r['case_id']==ci and r['objective']==obj); z=r['values']; vals=[(z[p]-z['P0'])/1000 for p in ['P1','P2','P3','P4']]
            ax.bar(range(4),vals,color=['#c4ced5','#438EB0','#17324D','#C78326'],width=.65)
            for k,v in enumerate(vals): ax.annotate(f'{v:.1f}',(k,v),xytext=(0,4),textcoords='offset points',ha='center',fontsize=7)
            ax.text(.03,.95,f'Factorial interaction: {r["factorial"]/1000:+.1f}k',transform=ax.transAxes,va='top',fontsize=7)
            ax.set(xticks=range(4),xticklabels=['Fare','Frequency','Joint','+ K'],title=f'{ci} / {obj}',ylabel='Gain over P0 (CNY thousand)' if j==0 else '',ylim=(0,max(vals)*1.32+1)); ax.tick_params(axis='x',rotation=25)
    save(fig,6)

def figure09():
    a,c,refs=load(); fig,axs=plt.subplots(3,3,figsize=(6.61,6.2),layout='constrained'); xs=[0,.05,.1,.2,.35,.5,.75,1.]
    for j,ci in enumerate(CIS):
        for k,inc in enumerate(['reference','uniform','polarized']):
            rr=[record(e2(ci,inc,x),'P0','profit') for x in xs]
            denominator=record(refs[ci],'P0','profit')['class_trips'][2]
            ys=[[r['rail_by_class'][2]/r['class_trips'][2]*100 for r in rr],[r['class_trips'][2]/denominator for r in rr],[(r['profit']+r['budget'])/1000 for r in rr]]
            for i in range(3): axs[i,j].plot(xs,ys[i],c=COLORS[k],marker=['o','s','^'][k],ms=3,lw=1,label=inc)
        axs[0,j].set_title(ci); axs[1,j].axhline(.95,c='#777777',ls='--',lw=.7); axs[2,j].axhline(0,c='#777777',ls='--',lw=.7)
        for i,lab in enumerate(['Low-income rail share (%)','Vulnerable-trip retention','Financial margin (CNY thousand)']): axs[i,j].set(ylabel=lab if j==0 else '',xlabel='Additional road-cost intensity x' if i==2 else '',xlim=(-.02,1.02))
    fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncols=3,frameon=False); save(fig,9)

def figure10():
    a,c,refs=load(); fig,axs=plt.subplots(2,3,figsize=(6.61,3.7),layout='constrained'); xs=[0,.05,.1,.2,.35,.5,.75,1.]; incs=['uniform','polarized']; colors=['#D6E5E6','#9FBDC9','#438EB0','#17324D','#C78326','#e5e7e9'];absolute=groups('E11')
    for j,ci in enumerate(CIS):
        for l,convention in enumerate(['Absolute reference','Same-state P0']):
            ax=axs[l,j];mat=np.full((2,8),5)
            for i,inc in enumerate(incs):
                for k,x in enumerate(xs):
                    g=next(g for g in absolute if g['job']['case']==ci and g['job']['income']==inc and abs(g['job']['spec']['electric_scale']-x)<1e-9) if l==0 else e2(ci,inc,x)
                    mat[i,k]=next((ii for ii,p in enumerate(['P0','P1','P2','P3','P4']) if pair_feasible(g,p)),5)
            ax.imshow(mat,cmap=ListedColormap(colors),vmin=0,vmax=5,aspect='auto',interpolation='nearest')
            for i in range(2):
                for k in range(8):ax.text(k,i,['0','F','N','J','K','?'][mat[i,k]],ha='center',va='center',fontsize=7.2,color='white' if mat[i,k] in [2,3] else '#17324D')
            ax.set(title=ci if l==0 else '',xticks=range(8),xticklabels=[f'{x:g}' for x in xs],yticks=range(2),yticklabels=incs if j==0 else [],xlabel='Road intensity x' if l==1 else '',ylabel=convention if j==0 else '');ax.tick_params(axis='x',rotation=45)
    fig.legend(handles=[Rectangle((0,0),1,1,color=co,label=la) for co,la in zip(colors,['P0','Fare','Frequency','Joint','+ K','Unresolved'])],loc='outside lower center',ncols=6,frameon=False,fontsize=7); save(fig,10)

def figure12():
    a,c,refs=load(); gg=groups('E10'); fig,axs=plt.subplots(3,2,figsize=(6.61,6.3),layout='constrained'); colors=['#e6e9ec','#C78326','#438EB0','#17324D']; costs=[.1,.25,.5,.75,1.]; xs=[0,.05,.1,.2,.35,.5,.75,1.]
    for i,ci in enumerate(CIS):
        for j,obj in enumerate(OBJS):
            ax=axs[i,j]; mat=np.zeros((len(xs),5))
            for u in range(5):
                for v in range(len(xs)):
                    g=next(g for g in gg if g['job']['id']==f'{ci}_{u:02d}_{v:02d}'); p=record(g,'P3',obj); r=record(g,'P4',obj); f3=pair_feasible(g,'P3'); f4=pair_feasible(g,'P4')
                    has_additions=np.array(r['N'])[[p['candidate'] for p in c[ci]['products']]].sum()>0
                    mat[v,u]=3 if not f4 else 2 if not f3 else 1 if has_additions and r['objective_value']-p['objective_value']>1e-4*max(1,abs(p['objective_value'])) else 0
            ax.imshow(mat,origin='lower',cmap=ListedColormap(colors),vmin=0,vmax=3,aspect='auto',interpolation='nearest'); ax.set(xticks=range(5),xticklabels=[f'{x:g}' for x in costs],yticks=range(len(xs)),yticklabels=[f'{x:g}' for x in xs],title=f'{ci} / {obj}',xlabel='K operating-cost multiplier' if i==2 else '',ylabel='Tested road intensity x' if j==0 else '')
            ax.set_xticks(np.arange(-.5,5,1),minor=True);ax.set_yticks(np.arange(-.5,len(xs),1),minor=True);ax.grid(which='minor',color='white',lw=.6);ax.tick_params(which='minor',length=0)
            if not np.any((mat==1)|(mat==2)): ax.text(.5,.5,'No improving K entry\non the tested grid',transform=ax.transAxes,ha='center',va='center',fontsize=8,bbox=dict(fc='white',ec='none',alpha=.9))
    fig.legend(handles=[Rectangle((0,0),1,1,color=co,label=la) for co,la in zip(colors,['K inactive / no gain','Objective gain','Feasibility recovery','Unresolved'])],loc='outside lower center',ncols=4,frameon=False,fontsize=7); save(fig,12)

def figure11():
    a,c,refs=load(); e3=groups('E3'); e6=groups('E6'); fig=plt.figure(figsize=(6.61,4.8),layout='constrained'); gs=fig.add_gridspec(2,6,height_ratios=[1.25,1.0])
    for j,ci in enumerate(CIS):
        ax=fig.add_subplot(gs[0,2*j:2*j+2]); cand=np.array([p['candidate'] for p in c[ci]['products']]); xs=[.1,.25,.5,.75,1.]
        for obj,col,marker,ls in [('profit','#17324D','o','-'),('welfare','#C78326','s','--')]:
            yy=[]
            for x in xs:
                label=ci+'_baseline' if x==1 else ci+f'_k_cost_{x}'; g=next(g for g in e3 if g['job']['id']==label); r=record(g,'P4',obj); yy.append(np.array(r['N'])[cand].sum() if r['feasible'] else np.nan)
            ax.plot(xs,yy,c=col,marker=marker,ls=ls,ms=3,label=obj)
        ax.set(title=ci,xlabel='K cost multiplier',ylabel='Additional K departures/day' if j==0 else '',xlim=(.05,1.03)); ax.legend(frameon=False,fontsize=6.5)
    mats=[]; labels=[]
    for obj in OBJS:
        mat=np.full((3,3),np.nan); lab={}
        for i,inc in enumerate(['reference','uniform','polarized']):
            for j,ci in enumerate(CIS):
                g=next(g for g in e6 if g['job']['case']==ci and g['job']['income']==inc); p=record(g,'P3',obj); s=record(g,'P3-sb',obj)
                if p['feasible'] and s['feasible']: mat[i,j]=max(0,(s['objective_value']-p['objective_value'])/1000); lab[i,j]=f'{mat[i,j]:.1f}'
                else: lab[i,j]='R' if s['feasible'] else '?'
        mats.append(mat); labels.append(lab)
    vmax=max(np.nanmax(m) for m in mats); axes=[]
    for j,obj in enumerate(OBJS):
        ax=fig.add_subplot(gs[1,3*j:3*j+3]); axes.append(ax); im=ax.imshow(mats[j],aspect='auto',cmap='YlGnBu',vmin=0,vmax=vmax); ax.set_facecolor('#e5e7e9')
        for (i,k),text in labels[j].items(): ax.text(k,i,text,ha='center',va='center',fontsize=8,color='white' if mats[j][i,k]>.65*vmax else '#17324D')
        ax.set(xticks=range(3),xticklabels=CIS,yticks=range(3),yticklabels=['Reference','Uniform','Polarized'] if j==0 else [],title=f'Seat-specific increment / {obj}')
    fig.colorbar(im,ax=axes,label='P3-sb minus P3 (CNY thousand)',shrink=.8); save(fig,11)

def figure13():
    a,c,refs=load(); gg=groups('E9'); fig=plt.figure(figsize=(6.61,5.5),layout='constrained'); gs=fig.add_gridspec(2,2,height_ratios=[1,1.2])
    for j,obj in enumerate(OBJS):
        sub=gs[0,j].subgridspec(2,1,height_ratios=[1,.15],hspace=.06);ax=fig.add_subplot(sub[0]);strip=fig.add_subplot(sub[1],sharex=ax);ymax=1.
        for k,ci in enumerate(CIS):
            cells=sorted([g for g in gg if g['job']['case']==ci],key=lambda g:g['job']['spec']['eta'])
            for pol,marker,filled in [('P3','o',True),('P4','s',False)]:
                baseline=record(refs[ci],pol,obj);base=baseline['objective_value'];xx=[baseline['eta']];yy=[0.];bad=[]
                for g in cells:
                    floor=g['job']['spec']['eta']
                    if floor<.975-1e-8: continue
                    r=record(g,pol,obj)
                    if r['feasible']: xx.append(floor); yy.append((base-r['objective_value'])/1000)
                    else: bad.append(floor)
                if yy: ymax=max(ymax,max(yy))
                ax.scatter(xx,yy,marker=marker,s=21,facecolors=COLORS[k] if filled else 'none',edgecolors=COLORS[k],label=f'{ci} {pol}')
                strip.scatter(bad,np.full(len(bad),k+.13*(pol=='P4')),marker='x',s=14,c=COLORS[k])
        ax.axvline(1,c='#777777',ls='--',lw=.7); ax.set(title=f'({chr(97+j)}) {obj.capitalize()}: sampled no-harm boundary',xlabel='Retention floor',ylabel='Objective loss\n(CNY thousand/day)' if j==0 else '',xticks=[.98,.99,1.,1.01],xlim=(.976,1.011)); ax.tick_params(axis='x',rotation=35);ax.yaxis.label.set_size(7)
        if j==0: ax.legend(ncols=2,fontsize=6.4,frameon=False)
        ax.set_xlabel('');ax.tick_params(labelbottom=False);strip.set(ylim=(-.5,3),yticks=[],xlabel='Retention floor');strip.text(.02,.5,'Unresolved',transform=strip.transAxes,fontsize=6,va='center');strip.spines['left'].set_visible(False);strip.set_facecolor('#f1f2f3');strip.tick_params(axis='x',rotation=35)
    ax=fig.add_subplot(gs[1,:]); eq=json.loads((ROOT/'equity_unique.json').read_text(encoding='utf-8')); good=[r for r in eq if r['feasible'] and abs(r['dG'])+abs(r['deta'])>1e-7]; zero=sum(r['feasible'] and abs(r['dG'])+abs(r['deta'])<=1e-7 for r in eq)
    for withdraw,col,marker,lab in [(False,'#438EB0','o','Observed K retained'),(True,'#C78326','^','Observed K departures withdrawn')]:
        rows=[r for r in good if (r['observed_K_removed']>0)==withdraw]; ax.scatter([r['dG'] for r in rows],[100*r['deta'] for r in rows],s=15,alpha=.55,c=col,marker=marker,label=lab)
    ax.axhline(0,c='#666666',lw=.6); ax.axvline(0,c='#666666',lw=.6); ax.set(title=f'(c) Unique feasible designs; {zero} zero-response designs omitted',xlabel='Change in worst-case cost ratio',ylabel='Vulnerable retention change (pp)'); xl=ax.get_xlim(); yl=ax.get_ylim(); ax.add_patch(Rectangle((min(xl[0],0),min(yl[0],0)),max(-xl[0],0),max(-yl[0],0),fc='#FCE9E1',ec='none',zorder=-1)); ax.legend(loc='upper center',bbox_to_anchor=(.5,-.21),ncols=2,fontsize=7,frameon=False); save(fig,13)

def figure14():
    a,c,refs=load(); fig,axs=plt.subplots(1,3,figsize=(6.61,3.2),layout='constrained')
    for ax,ci in zip(axs,CIS):
        rows=[r for r in a['governance'] if r['case_id']==ci and r['continuous']]
        for r in rows: ax.scatter(r['profit_gap']/1000,r['welfare_gap']/1000,c=COLORS[['reference','uniform','polarized'].index(r['income'])],s=20+20*r['intensity'],edgecolor='white',lw=.3,alpha=.85)
        ax.set(title=f'{ci} ({len(rows)} states)',xlabel='Profit compensation (CNY thousand)',ylabel='Welfare gain (CNY thousand)' if ci=='HN' else ''); ax.margins(.18)
        if rows:
            r=max(rows,key=lambda r:r['welfare_gap']); ax.annotate(f'{r["income"]}; x={r["intensity"]:g}',(r['profit_gap']/1000,r['welfare_gap']/1000),xytext=(-4,7),textcoords='offset points',ha='right',fontsize=6.5)
    fig.legend(handles=[Line2D([],[],marker='o',ls='',c=co,label=inc) for inc,co in zip(['reference','uniform','polarized'],COLORS)],loc='outside lower center',ncols=3,frameon=False); save(fig,14)

def appendix():
    a,c,refs=load(); fig,axs=plt.subplots(2,3,figsize=(6.61,4.4),layout='constrained')
    for i,cap in enumerate([.95,1.]):
        for j,ci in enumerate(CIS):
            ax=axs[i,j]
            for var,co in zip([.5,.7,.9],COLORS):
                rr=sorted([r for r in a['headroom'] if r['case_id']==ci and r['objective']=='profit' and r['spec']['lambda']==cap and r['spec']['variable_share']==var],key=lambda r:r['spec']['ref_load']); ax.plot([r['spec']['ref_load'] for r in rr],[r['gain']/1000 for r in rr],c=co,marker='o',ms=3,label=f'Variable {var:.0%}')
            ax.set(title=f'{ci}; ceiling {cap:.2f}',xlabel='Reference peak load',ylabel='P3 profit gain (CNY thousand)' if j==0 else '')
    fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncols=3,frameon=False); out=ROOT.parents[1]/'visualization'/'main_figures'; fig.savefig(out/'review_appendix_headroom.pdf',bbox_inches='tight'); fig.savefig(out/'review_appendix_headroom.png',bbox_inches='tight',dpi=180); plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(6.61,2.8),layout='constrained'); im=None
    vmax=max(r['gain']/1000 for r in a['network'] if r['objective']=='profit' and 'chi' in r['spec'] and r['feasible'])
    for ax,ci in zip(axs,CIS):
        mat=np.full((3,3),np.nan)
        for i,bg in enumerate([0,.15,.3]):
            for j,chi in enumerate([.25,.5,1.]):
                r=next(r for r in a['network'] if r['case_id']==ci and r['objective']=='profit' and r['spec'].get('background')==bg and r['spec']['chi']==chi); mat[i,j]=r['gain']/1000 if r['feasible'] else np.nan
        im=ax.imshow(mat,aspect='auto',cmap='YlGnBu',vmin=0,vmax=vmax); ax.set(xticks=range(3),xticklabels=['.25','.50','1.00'],yticks=range(3),yticklabels=['0','.15','.30'],title=ci,xlabel='Cost share',ylabel='Background fraction' if ci=='HN' else '')
        for i in range(3):
            for j in range(3):
                if j==2 and i>0:ax.add_patch(Rectangle((j-.5,i-.5),1,1,fc='#e5e7e9',ec='#aaa',hatch='///'));text='Excluded'
                else:text='?' if np.isnan(mat[i,j]) else f'{mat[i,j]:.0f}'
                ax.text(j,i,text,ha='center',va='center',fontsize=6.5,color='white' if np.isfinite(mat[i,j]) and mat[i,j]>.65*vmax and not(j==2 and i>0) else '#17324D')
    fig.colorbar(im,ax=axs.tolist(),label='P3 profit gain (CNY thousand)',shrink=.8); fig.savefig(out/'review_appendix_network.pdf',bbox_inches='tight'); fig.savefig(out/'review_appendix_network.png',bbox_inches='tight',dpi=180); plt.close(fig)

def schematic_alternative():
    a,c,refs=load(); fig,axs=plt.subplots(3,1,figsize=(6.61,3.4),layout='constrained'); cities={'HN':['Hangzhou','Nanjing'],'WC':['Wuhan','Changsha'],'JX':['Ganzhou',"Ji'an",'Nanchang','Jiujiang']}
    for ax,ci in zip(axs,CIS):
        m=Model(c[ci]); xx=np.linspace(.16,.85,len(cities[ci])); ax.set(xlim=(0,1),ylim=(-.3,1.0)); ax.axis('off')
        ax.text(0,.85,ci,fontweight='bold',fontsize=9); ax.text(.98,.85,f'{int((m.N0-m.Nmin).sum())} adjustable / {int(m.Nmin.sum())} protected',ha='right',fontsize=8)
        for y,col,ls,lab in [(.55,'#17324D','-','G/D'),(.30,'#C78326','--','K'),(.05,'#B44334',':','Road')]: ax.plot(xx,np.full(len(xx),y),c=col,ls=ls,lw=1.7); ax.text(.025,y,lab,va='center',fontsize=8,color=col)
        for x,name in zip(xx,cities[ci]): ax.scatter(x,.55,c='white',edgecolor='#17324D',s=22,zorder=3); ax.text(x,-.16,name,ha='center',fontsize=8)
    fig.suptitle('Service-network topology (not a geographic map)',fontsize=10); out=ROOT.parents[1]/'visualization'/'main_figures'; fig.savefig(out/'review_corridor_schematic.pdf',bbox_inches='tight'); fig.savefig(out/'review_corridor_schematic.png',bbox_inches='tight',dpi=200); plt.close(fig)

def polarization_plot():
    a,c,refs=load();fig,axs=plt.subplots(3,3,figsize=(6.61,5.5),layout='constrained');xs=[0,.05,.1,.2,.35,.5,.75,1.]
    for j,ci in enumerate(CIS):
        den=record(refs[ci],'P0','profit')['class_trips'][2];gd=np.array([p['tier']!='K' for p in c[ci]['products']])
        for inc,col,mark in [('uniform','#438EB0','o'),('polarized','#C78326','^')]:
            rs=[record(e2(ci,inc,x),'P3','profit') for x in xs]
            fares=[(np.array(r['N'])[gd]*np.array(r['phi'])[gd,:,0]).sum()/np.array(r['N'])[gd].sum() if r['feasible'] else np.nan for r in rs]
            values=[fares,[np.array(r['N']).sum() if r['feasible'] else np.nan for r in rs],[r['class_trips'][2]/den if r['feasible'] else np.nan for r in rs]]
            for i in range(3):axs[i,j].plot(xs,values[i],c=col,marker=mark,ms=3,lw=1,label=inc)
        for i,label in enumerate(['Common G/D fare multiplier','Total departures/day','Absolute vulnerable retention']):axs[i,j].set(ylabel=label if j==0 else '',xlabel='Road intensity x' if i==2 else '',title=ci if i==0 else '')
    fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncols=2,frameon=False);out=ROOT.parents[1]/'visualization'/'main_figures';fig.savefig(out/'round2_polarization.pdf',bbox_inches='tight');fig.savefig(out/'round2_polarization.png',bbox_inches='tight',dpi=200);plt.close(fig)

if __name__=='__main__':
    for n in [4,6,7,8,9,10,11,12,13,14]:
        if n==7: rev.figure07()
        elif n==8: old.figure08()
        elif n==11: figure11()
        else: globals()[f'figure{n:02d}']()
    appendix()
    polarization_plot()
