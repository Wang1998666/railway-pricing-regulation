"""Message-specific vector research figures; original Fig 3/4a preserved."""
import json,itertools
from functools import lru_cache
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Arc,Rectangle
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap,Normalize,LogNorm
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import NullFormatter,NullLocator
import fitz
from model import ROOT,Model,INCOMES,dump
from analyze import groups as rawgroups,record,pair_feasible

P=ROOT.parent;OUT=ROOT.parents[1]/'visualization'/'main_figures';CIS=['HN','WC','JX'];CC={'HN':'#7B3294','WC':'#008579','JX':'#C18A00'};IC={'reference':'#626B73','uniform':'#0072B2','polarized':'#D55E00'};PART=['#0072B2','#009E73','#CC79A7','#E69F00'];COL={'profit':'#263C4A','U':'#D55E00','welfare':'#7B3294'}
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':8.5,'axes.titlesize':9,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'savefig.facecolor':'white'})
@lru_cache(None)
def groups(exp):return rawgroups(exp)
C={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in CIS};REF={ci:next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none') for ci in CIS};A=json.loads((ROOT/'review_analysis.json').read_text(encoding='utf-8'));D=json.loads((ROOT/'round3_analysis.json').read_text(encoding='utf-8'))
def save(fig,name):
    from matplotlib.text import Text
    for artist in fig.findobj(Text):
        if artist.get_fontsize()<8:artist.set_fontsize(8)
    fig.savefig(OUT/f'round3_{name}.pdf',bbox_inches='tight');fig.savefig(OUT/f'round3_{name}.png',dpi=190,bbox_inches='tight');plt.close(fig)
def e2(ci,inc,x):return next(g for g in groups('E2') if g['job']['case']==ci and g['job']['income']==inc and not g['job']['spec'].get('road_contrast') and abs(g['job']['spec']['electric_scale']-x)<1e-8)
def endlabels(ax,x,ys,labels,colors):
    lo,hi=ax.get_ylim();gap=(hi-lo)*.07;placed=[]
    for idx in np.argsort(ys):
        y=max(ys[idx],placed[-1]+gap if placed else lo+gap);placed.append(y);ax.annotate(labels[idx],(x,ys[idx]),xytext=(x+.045,y),textcoords='data',color=colors[idx],fontsize=7.5,va='center',arrowprops={'arrowstyle':'-','lw':.5,'color':colors[idx]})
    ax.set_xlim(right=x+.21)

def calibration():
    fig,axs=plt.subplots(1,2,figsize=(6.72,3.3),gridspec_kw={'width_ratios':[.85,1.15]},layout='constrained')
    for j,inc in enumerate(['reference','uniform','polarized']):
        v=60*np.array([.035,.03,.025])/(np.array([.012,.02,.035])*np.exp(-np.array([.7,.8,.9])*INCOMES[inc]));yy=np.arange(3)+(j-1)*.23
        axs[0].scatter(v,yy,c=IC[inc],marker=['o','s','^'][j],s=20)
        for x,y in zip(v,yy):axs[0].annotate(f'{inc[:3].capitalize()} {x:.0f}',(x,y),xytext=(5,0),textcoords='offset points',va='center',fontsize=7,color=IC[inc])
    axs[0].set(xscale='log',xlim=(25,360),yticks=range(3),yticklabels=['H','M','L'],ylim=(2.45,-.45),xlabel='Value of time (CNY/h)',title='(b) Income changes VOT');axs[0].set_xticks([40,100,200],labels=['40','100','200']);axs[0].xaxis.set_minor_formatter(NullFormatter())
    labels=[]
    for i,mode in enumerate(['Auto','Coach','MaaS','Van']):
        for j,ci in enumerate(CIS):
            m=Model(C[ci]);w=int(np.argmax(m.c['road_km']));base=m.road[w,i,0];new=base-m.c['road_km'][w]*[.145,.084,.14,.21][i];y=3*i+j;labels.append(mode+' / '+ci);axs[1].plot([new,base],[y,y],c=CC[ci],lw=1);axs[1].scatter([new,base],[y,y],c=['white',CC[ci]],edgecolor=CC[ci],s=17,zorder=3)
            axs[1].annotate(f'{new:.0f}',(new,y),xytext=(-5,0),textcoords='offset points',ha='right',va='center',fontsize=8,color=CC[ci]);axs[1].annotate(f'{base:.0f}',(base,y),xytext=(5,0),textcoords='offset points',ha='left',va='center',fontsize=8,color=CC[ci])
    axs[1].set(yticks=range(12),yticklabels=labels,ylim=(11.7,-.8),xlim=(-180,1400),xlabel='Cost per traveler (CNY)',title='(c) Longest OD: hollow x=1 / filled x=0');axs[1].tick_params(axis='y',labelsize=7)
    save(fig,'calibration_bottom');top=fitz.open(OUT/'round3_fig04a_preserved.pdf');bot=fitz.open(OUT/'round3_calibration_bottom.pdf');out=fitz.open();w=top[0].rect.width;bh=bot[0].rect.height*w/bot[0].rect.width;page=out.new_page(width=w,height=top[0].rect.height+8+bh);page.show_pdf_page(fitz.Rect(0,0,w,220),top,0);page.show_pdf_page(fitz.Rect(0,228,w,228+bh),bot,0);out.save(OUT/'round3_calibration.pdf');page.get_pixmap(matrix=fitz.Matrix(2,2)).save(OUT/'round3_calibration.png');old=fitz.open(P/'archive/before_round3_20261015/fig/case_fig04.pdf');a=old[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(0,0,w,220),alpha=False);b=page.get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(0,0,w,220),alpha=False);assert a.samples==b.samples

