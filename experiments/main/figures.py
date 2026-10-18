"""Shared plotting functions; fig03.py--fig14.py are reproducible entry points.
All plotting inputs are archived calibrated inputs and saved run records.
"""
import json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Rectangle,PathPatch
from matplotlib.path import Path as MPath
from matplotlib import gridspec
from analyze import groups,record,pair_feasible
from model import ROOT,INCOMES

OUT=ROOT.parents[1]/'visualization'/'main_figures'
TIERS={'G':'#0072B2','D':'#009E73','K':'#E69F00'}
COLORS=['#08306B','#4292C6','#9ECAE1']
CIS=['HN','WC','JX']; PERIODS=['AM','Day','PM','Night']; OBJS=['profit','welfare']
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':8.5,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7.5,'ytick.labelsize':7.5,'pdf.fonttype':42,'savefig.dpi':180,'axes.spines.top':False,'axes.spines.right':False})

def load():
    a=json.loads((ROOT/'analysis.json').read_text(encoding='utf-8'))
    c={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in CIS}
    refs={ci:next(g for g in groups('E2') if g['job']['id']==f'{ci}_reference_none') for ci in CIS}
    return a,c,refs
def save(fig,n):
    fig.savefig(OUT/f'case_fig{n:02d}.pdf',bbox_inches='tight',pad_inches=.06)
    fig.savefig(OUT/f'case_fig{n:02d}.png',bbox_inches='tight',pad_inches=.06); plt.close(fig)
def labels(axs):
    for i,ax in enumerate(np.ravel(axs)): ax.text(-.1,1.03,f'({chr(97+i)})',transform=ax.transAxes,fontweight='bold')

def figure03():
    a,c,ref=load(); fig,axs=plt.subplots(3,1,figsize=(6.61,3.9),layout='constrained')
    nodes={'HN':['HZ','NJ'],'WC':['WH','CS'],'JX':['GZ','JA','NC','JJ']}
    for ax,ci in zip(axs,CIS):
        case=c[ci]; xx=np.linspace(.12,.88,len(nodes[ci])); ax.plot(xx,np.zeros(len(xx)),color=TIERS['G'],lw=2); ax.plot(xx,np.full(len(xx),-.18),color=TIERS['K'],lw=1)
        for x,name in zip(xx,nodes[ci]): ax.scatter(x,0,facecolor='white',edgecolor='black',zorder=3,s=35); ax.text(x,-.07,name,ha='center',va='top')
        ax.text(.01,.35,ci,fontweight='bold'); ax.text(.98,.35,'0% adjustable\nobserved departures',ha='right',fontsize=7.5)
        N=np.array([p['N0'] for p in case['products']]); tiers=np.array([p['tier'] for p in case['products']]); route=np.array([p['route'] for p in case['products']]); E=len(xx)-1
        for e in range(E):
            mid=(xx[e]+xx[e+1])/2; gs=[int(N[(tiers==t)&(route[:,e if t!='K' else E+e]>0)].sum()) for t in ['G','D','K']]
            ax.text(mid,.13,' / '.join(map(str,gs))+' G/D/K',ha='center',fontsize=7.5)
            cap=np.array(case['path_capacity'])[:,e]; ax.text(mid,-.24,'paths '+('/'.join(str(int(x)) for x in cap)),ha='center',fontsize=6.7)
        if ci=='JX':
            for p in case['products']:
                if not p['candidate']: continue
                sig=np.flatnonzero(p['serve']); endpoints=[case['ods'][w].split('-') for w in sig]; lo=min(case['cities'].index(x[0]) for x in endpoints); hi=max(case['cities'].index(x[1]) for x in endpoints)
                x=np.linspace(xx[lo],xx[hi],50); height=.09+.015*int(p['id'][-2:]); y=-.32-height*np.sin(np.pi*(x-xx[lo])/(xx[hi]-xx[lo])); serves_gznc=any(pair==['赣州','南昌'] for pair in endpoints)
                ax.plot(x,y,color='#D55E00' if serves_gznc else '#777777',lw=.5+.12*len(sig),alpha=.75)
        ax.set(xlim=(0,1),ylim=(-.65,.5)); ax.axis('off')
    save(fig,3)

