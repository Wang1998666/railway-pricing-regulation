"""Figures redesigned around decision changes and feasible-domain boundaries."""
import json,math,collections
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyBboxPatch,Circle
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox,DrawingArea
from matplotlib.colors import ListedColormap
from matplotlib.collections import LineCollection
import geopandas as gpd
from PIL import Image
from model import ROOT,Model
from analyze import groups,record,pair_feasible
import figures as old

OUT=ROOT.parents[1]/'visualization'/'main_figures'; COLORS=old.COLORS; TIERS=old.TIERS; CIS=old.CIS; OBJS=old.OBJS
plt.rcParams.update({'font.size':8.5,'axes.titlesize':9,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,'axes.spines.right':False})

def load(): return old.load()
def save(fig,n): old.save(fig,n)
def icon(kind,color):
    a=DrawingArea(26,20,0,0)
    if kind=='rail':
        a.add_artist(FancyBboxPatch((6,5),14,14,boxstyle='round,pad=0,rounding_size=3',facecolor='white',edgecolor=color,lw=1.2))
        a.add_artist(Rectangle((8,11),10,5,facecolor=color,edgecolor='none'))
        for x in [9,17]: a.add_artist(Circle((x,7),1,facecolor=color))
        a.add_artist(Line2D([9,5],[5,0],c=color,lw=1)); a.add_artist(Line2D([17,21],[5,0],c=color,lw=1))
    else:
        a.add_artist(FancyBboxPatch((3,5),20,8,boxstyle='round,pad=0,rounding_size=2',facecolor='white',edgecolor=color,lw=1.2))
        a.add_artist(Rectangle((8,11),11,5,facecolor='white',edgecolor=color,lw=1))
        for x in [8,19]: a.add_artist(Circle((x,4),2,facecolor=color))
    return a