def elasticity():
    E=json.loads((ROOT/'elasticities_round2.json').read_text(encoding='utf-8'));fig,ax=plt.subplots(figsize=(7.48,3.5),layout='constrained');ax.axvspan(-1.21,-.67,color='#d9d9d9',alpha=.55)
    for i,e in enumerate(E):
        for k,cl in enumerate(['H','M','L']):
            y=3*i+k;own=[p['own_by_class'][k] for p in e['products']];ax.plot([min(own),max(own)],[y,y],color=CC[e['case_id']],lw=1.2);ax.scatter([e['own_GD_by_class'][k],e['pooled_GD_K_fixed'][k],e['all_rail_fares'][k]],[y]*3,c=CC[e['case_id']],s=[25,24,21],marker='o');ax.scatter(e['pooled_GD_K_fixed'][k],y,c='white',edgecolor=CC[e['case_id']],marker='^',s=28,zorder=4);ax.scatter(e['all_rail_fares'][k],y,c='white',edgecolor=CC[e['case_id']],marker='s',s=24,zorder=4)
    ax.set(yticks=range(9),yticklabels=[ci+' / '+cl for ci in CIS for cl in ['H','M','L']],ylim=(8.7,-.7),xlabel='Log quantity response to log fare',title='Own-product calibration leaves pooled rail demand much less elastic');ax.axvline(0,c='#777',lw=.6)
    for y in [2.5,5.5]:ax.axhline(y,c='#ddd',lw=.6)
    fig.legend(handles=[Line2D([],[],marker='o',ls='-',color='#333',label='Own G/D: weighted dot / product range'),Line2D([],[],marker='^',ls='',mfc='white',color='#333',label='Pooled G/D, K fixed'),Line2D([],[],marker='s',ls='',mfc='white',color='#333',label='All-rail fares'),Rectangle((0,0),1,1,fc='#d9d9d9',label='Train-OD reference range')],loc='outside lower center',ncols=2,frameon=False,fontsize=7.5);save(fig,'elasticity')

def waterfall(ax,values,labels,totals,colors):
    current=0.;ends=[0.];last_offset=3
    for i,v in enumerate(values):
        if i in totals:
            height=current if v is None else v;ax.bar(i,height,color='#263C4A',width=.7);current=height;end=height
        else:ax.bar(i,v,bottom=current,color=colors[i%len(colors)],width=.7);current+=v;end=current
        offset=14 if i and abs(end-ends[-1])<.08*max(abs(end),1) and last_offset==3 else 3
        ax.annotate(f'{end:.0f}' if i in totals else f'{v:+.0f}',(i,end),xytext=(0,offset if end>=0 else -10),textcoords='offset points',ha='center',fontsize=7);last_offset=offset
        ends.append(current)
        if i<len(values)-1:ax.plot([i+.35,i+.65],[current,current],c='#888',lw=.6)
    ax.set_xticks(range(len(labels)),labels,rotation=35,ha='right');ax.axhline(0,c='#777',lw=.6)
    lo,hi=min(ends),max(ends);span=max(hi-lo,1);ax.set_ylim(0 if lo>=0 else lo-.12*span,hi+.23*span)