def _band(ax,x0,x1,y0,y1,width,color):
    vertices=[(x0,y0),(x0+.25,y0),(x1-.25,y1),(x1,y1),(x1,y1+width),(x1-.25,y1+width),(x0+.25,y0+width),(x0,y0+width),(x0,y0)]
    codes=[MPath.MOVETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.LINETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=color,alpha=.45,edgecolor='none'))
def figure04():
    a,c,refs=load(); fig=plt.figure(figsize=(6.61,5.8),layout='constrained'); gs=fig.add_gridspec(2,2,height_ratios=[1.4,1]); ax=fig.add_subplot(gs[0,:]); r=record(refs['WC'],'P0','profit'); cc=c['WC']; pop=np.array(r['class_potential'])/1000; trips=np.array(r['class_trips'])/1000; tiers={t:np.array(r['tier_by_class'][t])/1000 for t in TIERS}; total=pop.sum()
    stages=[{'H':np.array([pop[0],0,0]),'M':np.array([0,pop[1],0]),'L':np.array([0,0,pop[2]])},{'Travel':trips,'No travel':pop-trips},{'Rail':np.array(r['rail_by_class'])/1000,'Road':trips*.3*.6,'Auto':trips*.3*.4},tiers,{}]
    for t in TIERS:
        seats=np.array([p['seats'] for p in cc['products'] if p['tier']==t and not p['candidate']][0],float); seats/=seats.sum()
        for b,v in enumerate(seats):
            if v>0: stages[-1][f'{t}-{b+1}']=tiers[t]*v
    positions=[]
    for j,stage in enumerate(stages):
        ypos=0.; pos={}
        for name,vals in stage.items():
            pos[name]=[]
            for k,v in enumerate(vals):
                pos[name].append(ypos); ax.add_patch(Rectangle((j-.035,ypos),.07,v,facecolor=COLORS[k],edgecolor='white',lw=.2)); ypos+=v
            ax.text(j+.06,ypos-sum(vals)/2,name,va='center',fontsize=6.5); ypos+=total*.04
        positions.append(pos)
    # Links carry the same class through every retained branch.
    links=[]
    for k,name in enumerate(['H','M','L']): links.append((0,name,'Travel',k,trips[k])); links.append((0,name,'No travel',k,pop[k]-trips[k]))
    for name,vals in stages[2].items():
        for k,v in enumerate(vals): links.append((1,'Travel',name,k,v))
    for name,vals in stages[3].items():
        for k,v in enumerate(vals): links.append((2,'Rail',name,k,v))
    for name,vals in stages[4].items():
        for k,v in enumerate(vals): links.append((3,name[0],name,k,v))
    outgoing={}; incoming={}
    for j,src,dst,k,v in links:
        sk=(j,src,k); dk=(j+1,dst,k); y0=positions[j][src][k]+outgoing.get(sk,0); y1=positions[j+1][dst][k]+incoming.get(dk,0)
        _band(ax,j+.035,j+1-.035,y0,y1,v,COLORS[k]); outgoing[sk]=outgoing.get(sk,0)+v; incoming[dk]=incoming.get(dk,0)+v
    ax.set(xlim=(-.2,4.8),ylim=(-total*.1,total*1.2)); ax.invert_yaxis(); ax.axis('off'); ax.set_title('(a) WC: participation target/reproduced 0.850/0.850; rail 0.700/0.700',loc='left')
    bx=fig.add_subplot(gs[1,0]); markers=['o','s','^']
    for j,(state,dy) in enumerate([(s,INCOMES[s]) for s in ['reference','uniform','polarized']]):
        vot=60*np.array([.035,.03,.025])/(np.array([.012,.02,.035])*np.exp(-np.array([.7,.8,.9])*dy))
        bx.scatter(vot,np.arange(3)+j*.13,label=state,marker=markers[j],s=25)
    bx.set(xscale='log',yticks=np.arange(3)+.13,yticklabels=['H','M','L'],xlabel='Value of time (CNY/h)',title='(b) Same mean log income, different dispersion'); bx.invert_yaxis(); bx.legend(fontsize=6.5)
    cx=fig.add_subplot(gs[1,1]); names=['Auto','Coach','MaaS','Van']
    for j,ci in enumerate(CIS):
        base=np.array(c[ci]['road'])[0,:,0]; km=c[ci]['road_km'][0]; high=base-km*np.array([.58*.5,.12*.7,.2*.7,.3*.7]); yy=np.arange(4)+j*.17
        for i in range(4): cx.plot([high[i],base[i]],[yy[i]]*2,c=COLORS[j],lw=1)
        cx.scatter(base,yy,c=COLORS[j],s=15,label=ci); cx.scatter(high,yy,facecolor='white',edgecolor=COLORS[j],s=15)
    cx.set(yticks=np.arange(4)+.17,yticklabels=names,xlabel='Monetary cost per trip (CNY)',title='(c) Filled: none; hollow: all-high'); cx.legend(fontsize=6.5)
    save(fig,4)