def figure03():
    A,C,refs=load(); geo=json.loads((ROOT/'maps'/'reference_geometry.json').read_text(encoding='utf-8'))
    fig=plt.figure(figsize=(6.61,4.65),layout='constrained'); gs=fig.add_gridspec(2,3,height_ratios=[3.7,1.0]); names={'HN':'Hangzhou--Nanjing','WC':'Wuhan--Changsha','JX':'Jiangxi corridor'}
    for j,ci in enumerate(CIS):
        ax=fig.add_subplot(gs[0,j]); d=geo[ci]; w,e,s,n=d['extent']; image=np.array(Image.open(ROOT/'maps'/d['basemap']))
        ax.imshow(image,extent=(w,e,s,n),origin='upper',aspect='auto',alpha=.95,zorder=0)
        railfile='zip://'+str((ROOT/'maps'/'ne_10m_railroads.zip').resolve())
        rail=gpd.read_file(railfile,bbox=(w,s,e,n)); lines=[]
        for shape in rail.geometry:
            for line in (shape.geoms if hasattr(shape,'geoms') else [shape]): lines.append(np.array(line.coords))
        if ci=='JX' and (ROOT/'maps'/'JX_rail_osm.json').exists():
            osm=json.loads((ROOT/'maps'/'JX_rail_osm.json').read_text(encoding='utf-8'))
            lines += [np.array([[p['lon'],p['lat']] for p in el['geometry']]) for el in osm['elements'] if 'geometry' in el and any(name in el.get('tags',{}).get('name','') for name in ['京九','昌赣','昌九'])]
        ax.add_collection(LineCollection(lines,colors='#346482',linewidths=.60,linestyles='--',alpha=.8,zorder=2))
        for line in d['road_routes']:
            line=np.array(line); ax.plot(line[:,0],line[:,1],color='white',lw=2.8,zorder=3); ax.plot(line[:,0],line[:,1],color='#B44334',lw=1.55,zorder=4)
        for k,(city,xy) in enumerate(d['cities'].items()):
            ax.scatter(*xy,s=22,c='#17324D',edgecolor='white',linewidth=.7,zorder=5)
            offset=(5,8) if k%2==0 else (-5,-10); align='left' if k%2==0 else 'right'
            if ci=='HN' and city=='Hangzhou': offset=(-5,8); align='right'
            if ci=='HN' and city=='Nanjing': offset=(5,-10); align='left'
            if ci=='WC' and city=='Changsha': offset=(5,7); align='left'
            ax.annotate(city,xy,xytext=offset,textcoords='offset points',fontsize=7.6,ha=align,va='center',bbox=dict(boxstyle='round,pad=.15',fc='white',ec='none',alpha=.9),zorder=6)
        ax.set(xlim=(w,e),ylim=(s,n),title=f'({chr(97+j)}) {names[ci]}',xlabel='Longitude',ylabel='Latitude' if j==0 else '')
        ax.tick_params(labelsize=7); ax.locator_params(axis='x',nbins=3); ax.locator_params(axis='y',nbins=5)
        ax.annotate('N',xy=(.92,.90),xytext=(.92,.80),xycoords='axes fraction',textcoords='axes fraction',ha='center',fontsize=8,arrowprops=dict(arrowstyle='-|>',lw=.8,color='#17324D'))
        # Mode icons and supply labels sit on the geographic panels.
        ax.add_patch(FancyBboxPatch((.025,.865),.75,.12,boxstyle='round,pad=.015',transform=ax.transAxes,fc='white',ec='#b9c9d3',lw=.5,alpha=.95,zorder=7))
        ax.add_artist(AnnotationBbox(icon('rail','#17324D'),(.08,.955),xycoords='axes fraction',frameon=False,box_alignment=(.5,.5),zorder=8))
        ax.add_artist(AnnotationBbox(icon('road','#B44334'),(.08,.895),xycoords='axes fraction',frameon=False,box_alignment=(.5,.5),zorder=8))
        c=C[ci]; m=Model(c); N=m.N0; counts=[int(N[m.tier==t].sum()) for t in TIERS]
        ax.text(.18,.955,f'G {counts[0]}  D {counts[1]}  K {counts[2]}',transform=ax.transAxes,fontsize=7.1,va='center',zorder=8,color='#17324D')
        ax.text(.18,.895,f'Road {max(c["road_km"]):.1f} km',transform=ax.transAxes,fontsize=7.1,va='center',zorder=8,color='#B44334')
        bx=fig.add_subplot(gs[1,j]); bx.axis('off'); seats=sum(sum(p['N0'])*sum(p['seats']) for p in c['products']); flexible=int((m.N0-m.Nmin).sum()); protected=int(m.Nmin.sum())
        bx.text(0,.95,f'{len(c["cities"])} nodes / {len(c["ods"])} forward ODs',fontsize=8.2,fontweight='bold',va='top')
        bx.text(0,.66,f'{seats/1000:.1f}k modeled seats/day',fontsize=8.0)
        bx.text(0,.39,f'{flexible} adjustable / {protected} protected trains',fontsize=7.4)
        total=flexible+protected; bx.barh(.13,protected/total,left=0,height=.12,color='#c4d1db',hatch='///'); bx.barh(.13,flexible/total,left=protected/total,height=.12,color='#007F86'); bx.set(xlim=(0,1),ylim=(0,1))
    fig.legend(handles=[Line2D([],[],c='#B44334',lw=1.6,label='Amap road trajectory'),Line2D([],[],c='#346482',lw=1,ls='--',label='Mapped railway network')],loc='outside lower center',ncols=2,frameon=False,fontsize=8,borderaxespad=1.6)
    fig.text(.01,0,'Basemap © OpenStreetMap contributors © CARTO; railway context: Natural Earth / OSM.',fontsize=6.2)
    save(fig,3)

def figure06():
    A,C,refs=load(); fig,axs=plt.subplots(2,3,figsize=(6.61,4.2),layout='constrained')
    palette=['#B8C4CE','#4C9B9B','#17324D','#D59A36']
    for i,obj in enumerate(OBJS):
        for j,ci in enumerate(CIS):
            ax=axs[i,j]; p0=record(refs[ci],'P0',obj)['objective_value']; vals=[(record(refs[ci],p,obj)['objective_value']-p0)/1000 for p in ['P1','P2','P3','P4']]
            ax.bar(range(4),vals,color=palette,width=.65)
            for k,v in enumerate(vals): ax.annotate(f'{v:.1f}',(k,v),xytext=(0,4),textcoords='offset points',ha='center',fontsize=7.5)
            incr=vals[2]-max(vals[:2]); ax.text(.04,.94,f'Joint increment: {incr:.1f}k',transform=ax.transAxes,va='top',fontsize=7.2)
            ax.set(xticks=range(4),xticklabels=['Fares','Frequency','Joint','+ K'],title=f'{ci} / {obj}',ylabel='Gain over P0 (CNY thousand/day)' if j==0 else '',ylim=(0,max(vals)*1.32+1)); ax.tick_params(axis='x',rotation=25)
    save(fig,6)