def attribution():
    fig=plt.figure(figsize=(7.48,5.5),layout='constrained');gs=fig.add_gridspec(3,3,height_ratios=[1.1,.65,1.1])
    for j,ci in enumerate(CIS):
        for row,obj in [(0,'profit'),(2,'welfare')]:
            ax=fig.add_subplot(gs[row,j]);g=REF[ci];z={p:record(g,p,obj)['objective_value']/1000 for p in ['P0','P1','P2','P3','P4']};f=z['P1']-z['P0'];n=z['P2']-z['P0'];inter=z['P3']-z['P1']-z['P2']+z['P0'];waterfall(ax,[z['P0'],f,n,inter,None,z['P4']-z['P3'],None],['P0','Fare','Freq.','Interact.','P3','K','P4'],{0,4,6},['#263C4A',PART[0],PART[1],PART[2],'#263C4A',PART[3]]);ax.set_title(ci+' / '+obj,color=CC[ci]);ax.set_ylabel('CNY thousand/day' if j==0 else '')
        ax=fig.add_subplot(gs[1,j]);r=record(REF[ci],'P3','profit');b=record(REF[ci],'P0','profit');vals=[(r['profit']-b['profit'])/1000,r['consumer_surplus_change']/1000,r['welfare']/1000]
        for i,(v,key) in enumerate(zip(vals,['profit','U','welfare'])):ax.barh(i,v,color=COL[key],height=.55);ax.text(v,i,f' {v:+.0f}',va='center',ha='left' if v>=0 else 'right',fontsize=7)
        ax.set(yticks=range(3),yticklabels=[r'$\Delta\Pi$',r'$\Delta U$',r'$\Delta W$']);ax.axvline(0,c='#777',lw=.6);ax.margins(x=.28);ax.invert_yaxis()
    save(fig,'attribution')

def fares_headroom():
    fig=plt.figure(figsize=(7.48,6.5),layout='constrained');gs=fig.add_gridspec(3,2,height_ratios=[1,1,1.3],width_ratios=[1,1.1]);loc={'HN':gs[0,0],'WC':gs[1,0],'JX':gs[:,1]}
    for ci in CIS:
        ax=fig.add_subplot(loc[ci]);m=Model(C[ci]);rs=[record(REF[ci],'P3',o) for o in ['profit','welfare']];coords=[(s,h) for s in np.flatnonzero(m.adjustable) for h in range(4) if any(r['N'][s][h]>0 for r in rs)]
        ax.axvspan(1.15,1.20,color='#F8E7D7');ax.axvline(1.2,c='#D55E00',lw=.8,ls='--')
        for y,(s,h) in enumerate(coords):
            for i,r in enumerate(rs):
                if r['N'][s][h]>0:ax.scatter(r['phi'][s][h][0],y+(-.09 if i==0 else .09),marker='o' if i==0 else 's',facecolor=CC[ci] if i==0 else 'white',edgecolor=CC[ci],s=22)
            ax.text(1.24,y,'/'.join(f'{int(r["N"][s][h]-m.N0[s,h]):+d}' for r in rs),va='center',fontsize=6.8)
        ax.set(yticks=range(len(coords)),yticklabels=[m.c['products'][s]['id']+'-'+['AM','Day','PM','Night'][h] for s,h in coords],ylim=(len(coords)-.4,-.7),xlim=(.78,1.36),xticks=[.8,1,1.2],xlabel='Fare multiplier',title=ci+'; right: departure change P/W');ax.tick_params(axis='y',labelsize=7)
    ax=fig.add_subplot(gs[2,0]);rr=A['headroom']
    for ci in CIS:
        den=Model(C[ci]).N0.sum()
        for var,ls in [(.5,':'),(.7,'-'),(.9,'--')]:
            z=sorted([r for r in rr if r['case_id']==ci and r['objective']=='profit' and r['spec']['lambda']==.95 and r['spec']['variable_share']==var],key=lambda r:r['spec']['ref_load']);ax.plot([r['spec']['ref_load'] for r in z],[r['gain']/den/1000 for r in z],c=CC[ci],ls=ls,lw=1.5 if var==.7 else .8,marker='o',ms=2.5,alpha=1 if var==.7 else .5)
    ax.set(xlabel='Reference peak load',ylabel='Gain / reference train (CNY k)',title='Headroom supports consolidation');ax.legend(handles=[Line2D([],[],c=CC[ci],label=ci) for ci in CIS]+[Line2D([],[],c='#333',ls=ls,label=f'Variable {v:.0%}') for v,ls in [(.5,':'),(.7,'-'),(.9,'--')]],ncols=2,fontsize=6.5,frameon=False);save(fig,'fares_headroom')