def figure06():
    a,c,refs=load(); fig,axs=plt.subplots(2,3,figsize=(6.61,4),layout='constrained')
    for row,obj in enumerate(OBJS):
        for col,ci in enumerate(CIS):
            ax=axs[row,col]; vals={p:record(refs[ci],p,obj)['objective_value']/1000 for p in ['P0','P1','P2','P3','P4']}; best=max(vals['P1'],vals['P2']); levels=[vals['P0'],best,vals['P3'],vals['P4']]
            ax.bar(0,levels[0],color='#999999'); ax.bar(1,best-levels[0],bottom=levels[0],color='#56B4E9'); ax.bar(2,levels[2]-best,bottom=best,color='#0072B2'); ax.bar(3,levels[3]-levels[2],bottom=levels[2],color='#E69F00'); ax.bar(4,levels[3],color='#333333')
            if abs(vals['P3']-best)<1e-8: ax.annotate('joint increment = 0',(2,best),xytext=(.3,.82),textcoords='axes fraction',fontsize=6.5,arrowprops=dict(arrowstyle='-',lw=.5))
            ax.set(xticks=range(5),xticklabels=['P0','Fare','Joint','K','P4'],title=f'{ci} / {obj}',ylabel='CNY thousand/day' if col==0 else ''); ax.tick_params(axis='x',labelsize=6.5)
    labels(axs); save(fig,6)

def figure07():
    a,c,refs=load(); fig,axs=plt.subplots(3,2,figsize=(6.61,7.4),height_ratios=[1,1,3.2],layout='constrained')
    for row,ci in enumerate(CIS):
        ps=[p for p in c[ci]['products'] if not p['candidate']]
        for col,obj in enumerate(OBJS):
            ax=axs[row,col]; r=record(refs[ci],'P3',obj); ph=np.array(r['phi'])[:len(ps),:,0]; active=np.array(r['N'])[:len(ps)]>0
            ax.imshow(np.where(active,ph-1,np.nan),cmap='RdBu_r',vmin=-.2,vmax=.2,aspect='auto')
            for s in range(len(ps)):
                for h in range(4):
                    ax.add_patch(Rectangle((h-.5,s-.5),1,1,fill=False,hatch='//',edgecolor='#999999',lw=.1,alpha=.5)); ax.text(h,s,f'{ph[s,h]:.2f}' if active[s,h] else '--',ha='center',va='center',fontsize=6.5)
            ax.set(xticks=range(4),xticklabels=PERIODS,yticks=range(len(ps)),yticklabels=[p['id'] for p in ps],title=f'{ci} / {obj}: all departures fixed'); ax.tick_params(length=0)
    save(fig,7)