def figure07():
    A,C,refs=load(); selections={}; heights=[]
    for ci in CIS:
        c=C[ci]; N0=np.array([p['N0'] for p in c['products']]); change=np.zeros(len(N0),bool)
        for obj in OBJS:
            r=record(refs[ci],'P3',obj); change |= np.any(abs(np.array(r['N'])-N0)>0,axis=1)|np.any((abs(np.array(r['phi'])[:,:,0]-1)>.001)&(np.array(r['N'])>0),axis=1)
        idx=np.flatnonzero(change); selections[ci]=idx; heights.append(max(2,len(idx)))
    fig,axs=plt.subplots(3,2,figsize=(6.61,6.2),height_ratios=heights,layout='constrained'); maxchange=max(abs(np.array(record(refs[ci],'P3',obj)['N'])-np.array([p['N0'] for p in C[ci]['products']])).max() for ci in CIS for obj in OBJS)
    for row,ci in enumerate(CIS):
        idx=selections[ci]; N0=np.array([p['N0'] for p in C[ci]['products']]);
        for col,obj in enumerate(OBJS):
            ax=axs[row,col]; r=record(refs[ci],'P3',obj); N=np.array(r['N']); ph=np.array(r['phi'])[:,:,0]; delta=(N-N0)[idx]
            im=ax.imshow(delta,cmap='RdBu_r',vmin=-maxchange,vmax=maxchange,aspect='auto')
            for ii,s in enumerate(idx):
                for h in range(4):
                    text=f'{int(delta[ii,h]):+d}\n{ph[s,h]:.2f}' if N[s,h]>0 else f'{int(delta[ii,h]):+d}\n--'
                    ax.text(h,ii,text,ha='center',va='center',fontsize=7.2,color='white' if abs(delta[ii,h])>.65*maxchange else '#17324D')
            ax.set(xticks=range(4),xticklabels=['AM','Day','PM','Night'],yticks=range(len(idx)),yticklabels=[C[ci]['products'][s]['id'] for s in idx],title=f'{ci} / {obj}'); ax.tick_params(length=0)
    fig.colorbar(im,ax=axs.ravel().tolist(),label='Change in daily departures',shrink=.7,pad=.02)
    save(fig,7)

def figure10():
    A,C,refs=load(); fig,axs=plt.subplots(2,3,figsize=(6.61,4.1),layout='constrained'); by={(x['case_id'],x['income'],x['electric'],x['policy']):x for x in A['budgets']}; es=['none','auto','am_low','am_high','all_low','all_high']; im=None
    for i,p in enumerate(['P3','P4']):
        for j,ci in enumerate(CIS):
            ax=axs[i,j]; mat=np.full((3,6),np.nan); text={}
            for k,inc in enumerate(['reference','uniform','polarized']):
                for l,e in enumerate(es):
                    b=by.get((ci,inc,e,p))
                    if inc=='reference' and e=='none': mat[k,l]=0.; text[k,l]='0'
                    elif b and b['budget_fixable_found']: mat[k,l]=b['Bstar_upper_bound']/1e6; text[k,l]=f'{mat[k,l]:.1f}'
                    else: text[k,l]='?'
            im=ax.imshow(mat,cmap='YlGnBu',vmin=0,vmax=14,aspect='auto'); ax.set_facecolor('#e6e8eb')
            for (k,l),t in text.items(): ax.text(l,k,t,ha='center',va='center',fontsize=7.5,color='white' if mat[k,l]>9 else '#17324D')
            ax.set(xticks=range(6),xticklabels=['0','A','AMl','AMh','Alll','Allh'],yticks=range(3),yticklabels=['Reference','Uniform','Polarized'] if j==0 else [],title=f'{ci} / {p}'); ax.tick_params(axis='x',rotation=35)
    fig.colorbar(im,ax=axs.ravel().tolist(),shrink=.8,label='Sufficient daily loss budget (CNY million)'); save(fig,10)