def od_arcs():
    fig,ax=plt.subplots(figsize=(7.48,3.4),layout='constrained');m=Model(C['JX']);base=record(REF['JX'],'P0','profit');allpct=[];allq=[]
    for obj in ['profit','welfare']:
        r=record(REF['JX'],'P3',obj);allpct.extend(100*(np.array(r['rail_by_od'])/base['rail_by_od']-1));allq.extend(r['rail_by_od'])
    lim=max(abs(np.array(allpct)));norm=Normalize(-lim,lim);cmap=LinearSegmentedColormap.from_list('change',['#D55E00','#eeeeee','#0072B2'])
    for obj,sign in [('profit',1),('welfare',-1)]:
        r=record(REF['JX'],'P3',obj)
        for w,od in enumerate(C['JX']['ods']):
            i,j=[C['JX']['cities'].index(x) for x in od.split('-')];q=r['rail_by_od'][w];pct=100*(q/base['rail_by_od'][w]-1);h=(j-i)*.33;ax.add_patch(Arc(((i+j)/2,0),j-i,2*h,theta1=0 if sign==1 else 180,theta2=180 if sign==1 else 360,lw=.7+4*q/max(allq),color=cmap(norm(pct)),alpha=.9));ax.text((i+j)/2,sign*(h+.04),f'{q/1000:.1f}k; {pct:+.1f}%',ha='center',va='bottom' if sign==1 else 'top',fontsize=7.5,bbox=dict(fc='white',ec='#444' if (i,j)==(0,2) else 'none',pad=.8))
    ax.plot(range(4),[0]*4,c='#444',lw=.8);ax.scatter(range(4),[0]*4,s=35,c='white',edgecolor='#333',zorder=3)
    for x,label in enumerate(['GZ','JA','NC','JJ']):ax.text(x,-.07,label,ha='center',va='top',fontweight='bold',fontsize=8)
    ax.text(-.27,.75,'Profit',rotation=90);ax.text(-.27,-.75,'Welfare',rotation=90);ax.set(xlim=(-.38,3.2),ylim=(-1.25,1.25));ax.axis('off');fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,label='Rail-flow change (%)',shrink=.7);save(fig,'od_arcs')

def shocks():
    fig,axs=plt.subplots(1,3,figsize=(7.48,2.7),layout='constrained');xs=[0,.05,.1,.2,.35,.5,.75,1.]
    for k in range(3):
        ends=[]
        for ci in CIS:
            rs=[record(e2(ci,'reference',x),'P0','profit') for x in xs];den=Model(C[ci]).N0.sum();refL=record(REF[ci],'P0','profit')['class_trips'][2]
            yy=[[100*r['rail_by_class'][2]/r['class_trips'][2] for r in rs],[r['class_trips'][2]/refL for r in rs],[(r['profit']+r['budget'])/den/1000 for r in rs]][k];axs[k].plot(xs,yy,c=CC[ci],marker=['o','s','^'][CIS.index(ci)],ms=3,lw=1.2);ends.append(yy[-1])
        axs[k].set(xlabel='Road intensity',ylabel=['L rail share (%)','Absolute L retention','Financial margin / train (CNY k)'][k]);endlabels(axs[k],1,ends,CIS,[CC[x] for x in CIS])
    save(fig,'shocks')