def figure08():
    a,c,refs=load(); fig,ax=plt.subplots(figsize=(3.94,3.5),layout='constrained'); cc=c['JX']; p0=record(refs['JX'],'P0','profit'); matrix=np.full((4,4),np.nan); values={}
    for obj in OBJS:
        r=record(refs['JX'],'P3',obj)
        for w,od in enumerate(cc['ods']):
            i,j=[cc['cities'].index(x) for x in od.split('-')]; rr=(i,j) if obj=='profit' else (j,i); matrix[rr]=100*(r['rail_by_od'][w]/p0['rail_by_od'][w]-1); values[rr]=r['rail_by_od'][w]/1000
    im=ax.imshow(matrix,cmap='RdBu_r',vmin=-max(1,np.nanmax(abs(matrix))),vmax=max(1,np.nanmax(abs(matrix))))
    for (i,j),v in values.items(): ax.text(j,i,f'{v:.1f}',ha='center',va='center')
    for i,j in [(0,2),(2,0)]: ax.add_patch(Rectangle((j-.5,i-.5),1,1,fill=False,edgecolor='black',lw=2))
    ax.set(xticks=range(4),yticks=range(4),xticklabels=['GZ','JA','NC','JJ'],yticklabels=['GZ','JA','NC','JJ'],title='Upper: profit; lower: welfare\nText: rail trips (thousand/day)'); fig.colorbar(im,ax=ax,label='Rail trip change (%)',shrink=.7); save(fig,8)

def figure09():
    a,c,refs=load(); es=groups('E2'); fig=plt.figure(figsize=(6.61,7),layout='constrained'); gs=fig.add_gridspec(2,1,height_ratios=[1.6,1]); top=gs[0].subgridspec(4,5); shocks=[('uniform','none'),('polarized','none'),('reference','all_high'),('polarized','all_high')]; metrics=['Participation','Rail share','G / rail','D+K / rail','Premium / rail']
    for row,(inc,elec) in enumerate(shocks):
        for col,metric in enumerate(metrics):
            ax=fig.add_subplot(top[row,col])
            for i,ci in enumerate(CIS):
                g=next(g for g in es if g['job']['id']==f'{ci}_{inc}_{elec}'); r=record(g,'P0','profit'); base=record(refs[ci],'P0','profit')
                def calc(rr):
                    q=np.array(rr['class_trips']); rail=np.array(rr['rail_by_class']); g=np.array(rr['tier_by_class']['G']); premium=np.array(rr['premium_by_class']); return [q/rr['class_potential'],rail/q,g/rail,1-g/rail,premium/rail][col]
                diff=100*(calc(r)-calc(base))
                for k in range(3): ax.scatter(diff[k],i+(k-1)*.16,c=COLORS[k],s=10)
            ax.axvline(0,color='#777777',lw=.5); ax.set(yticks=range(3),yticklabels=CIS if col==0 else [],title=metric if row==0 else ''); ax.invert_yaxis(); ax.tick_params(labelsize=6)
            if col==0: ax.set_ylabel(['Uniform','Polarized','All-high','Combined'][row],fontsize=7)
    bottom=gs[1].subgridspec(2,3)
    for i,ci in enumerate(CIS):
        for row in range(2):
            ax=fig.add_subplot(bottom[row,i])
            for j,inc in enumerate(['reference','uniform','polarized']):
                rs=[record(next(g for g in es if g['job']['id']==f'{ci}_{inc}_{elec}'),'P0','profit') for elec in ['none','auto','am_low','am_high','all_low','all_high']]
                ax.plot(range(6),[r['eta'] if row==0 else (r['profit']+500000)/1000 for r in rs],marker=['o','s','^'][j],ms=2.5,label=inc)
            ax.axhline(.95 if row==0 else 0,color='black',lw=.6,ls='--'); ax.set(xticks=range(6),xticklabels=['0','A','AMl','AMh','Alll','Allh'] if row==1 else [],title=ci if row==0 else '',ylabel=('Retention' if row==0 else 'Margin (CNY k)') if i==0 else '')
            if row==0 and i==2: ax.legend(fontsize=6)
    fig.suptitle('Class markers: H (dark blue), M (blue), L (light blue)',fontsize=8)
    save(fig,9)