def figure11():
    A,C,refs=load(); es=groups('E3'); fig=plt.figure(figsize=(6.61,4.7),layout='constrained'); gs=fig.add_gridspec(2,3,height_ratios=[1.4,1.2])
    for j,ci in enumerate(CIS):
        ax=fig.add_subplot(gs[0,j]); cand=np.array([p['candidate'] for p in C[ci]['products']]); costs=[.1,.25,.5,.75,1.]
        for obj,marker,ls in [('profit','o','-'),('welfare','s','--')]:
            yy=[]
            for factor in costs:
                label=f'{ci}_baseline' if factor==1 else f'{ci}_k_cost_{factor}'
                g=next(g for g in es if g['job']['id']==label); r=record(g,'P4',obj); yy.append(np.array(r['N'])[cand].sum() if r['feasible'] else np.nan)
            ax.plot(costs,yy,color='#17324D' if obj=='profit' else '#D59A36',marker=marker,ls=ls,ms=4,label=obj)
        ax.set(title=ci,xlabel='K operating-cost multiplier',ylabel='Additional K departures/day' if j==0 else '',xlim=(0,1.03)); ax.legend(fontsize=7,frameon=False)
    ax=fig.add_subplot(gs[1,:]); rows=[(ci,obj) for ci in CIS for obj in OBJS]; e6=groups('E6')
    for i,(ci,obj) in enumerate(rows):
        g=next(g for g in e6 if g['job']['id']==f'{ci}_reference'); p=record(g,'P3',obj); s=record(g,'P3-sb',obj); base=record(refs[ci],'P0',obj)['objective_value']; x1=(p['objective_value']-base)/1000; x2=(s['objective_value']-base)/1000
        ax.plot([x1,x2],[i,i],color='#bbc7cf',lw=3); ax.scatter(x1,i,facecolor='white',edgecolor='#17324D',s=30,label='Common seat relativities' if i==0 else None); ax.scatter(x2,i,c='#007F86',s=25,label='Seat-specific multipliers' if i==0 else None)
    ax.set(yticks=range(6),yticklabels=[f'{ci} / {obj}' for ci,obj in rows],xlabel='Reference objective gain over P0 (CNY thousand/day)'); ax.invert_yaxis(); ax.legend(loc='upper center',bbox_to_anchor=(.5,-.25),ncols=2,frameon=False,fontsize=7.5); save(fig,11)

def figure12():
    A,C,refs=load(); es=groups('E10'); fig=plt.figure(figsize=(6.61,6.5),layout='constrained'); gs=fig.add_gridspec(4,2,height_ratios=[1,1,1,1.5]); cols=['#e4e8eb','#D59A36','#3D91B4','#33404c']; cmap=ListedColormap(cols); costs=[.1,.25,.4,.55,.7,.85,1.]; elecs=[0,.02,.04,.06,.08,.12,.20]
    for i,ci in enumerate(CIS):
        for j,obj in enumerate(OBJS):
            ax=fig.add_subplot(gs[i,j]); mat=np.zeros((7,7)); gains=np.full((7,7),np.nan)
            for a in range(7):
                for b in range(7):
                    g=next(g for g in es if g['job']['id']==f'{ci}_{a:02d}_{b:02d}'); f3=pair_feasible(g,'P3'); f4=pair_feasible(g,'P4'); p=record(g,'P3',obj); r=record(g,'P4',obj)
                    gain=r['objective_value']-p['objective_value']; mat[b,a]=3 if not f4 else 2 if not f3 else 1 if gain>1e-4*max(1,abs(p['objective_value'])) else 0; gains[b,a]=gain/1000 if f3 and f4 else np.nan
            ax.imshow(mat,origin='lower',cmap=cmap,vmin=0,vmax=3,aspect='auto')
            ax.set(xticks=[0,3,6],xticklabels=['.10','.55','1.00'],yticks=[0,3,6],yticklabels=['0','.06','.20'],title=f'{ci} / {obj}',xlabel='K cost multiplier' if i==2 else '',ylabel='Road-saving intensity' if j==0 else '')
            # Only actual positive entry gains are labeled; no fabricated contours.
            for b,a in [(0,0),(0,3),(3,0),(6,0)]:
                if mat[b,a]==1: ax.text(a,b,f'{gains[b,a]:.0f}',ha='center',va='center',fontsize=6.5,color='#17324D')
    ax=fig.add_subplot(gs[3,:]); events=A['events']; selected=sorted([e for e in events if e['role']=='improvement'],key=lambda e:abs(e['profit_change']),reverse=True)[:8]
    for i,e in enumerate(selected):
        values=[e['own_revenue']/1000,e['incumbent_revenue_change']/1000,-e['activation_cost']/1000,-e['incumbent_cost_change']/1000]; neg=0; pos=0
        for v,col in zip(values,['#D59A36','#9faeb9','#B44334','#007F86']):
            ax.barh(i,v,left=pos if v>=0 else neg,color=col,height=.6); pos+=max(0,v); neg+=min(0,v)
        ax.scatter(e['profit_change']/1000,i,c='#17324D',s=13,zorder=5)
    ax.axvline(0,c='#666666',lw=.6); ax.set(yticks=range(len(selected)),yticklabels=[e['trigger'].replace('_',' ')+' '+e['objective'][0].upper() for e in selected],xlabel='Entry profit accounting (CNY thousand/day)'); ax.invert_yaxis()
    ax.legend(handles=[Rectangle((0,0),1,1,color=col,label=lab) for col,lab in zip(['#D59A36','#9faeb9','#B44334','#007F86'],['New K revenue','Incumbent revenue change','New K cost (negative)','Incumbent cost saving'])],loc='upper center',bbox_to_anchor=(.5,-.28),ncols=2,frameon=False,fontsize=6.7)
    fig.legend(handles=[Rectangle((0,0),1,1,color=col,label=lab) for col,lab in zip(cols,['K inactive','Objective gain','Feasibility recovery','Unresolved'])],loc='outside lower center',ncols=4,frameon=False,fontsize=7.0)
    save(fig,12)