def polarization():
    fig=plt.figure(figsize=(7.48,3.8),layout='constrained');gs=fig.add_gridspec(2,4,height_ratios=[2,1]);metrics=['Common G/D fare','P3 profit trains/day','Seat profit gain (CNY k)','K additions: welfare'];vals={}
    for ci in CIS:
        gd=Model(C[ci]).adjustable;vv=[]
        for inc in ['reference','uniform','polarized']:
            g=next(g for g in groups('E6') if g['job']['case']==ci and g['job']['income']==inc);p=record(g,'P3','profit');sb=record(g,'P3-sb','profit');w=record(e2(ci,inc,0),'P4','welfare');vv.append([(np.array(p['N'])[gd]*np.array(p['phi'])[gd,:,0]).sum()/np.array(p['N'])[gd].sum(),np.array(p['N']).sum(),(sb['profit']-p['profit'])/1000,np.array(w['N'])[[x['candidate'] for x in C[ci]['products']]].sum()])
        vals[ci]=vv
    for k in range(4):
        ax=fig.add_subplot(gs[0,k])
        for y,ci in enumerate(CIS):
            ref,u,p=[v[k] for v in vals[ci]];ax.plot([u,p],[y,y],c='#aaa',lw=1.4);ax.scatter([u,p],[y,y],c=[IC['uniform'],IC['polarized']],s=27,marker='s' if k==3 else 'o',zorder=3);ax.scatter(ref,y,c=IC['reference'],marker='|',s=120,zorder=4)
            for v,offset,col in [(u,7,IC['uniform']),(p,-13,IC['polarized'])]:ax.annotate(f'{v:.3f}' if k==0 else f'{v:.1f}' if k==2 else f'{v:.0f}',(v,y),xytext=(0,offset),textcoords='offset points',ha='center',color=col,fontsize=7)
        ax.set(yticks=range(3),yticklabels=CIS if k==0 else [],ylim=(2.6,-.6),xlabel=metrics[k]);ax.margins(x=.3)
    ax=fig.add_subplot(gs[1,:]);xs=[0,.05,.1,.2,.35,.5,.75,1.]
    for ci in CIS:ax.plot(xs,[np.array(record(e2(ci,'polarized',x),'P3','profit')['N']).sum()-np.array(record(e2(ci,'uniform',x),'P3','profit')['N']).sum() for x in xs],color=CC[ci],marker='o',ms=2.5,label=ci)
    ax.axhline(0,c='#777',lw=.6);ax.set(xlabel='Road intensity',ylabel='Polarized minus uniform\ndepartures/day');ax.legend(ncols=3,frameon=False,fontsize=7)
    fig.legend(handles=[Line2D([],[],c=IC['reference'],marker='|',ls='',label='Reference'),Line2D([],[],c=IC['uniform'],marker='o',ls='',label='Uniform'),Line2D([],[],c=IC['polarized'],marker='o',ls='',label='Polarized')],loc='outside lower center',ncols=3,frameon=False);save(fig,'polarization')

def entries():
    rr=[r for r in D['entry'] if r['departures']];fig=plt.figure(figsize=(7.48,4.8),layout='constrained');gs=fig.add_gridspec(2,2,height_ratios=[1,1]);axs=[fig.add_subplot(gs[0,j]) for j in range(2)]
    for k,ax in enumerate(axs):
        for y,r in enumerate(rr):
            vv=[r['new_revenue_allocation'],r['incumbent_revenue'],r['incumbent_cost_saving'],-r['new_cost']] if k==0 else [r['U_channels'][x] for x in ['fare','schedule','availability','participation']];pos=neg=0
            for v,col in zip(np.array(vv)/1000,PART):ax.barh(y,v,left=pos if v>=0 else neg,color=col,height=.6);pos+=max(0,v);neg+=min(0,v)
            net=(r['profit_change'] if k==0 else r['U_change'])/1000;ax.scatter(net,y,c='#222',s=22,zorder=4);ax.annotate(f'{net:+.0f}',(net,y),xytext=(3,6),textcoords='offset points',fontsize=7)
        ax.set(yticks=range(len(rr)),yticklabels=[r['case_id']+' / '+r['objective'][0].upper() for r in rr] if k==0 else [],xlabel='CNY thousand/day',title='(a) Profit accounting' if k==0 else '(b) Traveler-surplus channels');ax.axvline(0,c='#777',lw=.6);ax.invert_yaxis();ax.margins(x=.2)
        labs=['Added-cohort revenue*','Incumbent revenue change','Incumbent cost saving','Added-cohort cost'] if k==0 else ['Fare','Schedule','Availability','Participation margin'];ax.legend(handles=[Rectangle((0,0),1,1,fc=c,label=l) for c,l in zip(PART,labs)],loc='upper center',bbox_to_anchor=(.5,-.25),ncols=2,frameon=False,fontsize=6.5)
    ax=fig.add_subplot(gs[1,:]);xs=[.1,.25,.5,.75,1.];levels=[0,.05,.1,.2,.35,.5,.75,1.]
    for ci in CIS:
        for obj,ls,marker in [('profit','-','o'),('welfare','--','s')]:
            yy=[]
            for cost in xs:
                found=[]
                for g in groups('E10'):
                    if g['job']['case']!=ci or g['job']['spec']['k_cost']!=cost:continue
                    p=record(g,'P3',obj);r=record(g,'P4',obj)
                    if p['feasible'] and r['feasible'] and np.array(r['N'])[[x['candidate'] for x in C[ci]['products']]].sum()>0 and r['objective_value']-p['objective_value']>1e-4*max(1,abs(p['objective_value'])):found.append(g['job']['spec']['electric_scale'])
                yy.append(max(found) if found else -.12)
            ax.step(xs,yy,where='mid',color=CC[ci],ls=ls,lw=1.2,label=ci+' '+obj);ax.scatter(xs,yy,color=CC[ci],marker=marker,s=18,facecolor=CC[ci] if obj=='profit' else 'white')
    ax.set(xlabel='Tested K cost multiplier',ylabel='Highest tested road intensity\nwith an improving addition',yticks=[-.12,0,.25,.5,.75,1.],yticklabels=['None','0','.25','.50','.75','1.00'],ylim=(-.2,1.12));ax.legend(ncols=3,fontsize=6.5,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.26));save(fig,'entries')