def figure10():
    a,c,refs=load(); fig,axs=plt.subplots(1,3,figsize=(6.61,2.8),layout='constrained'); cmap=ListedColormap(['#eeeeee','#cccccc','#999999','#555555','#E69F00','#222222']); code={'P0':0,'P1':1,'P2':2,'P3':3,'P4':4,'none':5}
    for ax,ci in zip(axs,CIS):
        m=np.zeros((3,6))
        for x in a['matrix']:
            if x['case_id']!=ci: continue
            i=['reference','uniform','polarized'].index(x['income']); j=['none','auto','am_low','am_high','all_low','all_high'].index(x['electric']); m[i,j]=code[x['minimum_policy']]
            ax.text(j,i,x['p0_failures'] or 'OK',ha='center',va='center',fontsize=7,color='white' if m[i,j]>=3 else 'black')
            if x['search_discrepancy']: ax.plot(j+.3,i-.3,'r.',ms=4)
        ax.imshow(m,cmap=cmap,vmin=0,vmax=5,aspect='auto'); ax.set(xticks=range(6),xticklabels=['0','A','AMl','AMh','Alll','Allh'],yticks=range(3),yticklabels=['Ref','Uniform','Polarized'],title=ci); ax.tick_params(axis='x',rotation=40)
    fig.supxlabel('Light: P0 feasible; dark: no feasible P4 found. F finance; R retention; C seats.',fontsize=7.5); save(fig,10)

def figure11():
    a,c,refs=load(); es=groups('E2'); fig=plt.figure(figsize=(6.61,5.1),layout='constrained'); gs=fig.add_gridspec(3,3,height_ratios=[1,1,1.2]); states=[(i,e) for i in ['reference','uniform','polarized'] for e in ['none','all_high']]
    for row,obj in enumerate(OBJS):
        for col,ci in enumerate(CIS):
            ax=fig.add_subplot(gs[row,col])
            for j,(inc,e) in enumerate(states):
                r=record(next(g for g in es if g['job']['id']==f'{ci}_{inc}_{e}'),'P4',obj); N=np.array(r['N']); total=N.sum(); bottom=0
                for t in TIERS:
                    mask=np.array([p['tier']==t for p in c[ci]['products']]); value=N[mask].sum()/total; ax.bar(j,value,bottom=bottom,color=TIERS[t],width=.65,hatch=None if r['feasible'] else '//'); bottom+=value
                ax.text(j,1.03,str(int(total)),ha='center',fontsize=6)
            ax.set(xticks=range(6),xticklabels=['R0','Rh','U0','Uh','P0','Ph'],ylim=(0,1.18),title=f'{ci} / {obj}',ylabel='Departure share' if col==0 else '')
    ax=fig.add_subplot(gs[2,:]); e6=groups('E6'); rows=[(ci,obj) for ci in CIS for obj in OBJS]
    for i,(ci,obj) in enumerate(rows):
        for j,inc in enumerate(['reference','uniform','polarized']):
            g=next(g for g in e6 if g['job']['id']==f'{ci}_{inc}'); p=record(g,'P3',obj); sb=record(g,'P3-sb',obj)
            if p['feasible'] and sb['feasible']: ax.scatter((sb['objective_value']-p['objective_value'])/1000,i+(j-1)*.18,marker=['o','s','^'][j],c=COLORS[j],s=25,label=inc if i==0 else None)
            else: ax.text(0,i+(j-1)*.18,'x',ha='center',va='center',color='#777777',fontsize=7)
    ax.set(yticks=range(6),yticklabels=[f'{ci} / {o}' for ci,o in rows],xlabel='Seat-relativity gain (CNY thousand/day); x = no feasible pair'); ax.invert_yaxis(); ax.legend(fontsize=7,ncols=3); save(fig,11)