def figure13():
    A,C,refs=load(); es=groups('E9'); fig=plt.figure(figsize=(6.61,5.1),layout='constrained'); gs=fig.add_gridspec(2,2,height_ratios=[1,1.2])
    for j,inc in enumerate(['reference']):
        ax=fig.add_subplot(gs[0,j])
        for k,ci in enumerate(CIS):
            cells=sorted([g for g in es if g['job']['case']==ci and g['job']['income']==inc],key=lambda g:g['job']['spec']['eta'])
            for obj,ls,marker in [('profit','-','o'),('welfare','--','s')]:
                rr=[record(g,'P3',obj) for g in cells]; base=next((r['objective_value'] for r in rr if r['feasible']),None)
                yy=[(base-r['objective_value'])/1000 if base is not None and r['feasible'] else np.nan for r in rr]; xx=[g['job']['spec']['eta'] for g in cells]
                ax.plot(xx,yy,c=COLORS[k],ls=ls,marker=marker,ms=3,label=f'{ci} {obj[0].upper()}')
                bad=[x for x,r in zip(xx,rr) if not r['feasible']]
                if bad: ax.scatter(bad,np.full(len(bad),-.03),marker='x',c=COLORS[k],s=15,transform=ax.get_xaxis_transform(),clip_on=False)
        ax.set(title='(a) Reference: threshold detail' if j==0 else '(b) Quarter-polarized income',xlabel='Vulnerable-trip retention floor',ylabel='Objective sacrifice (CNY thousand)' if j==0 else ''); ax.tick_params(axis='x',rotation=30)
        if j==0: ax.legend(ncols=2,fontsize=6.6,frameon=False)
    ax=fig.add_subplot(gs[0,1]); floors=[.90,.92,.94,.95,.96,.98,1.]; mat=np.zeros((6,7))
    for i,(ci,pol) in enumerate(( (ci,pol) for ci in CIS for pol in ['P3','P4'] )):
        for j,floor in enumerate(floors):
            g=next(g for g in es if g['job']['case']==ci and g['job']['income']=='mild' and abs(g['job']['spec']['eta']-floor)<1e-8)
            mat[i,j]=pair_feasible(g,pol)
    ax.imshow(mat,cmap=ListedColormap(['#d4dbe1','#007F86']),vmin=0,vmax=1,aspect='auto')
    for i in range(6):
        for j in range(7): ax.text(j,i,'Y' if mat[i,j] else '?',ha='center',va='center',fontsize=7,color='white' if mat[i,j] else '#17324D')
    ax.set(title='(b) Quarter-polarized: feasibility boundary',xticks=range(7),xticklabels=[f'{v:.2f}' for v in floors],yticks=range(6),yticklabels=[f'{ci} {pol}' for ci in CIS for pol in ['P3','P4']],xlabel='Vulnerable-trip retention floor'); ax.tick_params(axis='x',rotation=30)
    ax=fig.add_subplot(gs[1,:]); eq=json.loads((ROOT/'equity_designs.json').read_text(encoding='utf-8')); feasible=[r for r in eq if r['feasible']]; origin=sum(abs(r['dG'])<1e-7 and abs(r['deta'])<1e-7 for r in feasible); grouped=collections.Counter((r['policy'],round(r['dG'],7),round(r['deta'],7)) for r in feasible if abs(r['dG'])>1e-7 or abs(r['deta'])>1e-7)
    palette={'P0':'#cccccc','P1':'#9faeb9','P2':'#007F86','P3':'#17324D','P4':'#D59A36','P3-sb':'#7257A5'}
    for p,color in palette.items():
        rows=[(x,y,n) for (pol,x,y),n in grouped.items() if pol==p]
        ax.scatter([x for x,y,n in rows],[100*y for x,y,n in rows],s=[12+4*np.sqrt(n) for x,y,n in rows],facecolors='none' if p=='P4' else color,edgecolors=color,alpha=.7,linewidths=.8 if p=='P4' else .2,marker='^' if p=='P3-sb' else 'o',label=p)
    ax.axhline(0,c='#555555',lw=.6); ax.axvline(0,c='#555555',lw=.6); ax.set(title=f'(c) Nonzero equity responses; {origin} coincident reference points counted at the origin',xlabel='Change in worst-case cost ratio',ylabel='Retention change (percentage points)'); ax.legend(ncols=6,loc='upper center',bbox_to_anchor=(.5,-.21),frameon=False,fontsize=7)
    save(fig,13)