def guarantees():
    fig=plt.figure(figsize=(7.48,3.8),layout='constrained');gs=fig.add_gridspec(2,2,width_ratios=[1.15,1]);ax=fig.add_subplot(gs[:,0]);gg=groups('E9')
    for ci in CIS:
        for pol,ls,marker in [('P3','-','o'),('P4','--','s')]:
            base=record(REF[ci],pol,'profit');rows=sorted([g for g in gg if g['job']['case']==ci and g['job']['spec']['eta']>=.975],key=lambda g:g['job']['spec']['eta']);good=[g for g in rows if record(g,pol,'profit')['feasible']];xx=[base['eta']]+[g['job']['spec']['eta'] for g in good];yy=[0]+[(base['profit']-record(g,pol,'profit')['profit'])/1000 for g in good];idx=np.argsort(xx);ax.step(np.array(xx)[idx],np.array(yy)[idx],where='post',c=CC[ci],ls=ls,lw=1);ax.scatter(xx,yy,c=CC[ci],marker=marker,s=19,facecolor=CC[ci] if pol=='P3' else 'white',label=ci+' '+pol)
    ax.set(xlabel='Vulnerable retention floor',ylabel='Operator profit sacrifice (CNY k/day)',title='(a) Sampled integer-design costs');ax.axvline(1,c='#777',lw=.7,ls=':');ax.legend(ncols=2,fontsize=6.5,frameon=False)
    bx=fig.add_subplot(gs[0,1]);cx=fig.add_subplot(gs[1,1]);floors=D['floors']
    for y,r in enumerate(floors):
        bx.plot([r['L_fare'],r['operator_cost_per_trip']],[y,y],c=CC[r['case_id']],lw=1.2);bx.scatter(r['L_fare'],y,marker='|',c=CC[r['case_id']],s=100);bx.scatter(r['operator_cost_per_trip'],y,c=CC[r['case_id']],s=22);bx.annotate(f'{r["operator_cost_per_trip"]/r["L_fare"]:.0f}x',(r['operator_cost_per_trip'],y),xytext=(5,0),textcoords='offset points',va='center',fontsize=7)
        for j,(key,col) in enumerate([('profit_change',COL['profit']),('U_change',COL['U']),('welfare_change',COL['welfare'])]):cx.barh(y+(j-1)*.22,r[key]/1000,height=.2,color=col)
    bx.set(xscale='log',yticks=range(3),yticklabels=CIS,ylim=(2.4,-.4),xlabel='CNY per restored trip / reference L fare',title='(b) Operator cost exceeds the fare');bx.margins(x=.3);cx.axvline(0,c='#777',lw=.6);cx.set(yticks=range(3),yticklabels=CIS,ylim=(2.4,-.4),xlabel='CNY thousand/day',title='(c) Profit loss transfers to travelers');cx.legend(handles=[Rectangle((0,0),1,1,fc=COL[k],label=l) for k,l in [('profit',r'$\Delta\Pi$'),('U',r'$\Delta U$'),('welfare',r'$\Delta W$')]],ncols=3,frameon=False,fontsize=7,loc='upper center',bbox_to_anchor=(.5,-.3));save(fig,'guarantees')