def figure12():
    a,c,refs=load(); fig=plt.figure(figsize=(6.61,6.4),layout='constrained'); gs=fig.add_gridspec(4,2,height_ratios=[1,1,1,.75]); cmap=ListedColormap(['#dddddd','#E69F00','#0072B2','#333333']); codes={'inactive':0,'improvement':1,'restoration':2,'unresolved':3}
    for i,ci in enumerate(CIS):
        for j,obj in enumerate(OBJS):
            ax=fig.add_subplot(gs[i,j]); vals=[x for x in a['phase'] if x['case_id']==ci and x['objective']==obj]; m=np.zeros((7,11))
            for x in vals: m[int(round(x['electric']/1.5*6)),int(round(x['polarization']/1.7*10))]=codes[x['regime']]
            ax.imshow(m,origin='lower',extent=(-.085,1.785,-.125,1.625),cmap=cmap,vmin=0,vmax=3,aspect='auto'); ax.set(title=f'{ci} / {obj}',xlabel='Polarization scale' if i==2 else '',ylabel='Electrification scale' if j==0 else '',xticks=[0,.85,1.7],yticks=[0,.75,1.5])
            for px,py in [(0,0),(0,1),(1,0),(1,1)]: ax.scatter(px,py,s=13,facecolor='none',edgecolor='#56B4E9',linewidth=.7)
            if i==0:
                sec=ax.secondary_xaxis('top',functions=(lambda x:100*np.expm1(x*np.log(.85)),lambda y:np.log1p(np.maximum(y,-99.9)/100)/np.log(.85)))
                sec.set_xticks([0,-12,-24]); sec.set_xlabel('Low-income level change (%)',fontsize=7)
    ax=fig.add_subplot(gs[3,:]); ev=a['events']
    if not ev: ax.text(.5,.5,'No confirmed K-entry event in E2 or E3.\nEvent decomposition has no admissible comparison.',ha='center',va='center'); ax.axis('off')
    else:
        for i,e in enumerate(ev[:12]):
            if e['role']=='improvement':
                ax.barh(i,e['own_revenue']/1000,color=TIERS['K']); ax.barh(i,e['incumbent_revenue_change']/1000,color='#999999'); ax.barh(i,-e['activation_cost']/1000,left=min(0,e['incumbent_revenue_change']/1000),color='#D55E00'); ax.scatter(e['profit_change']/1000,i,c='black',s=10)
            else: ax.scatter(e['retention_change']*100,i,c='#0072B2')
        ax.set(yticks=range(min(12,len(ev))),yticklabels=[e['trigger'].replace('_',' ')[:24] for e in ev[:12]],xlabel='CNY thousand (improvement) / retention pp (restoration)')
    fig.supxlabel('Grey: inactive; orange: objective gain; blue: recovery; dark: no feasible design found.',fontsize=7); save(fig,12)