def figure14():
    A,C,refs=load(); fig,axs=plt.subplots(1,3,figsize=(6.61,3.1),layout='constrained'); color={'reference':'#17324D','uniform':'#D59A36','polarized':'#B44334'}
    for ax,ci in zip(axs,CIS):
        rows=[r for r in A['governance'] if r['case_id']==ci]
        for r in rows:
            e=r['electric']; marker='o' if e=='none' else 's' if e=='auto' else '^' if e.startswith('am') else 'D'; ax.scatter(r['profit_gap']/1000,r['welfare_gap']/1000,s=25,marker=marker,c=color[r['income']],alpha=.8,edgecolor='white',linewidth=.3)
        ax.set(title=ci,xlabel='Profit compensation (CNY thousand/day)',ylabel='Welfare gain (CNY thousand/day)' if ci=='HN' else ''); ax.margins(.15)
        zero=sum(abs(r['profit_gap'])<1e-5 and abs(r['welfare_gap'])<1e-5 for r in rows)
        if zero: ax.annotate(f'{zero} coincident states',(0,0),xytext=(5,12),textcoords='offset points',fontsize=7)
        if rows and max(r['welfare_gap'] for r in rows)>1e-5:
            best=max(rows,key=lambda r:r['welfare_gap']); ax.annotate(best['income'].replace('reference','ref.')+' / '+best['electric'].replace('all_high','all-high').replace('all_low','all-low'),(best['profit_gap']/1000,best['welfare_gap']/1000),xytext=(-5,8),textcoords='offset points',ha='right',fontsize=6.5)
        elif rows:
            ax.set(xticks=[0],yticks=[0],xlim=(-1,1),ylim=(-1,1)); ax.text(.5,.75,'Commercial and welfare\ndesigns coincide',transform=ax.transAxes,ha='center',fontsize=8)
    handles=[Line2D([],[],marker='o',ls='',c=color[i],label=i) for i in color]+[Line2D([],[],marker=m,ls='',c='#888888',label=t) for m,t in [('o','no EV'),('s','auto'),('^','auto + MaaS/van'),('D','all road')]]
    fig.legend(handles=handles,loc='outside lower center',ncols=4,frameon=False,fontsize=7.4)
    save(fig,14)

if __name__=='__main__':
    import sys
    for n in (list(map(int,sys.argv[1:])) if len(sys.argv)>1 else [3,6,7,10,11,12,13,14]): globals()[f'figure{n:02d}']()