def equity():
    eq=json.loads((ROOT/'equity_unique.json').read_text(encoding='utf-8'));r=[x for x in eq if x['feasible']];x=np.array([a['dG'] for a in r]);y=100*np.array([a['deta'] for a in r]);fig=plt.figure(figsize=(7.48,3.8),layout='constrained');gs=fig.add_gridspec(2,2,width_ratios=[5,1],height_ratios=[1,4]);ax=fig.add_subplot(gs[1,0]);top=fig.add_subplot(gs[0,0],sharex=ax);right=fig.add_subplot(gs[1,1],sharey=ax);cmap=LinearSegmentedColormap.from_list('visible_density',plt.get_cmap('YlGnBu')(np.linspace(.28,1,256)));hb=ax.hexbin(x,y,gridsize=35,mincnt=1,cmap=cmap,bins='log',linewidths=.1);ax.axhline(0,c='#666',lw=.6);ax.axvline(0,c='#666',lw=.6)
    for sx,sy,tx,ty in [(-1,-1,.02,.08),(-1,1,.02,.9),(1,-1,.73,.08),(1,1,.73,.9)]:
        n=int(np.sum((x*sx>1e-7)&(y*sy>1e-5)));ax.text(tx,ty,f'{n}/{len(r)} = {100*n/len(r):.1f}%',transform=ax.transAxes,fontsize=8,bbox=dict(fc='white',ec='none',alpha=.85))
    top.hist(x,bins=35,color='#8ba6af');right.hist(y,bins=35,orientation='horizontal',color='#8ba6af');top.tick_params(labelbottom=False);right.tick_params(labelleft=False);top.set_ylabel('Designs');right.set_xlabel('Designs');ax.set(xlabel='Change in worst-case realized cost ratio',ylabel='Vulnerable retention change (pp)');fig.colorbar(hb,ax=right,label='Design count (log scale)',shrink=.8)
    on=int(np.sum((abs(x)<=1e-7)|(abs(y)<=1e-5)));fig.suptitle(f'On coordinate axes: {on}/{len(r)} designs ({100*on/len(r):.1f}%)',fontsize=8);save(fig,'equity')

def governance():
    M=json.loads((ROOT/'round2_mechanisms.json').read_text(encoding='utf-8'));fig,axs=plt.subplots(2,3,figsize=(7.48,5.0),layout='constrained')
    for j,ci in enumerate(CIS):
        rows=[r for r in M['governance'] if r['case_id']==ci];ax=axs[0,j];xx=np.array([-r['profit_gap']/1000 for r in rows]);yy=np.array([r['CS_gap']/1000 for r in rows])
        for inc,marker in [('reference','o'),('uniform','s'),('polarized','^')]:
            ix=[i for i,r in enumerate(rows) if r['income']==inc];ax.scatter(xx[ix],yy[ix],c=IC[inc],marker=marker,s=[16+12*rows[i]['intensity'] for i in ix],edgecolor='white',lw=.3)
        ymax=max(abs(xx).max(),yy.max())*1.12;xmin=-ymax
        for level in [0,1000,2000,3000]:
            x=np.array([xmin,0]);y=level-x;ax.plot(x,y,c='#bbb',lw=.5,ls=':')
            if level<ymax*.9:ax.text(level-.97*ymax,.97*ymax,str(level),ha='center',va='top',fontsize=7,color='#888',bbox=dict(fc='white',ec='none',pad=.1))
        r=max(rows,key=lambda r:r['welfare_gap']);x=-r['profit_gap']/1000;y=r['CS_gap']/1000;ax.annotate('',xy=(x,y),xytext=(0,0),arrowprops=dict(arrowstyle='->',lw=.9,color='#333'));ax.set(xlim=(xmin,0),ylim=(0,ymax),xlabel=r'$\Delta\Pi$ (CNY k)',ylabel=r'$\Delta U$ (CNY k)' if j==0 else '',title=ci);ax.set_aspect('equal',adjustable='box');ax.text(.04,.04,f'Max '+r['income']+f', x={r["intensity"]:g}',transform=ax.transAxes,va='bottom',fontsize=6.8,bbox=dict(fc='white',ec='none',alpha=.9))
        waterfall(axs[1,j],[r['CS_gap']/1000,r['revenue_change']/1000,-r['cost_change']/1000,None],[r'$\Delta U$',r'$\Delta R$',r'$-\Delta C$',r'$\Delta W$'],{3},[COL['U'],PART[0],'#009E73']);axs[1,j].set_ylabel('CNY thousand/day' if j==0 else '')
    fig.legend(handles=[Line2D([],[],marker=marker,ls='',c=IC[inc],label=inc.capitalize()) for inc,marker in [('reference','o'),('uniform','s'),('polarized','^')]],loc='outside lower center',ncols=3,frameon=False);save(fig,'governance')