def figure13():
    a,c,refs=load(); e4=groups('E4'); eq=json.loads((ROOT/'equity_designs.json').read_text(encoding='utf-8')); fig=plt.figure(figsize=(6.61,5.6),layout='constrained'); gs=fig.add_gridspec(2,2,height_ratios=[1,1.1]); ax=fig.add_subplot(gs[0,0]); budgetax=fig.add_subplot(gs[0,1]); bx=fig.add_subplot(gs[1,:])
    for i,ci in enumerate(CIS):
        for j,obj in enumerate(OBJS):
            rs=[record(next(g for g in e4 if g['job']['id']==f'{ci}_reference_{eta}_{500000}'),'P3',obj) for eta in [.9,.925,.95,.975,1.]]; base=rs[0]['objective_value']; ax.plot([.9,.925,.95,.975,1.],[(base-r['objective_value'])/1000 if r['feasible'] else np.nan for r in rs],color=COLORS[i],ls='-' if j==0 else '--',marker='o' if j==0 else 's',ms=3,label=f'{ci} {obj[0].upper()}')
    ax.set(xlabel='Retention floor',ylabel='Objective cost (CNY thousand)',title='(a) Reference; all B curves coincide'); ax.legend(fontsize=6,ncols=2); ax.text(.02,.9,'Stressed: no feasible design\nwithin B = 0--2 million',transform=ax.transAxes,fontsize=7)
    for i,ci in enumerate(CIS):
        for policy,offset,marker in [('P3',-.12,'o'),('P4',.12,'s')]:
            rows=[b for b in a['budgets'] if b['case_id']==ci and b['policy']==policy]; vals=[b['Bstar_upper_bound']/1e6 for b in rows if b['budget_fixable_found']]; budgetax.scatter(vals,np.full(len(vals),i+offset),s=16,marker=marker,facecolor=COLORS[i] if policy=='P3' else 'white',edgecolor=COLORS[i]); failed=sum(not b['budget_fixable_found'] for b in rows); budgetax.text(1.02,i+offset,f'{failed} unresolved',transform=budgetax.get_yaxis_transform(),fontsize=6.5)
    budgetax.set(yticks=range(3),yticklabels=CIS,xlabel='Budget sufficient for saved design (CNY million)',title='(b) No financial floor; paired P3/P4'); budgetax.invert_yaxis(); budgetax.margins(x=.15)
    colors={'P0':'#bbbbbb','P1':'#888888','P2':'#666666','P3':'#0072B2','P4':'#E69F00','P3-sb':'#009E73'}
    for policy,color in colors.items():
        rows=[r for r in eq if r['policy']==policy and r['feasible']]; bx.scatter([r['dG'] for r in rows],[r['deta'] for r in rows],c=color,s=8,alpha=.45,label=policy)
    bx.axhline(0,c='black',lw=.6); bx.axvline(0,c='black',lw=.6); bx.set(xlabel='Change in worst OD-period cost ratio',ylabel='Change in vulnerable-trip retention',title='(c) Feasible saved designs; same-state P0 comparator'); bx.legend(fontsize=6.5,ncols=6)
    xl=bx.get_xlim(); yl=bx.get_ylim(); bx.add_patch(Rectangle((xl[0],yl[0]),max(0,-xl[0]),max(0,-yl[0]),facecolor='#FCE2DC',edgecolor='none',zorder=-2)); bx.set_xlim(xl); bx.set_ylim(yl)
    st=a['equity_stats']['feasible_only']; bx.text(.02,.05,f"Divergence {st['divergence_n']}/{st['n']}; rank correlation {st['spearman']:.3f}",transform=bx.transAxes,fontsize=7)
    save(fig,13)

def figure14():
    a,c,refs=load(); fig,axs=plt.subplots(1,3,figsize=(6.61,3),layout='constrained')
    for ax,ci in zip(axs,CIS):
        rows=[r for r in a['governance'] if r['case_id']==ci]
        for r in rows:
            x=np.array([r['profit_P'],r['profit_W']])/1000; y=np.array([r['surplus_P'],r['surplus_W']])/1000; ax.plot(x,y,c='#777777',lw=1); ax.scatter(x[0],y[0],s=30,c=COLORS[0]); ax.scatter(x[1],y[1],s=30,facecolor='white',edgecolor=COLORS[0])
        ax.set(title=ci,xlabel='Rail profit (CNY thousand)',ylabel='Consumer-surplus change (CNY thousand)' if ci=='HN' else '')
        if rows:
            xlim=ax.get_xlim(); ylim=ax.get_ylim(); span=max(xlim[1]-xlim[0],ylim[1]-ylim[0],10); center=np.mean(xlim)+np.mean(ylim)
            for v in np.linspace(center-span,center+span,5): ax.plot(xlim,[v-x for x in xlim],c='#dddddd',lw=.5,zorder=-1)
            ax.set_ylim(ylim)
        ax.text(.03,.94,'Filled: profit\nHollow: welfare',transform=ax.transAxes,fontsize=7,va='top')
    save(fig,14)

def main(n):
    globals()[f'figure{n:02d}']()

if __name__=='__main__':
    for n in [3,4,6,7,8,9,10,11,12,13,14]: main(n)