def calibration_dependence():
    fig=plt.figure(figsize=(7.48,6.3),layout='constrained');gs=fig.add_gridspec(2,3,height_ratios=[1,2.2]);cc=json.loads((ROOT/'constant_cost_grid.json').read_text(encoding='utf-8'))['groups']
    for j,ci in enumerate(CIS):
        den=Model(C[ci]).N0.sum();baseline=record(REF[ci],'P3','profit')['profit']-record(REF[ci],'P0','profit')['profit'];ax=fig.add_subplot(gs[0,j])
        for cap,ls,marker in [(1.1,':','^'),(1.2,'-','o'),(1.3,'--','s')]:
            vals=[]
            for anchor in [.6,.8,.85,.9,.95,1.]:
                g=next(g for g in groups('E16') if g['job']['case']==ci and abs(g['job']['anchor']-anchor)<1e-8 and g['job']['cap']==cap);vals.append(record(g,'P3','profit')['welfare']/1000)
            ax.plot([.6,.8,.85,.9,.95,1],vals,c=CC[ci],ls=ls,marker=marker,ms=3,label=f'Cap {cap:.2f}')
        ax.axhline(0,c='#777',lw=.6);ax.set(title=ci+(' (certified)' if ci!='JX' else ' (search witnesses)'),xlabel='Own-product elasticity magnitude',ylabel='Commercial welfare change (CNY k)' if j==0 else '')
        ranges={}
        def take(label,gg):
            vals=[(record(g,'P3','profit')['profit']-record(g,'P0','profit')['profit'])/den/1000 for g in gg if g['job']['case']==ci and pair_feasible(g,'P3')]
            if vals:ranges[label]=(min(vals),max(vals))
        take('Reference load',[g for g in cc if g['job']['spec']['lambda']==.95 and g['job']['spec']['variable_share']==.7]);take('Load ceiling',[g for g in cc if g['job']['spec']['ref_load']==.88 and g['job']['spec']['variable_share']==.7]);take('Variable costs',[g for g in cc if g['job']['spec']['ref_load']==.88 and g['job']['spec']['lambda']==.95]);take('Cost share',[g for g in groups('E8') if g['job']['spec'].get('background')==0]);take('Background*',[g for g in groups('E8') if g['job']['spec'].get('chi')==.5]);take('Elasticity',[g for g in groups('E16') if g['job']['cap']==1.2]);take('Fare cap',[g for g in groups('E16') if g['job']['anchor']==.8]);take('Nest scales',[g for g in groups('E5') if 'mu_' in g['job']['id']]);take('Tariff step',[g for g in groups('E5') if 'grid' in g['job']['id']]);take('Authority',[g for g in groups('E5') if 'authority' in g['job']['id']]);take('Schedule',[g for g in groups('E14') if not g['job']['spec']['active_period_K']]);take('Fleet',groups('E15')+[REF[ci]])
        rr=sorted(ranges.items(),key=lambda z:z[1][1]-z[1][0],reverse=True);ax=fig.add_subplot(gs[1,j]);ax.axvline(baseline/den/1000,c='#333',ls='--',lw=.8)
        for y,(lab,(lo,hi)) in enumerate(rr):ax.barh(y,hi-lo,left=lo,color=CC[ci],alpha=.65,height=.65);ax.plot([lo,hi],[y,y],c=CC[ci],lw=1)
        ax.set(yticks=range(len(rr)),yticklabels=[x[0] for x in rr],ylim=(len(rr)-.4,-.6),xlabel='Profit gain / reference train (CNY k)');ax.tick_params(axis='y',labelsize=7)
    fig.legend(handles=[Line2D([],[],color='#444',ls=ls,marker=marker,ms=4,label=f'Cap {cap:.2f}') for cap,ls,marker in [(1.1,':','^'),(1.2,'-','o'),(1.3,'--','s')]],loc='outside upper center',ncols=3,frameon=False,fontsize=8)
    save(fig,'calibration_dependence')

if __name__=='__main__':
    for fn in [calibration,elasticity,attribution,fares_headroom,od_arcs,shocks,polarization,entries,guarantees,equity,governance,calibration_dependence]:fn();print('rendered',fn.__name__,flush=True)
