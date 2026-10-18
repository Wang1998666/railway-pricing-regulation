"""Read-only use of archived experiments; all new assets stay beside this script.
Run: python redraw_case_figures.py
Arial text / Computer Modern math; PDF, SVG and 300-dpi PNG outputs.
"""
from pathlib import Path
import sys,json,hashlib
P=Path(__file__).resolve().parent
SOURCE=P.parents[1]/'experiments'/'main'
sys.path.insert(0,str(SOURCE))
import figures_round5 as src
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle,PathPatch
from matplotlib.path import Path as MPath
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap,TwoSlopeNorm
from matplotlib.ticker import MaxNLocator,NullFormatter
from PIL import Image,ImageDraw
import fitz

CIS=src.CIS; CC=src.CC; IC=src.IC; PART=src.PART; COL=src.COL
C=src.C; REF=src.REF; Model=src.Model; record=src.record; groups=src.groups
BLUE='#0072B2'; ORANGE='#D55E00'; INK='#263C4A'; GRID='#E6EBEF'
assert Path(font_manager.findfont('Arial',fallback_to_default=False)).is_file()
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial'],
 'font.size':9,'axes.titlesize':10,'axes.titleweight':'bold','axes.labelsize':9,
 'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
 'mathtext.fontset':'cm','pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
 'axes.spines.top':True,'axes.spines.right':True,'axes.linewidth':.65,
 'axes.edgecolor':'#75828C','axes.labelcolor':INK,'text.color':INK,
 'xtick.color':INK,'ytick.color':INK,'savefig.facecolor':'white'})
manifest={}
def finish(fig,num,name):
    from matplotlib.text import Text
    fig.set_size_inches(8.5,fig.get_figheight(),forward=True)
    for t in fig.findobj(Text):t.set_fontfamily('Arial');t.set_fontsize(min(9,max(8,t.get_fontsize())))
    allaxes=list(fig.axes)
    for ax in fig.axes:allaxes.extend(ax.child_axes)
    for ax in allaxes:
        ax.tick_params(direction='out',length=3,width=.6)
        ax.set_axisbelow(True)
        for side in ax.spines.values():side.set_visible(True);side.set_color('#75828C');side.set_linewidth(.65)
        for t in [ax.title,ax._left_title,ax._right_title]:
            t.set_color(INK);t.set_fontfamily('Arial');t.set_fontsize(10 if ax in fig.axes else 8);t.set_fontweight('bold' if ax in fig.axes else 'normal')
    title_audit=[]
    for ax in fig.axes:
        for t in [ax.title,ax._left_title,ax._right_title]:
            if t.get_text():title_audit.append({'text':t.get_text(),'size':t.get_fontsize(),'family':t.get_fontfamily(),'color':t.get_color(),'weight':t.get_fontweight()})
    for ext in ['pdf','svg','png']:
        fig.savefig(P/f'fig{num:02d}_{name}.{ext}',dpi=300,bbox_inches=None)
    manifest[str(num)]={'name':name,'pdf':f'fig{num:02d}_{name}.pdf','panel_titles':title_audit,'canvas_width_inches':8.5}
    plt.close(fig)
def grid(ax,axis='x'):
    ax.grid(axis=axis,color=GRID,lw=.55)
def title(ax,label,text): ax.set_title(f'({label}) {text}',loc='left',pad=9)
def legend_corridors(fig,loc='outside lower center'):
    fig.legend(handles=[Line2D([],[],color=CC[c],ls=['-','--','-.'][i],
         marker=['D','^','v'][i],ms=4,lw=1.4,label=c) for i,c in enumerate(CIS)],
         loc=loc,ncols=3,frameon=False)

def fig04():
    fig=plt.figure(figsize=(8.5,7.9),layout='constrained')
    gs=fig.add_gridspec(2,2,height_ratios=[1.0,1.05],width_ratios=[.9,1.1])
    ax=fig.add_subplot(gs[0,:]);r=record(REF['WC'],'P0','profit');m=Model(C['WC'])
    raw=m.evaluate(m.N0,np.ones((m.S,4,3)),True);qr=raw['qr'][0]
    Q=np.array(r['Q']);pm=np.array(r['mode_probs']);pop=np.array(r['class_potential'])/1000
    trips=np.array(r['class_trips'])/1000;total=pop.sum()
    modes={n:(Q*pm[:,:,:,i]).sum(axis=(0,2))/1000 for i,n in enumerate(['Rail','Road','Auto'])}
    tiers={t:np.array(r['tier_by_class'][t])/1000 for t in ['G','D','K']}
    stages=[{cl:np.eye(3)[k]*pop[k] for k,cl in enumerate(['H','M','L'])},
            {'Travel':trips,'No travel':pop-trips},modes,tiers,{}]
    for t in tiers:
        for b in range(3):
            vals=qr[:,:,:,m.tier==t,b].sum(axis=(0,2,3))/1000
            if vals.sum()>0: stages[-1][f'{t}-{b+1}']=vals
    classcols=['#244C66','#4B96AE','#CF943F'];positions=[]
    gap=total*.035
    for j,stage in enumerate(stages):
        ypos=0;pos={}
        for name,vals in stage.items():
            pos[name]=[];start=ypos
            for k,v in enumerate(vals):
                pos[name].append(ypos);ax.add_patch(Rectangle((j-.027,ypos),.054,v,
                  fc=classcols[k],ec='white',lw=.25,zorder=4));ypos+=v
            ax.text(j+.045,(start+ypos)/2,f'{name}  {sum(vals):.1f}',va='center',fontsize=8,
                    bbox=dict(fc='white',ec='none',pad=.35,alpha=.88),zorder=5)
            ypos+=gap
        positions.append(pos)
    links=[]
    for k,name in enumerate(['H','M','L']): links.extend([(0,name,'Travel',k,trips[k]),(0,name,'No travel',k,pop[k]-trips[k])])
    for j,source in [(1,'Travel'),(2,'Rail')]:
        for name,vals in stages[j+1].items(): links.extend((j,source,name,k,v) for k,v in enumerate(vals))
    for name,vals in stages[4].items():links.extend((3,name[0],name,k,v) for k,v in enumerate(vals))
    outgoing={};incoming={}
    for j,s,d,k,v in links:
        sk=(j,s,k);dk=(j+1,d,k);y0=positions[j][s][k]+outgoing.get(sk,0);y1=positions[j+1][d][k]+incoming.get(dk,0)
        x0=j+.027;x1=j+1-.027
        vertices=[(x0,y0),(x0+.3,y0),(x1-.3,y1),(x1,y1),(x1,y1+v),(x1-.3,y1+v),(x0+.3,y0+v),(x0,y0+v),(x0,y0)]
        codes=[1,4,4,4,2,4,4,4,79]
        ax.add_patch(PathPatch(MPath(vertices,codes),fc=classcols[k],ec='white',lw=.12,alpha=.43))
        outgoing[sk]=outgoing.get(sk,0)+v;incoming[dk]=incoming.get(dk,0)+v
    for j,head in enumerate(['Income class','Participation','Mode','Rail tier','Seat class']):
        ax.text(j,-total*.065,head,fontsize=8.5,fontweight='bold',ha='left')
    ax.set(xlim=(-.12,4.66),ylim=(total*1.32,-total*.12),xticks=[],yticks=[])
    title(ax,'a','WC reference demand: class-preserving flows (thousand/day)')
    ax.text(.99,.02,'Participation 85%  |  Rail share of trips 70%',transform=ax.transAxes,ha='right',fontsize=8)
    ax.legend(handles=[Rectangle((0,0),1,1,fc=c,label=l) for c,l in zip(classcols,['High income','Middle income','Low income'])],loc='lower left',ncols=3,frameon=False,fontsize=8)
    bx=fig.add_subplot(gs[1,0]);classy=np.arange(3)
    values=[]
    for inc in ['reference','uniform','polarized']:
        values.append(60*np.array([.035,.03,.025])/(np.array([.012,.02,.035])*np.exp(-np.array([.7,.8,.9])*src.INCOMES[inc])))
    for k in range(3):
        bx.axhspan(k-.42,k+.42,fc='#F4F7F9',zorder=0)
        bx.plot([min(v[k] for v in values),max(v[k] for v in values)],[k,k],c='#CBD4DC',lw=5,solid_capstyle='round')
        for j,(inc,v) in enumerate(zip(['reference','uniform','polarized'],values)):
            yy=k+(j-1)*.23;bx.scatter(v[k],yy,c=IC[inc],marker=['|','D','^'][j],s=[55,22,25][j],zorder=3)
            bx.annotate(f'{v[k]:.1f}',(v[k],yy),xytext=(5,0),textcoords='offset points',va='center',fontsize=8,color=IC[inc])
    bx.set(xlim=(25,225),yticks=classy,yticklabels=['H','M','L'],ylim=(2.55,-.55),xlabel='Value of time (CNY/h)');grid(bx)
    title(bx,'b','Income composition and VOT')
    bx.legend(handles=[Line2D([],[],ls='',marker=mk,c=IC[inc],label=inc.capitalize()) for inc,mk in zip(['reference','uniform','polarized'],['|','D','^'])],loc='lower right',frameon=False)
    cx=fig.add_subplot(gs[1,1]);labels=[]
    for i,mode in enumerate(['Auto','Coach','MaaS','Van']):
        cx.axhspan(3*i-.45,3*i+2.45,fc='#F4F7F9' if i%2==0 else 'white',zorder=0)
        for j,ci in enumerate(CIS):
            mm=Model(C[ci]);w=int(np.argmax(mm.c['road_km']));base=mm.road[w,i,0];new=base-mm.c['road_km'][w]*[.145,.084,.14,.21][i];y=3*i+j
            labels.append(mode+' / '+ci);cx.plot([new,base],[y,y],c=CC[ci],lw=1.6,solid_capstyle='round')
            cx.scatter(base,y,c=CC[ci],marker='|',s=65,zorder=3);cx.scatter(new,y,ec=CC[ci],fc='white',marker='D',s=20,zorder=3)
            cx.annotate(f'{new:.0f}',(new,y),xytext=(-5,0),textcoords='offset points',ha='right',va='center',fontsize=8,color=CC[ci])
            cx.annotate(f'{base:.0f}',(base,y),xytext=(5,0),textcoords='offset points',va='center',fontsize=8,color=CC[ci])
    cx.set(yticks=range(12),yticklabels=labels,ylim=(12.1,-.8),xlim=(-110,1430),xlabel='Passenger money cost (CNY)');grid(cx)
    title(cx,'c','Road cost reduction: longest OD')
    cx.text(.98,.02,r'$x=0$: tick; $x=1$: diamond',transform=cx.transAxes,ha='right',fontsize=8)
    finish(fig,4,'calibration')

def fig05():
    E=json.loads((SOURCE/'elasticities_round2.json').read_text(encoding='utf-8'))
    E={e['case_id']:e for e in E};fig,axs=plt.subplots(1,3,figsize=(8.5,4),layout='constrained',sharex=True,sharey=True)
    for i,ci in enumerate(CIS):
        ax=axs[i];e=E[ci]
        ax.axvspan(-1.21,-.67,color='#DCE5EB',alpha=.75,zorder=0)
        for k,cl in enumerate(['H','M','L']):
            own=np.array([p['own_by_class'][k] for p in e['products']]);weighted=e['own_GD_by_class'][k];pooled=e['pooled_GD_K_fixed'][k];allrail=e['all_rail_fares'][k]
            ax.axhline(k+.5,c=GRID,lw=.6,zorder=0)
            ax.plot([own.min(),own.max()],[k-.18]*2,c=CC[ci],lw=1.2,alpha=.65,zorder=2)
            ax.scatter(own,np.full(len(own),k-.18),c=CC[ci],marker='|',s=22,linewidths=.65,alpha=.55,zorder=2)
            ax.scatter(weighted,k-.18,c=CC[ci],marker='D',s=26,ec='white',lw=.5,zorder=4)
            ax.scatter(pooled,k,ec=CC[ci],fc='white',marker='^',s=26,lw=1,zorder=4)
            ax.scatter(allrail,k+.18,ec=CC[ci],fc='white',marker='s',s=22,lw=1,zorder=4)
            ax.annotate(f'{weighted:.2f}',(weighted,k-.18),xytext=(-5,-13),textcoords='offset points',ha='right',fontsize=8,color=CC[ci],bbox=dict(fc='white',ec='none',pad=.5,alpha=.9))
        ax.axvline(0,c='#87949E',lw=.7);ax.set(xlim=(-3.3,.10),ylim=(2.65,-.65),yticks=range(3),yticklabels=['H','M','L'],xlabel='Fare elasticity');title(ax,chr(97+i),ci+' calibration');grid(ax)
        ax.set_xticks([-3,-2,-1,0]);ax.tick_params(labelleft=True)
    fig.legend(handles=[Line2D([],[],c=INK,marker='D',lw=1,label='Own G/D: weighted value / range',ms=4),Line2D([],[],c=INK,marker='|',ls='',label='Individual products',ms=7),Line2D([],[],c=INK,marker='^',mfc='white',ls='',label='Pooled G/D, K fixed',ms=4),Line2D([],[],c=INK,marker='s',mfc='white',ls='',label='All-rail fares',ms=4),Rectangle((0,0),1,1,fc='#DCE5EB',label='Train-OD reference range')],loc='outside lower center',ncols=2,frameon=False,fontsize=8)
    finish(fig,5,'elasticity')

def fig06():
    # The preserved TikZ layout is compiled separately with Arial text.
    f=P/'fig06_solution_workflow.pdf'
    assert f.exists(),'Compile fig06_solution_workflow.tex first with XeLaTeX'
    d=fitz.open(f);d[0].get_pixmap(matrix=fitz.Matrix(300/72,300/72),alpha=False).save(P/'fig06_solution_workflow.png')
    (P/'fig06_solution_workflow.svg').write_text(d[0].get_svg_image(text_as_path=False),encoding='utf-8')
    manifest['6']={'name':'solution_workflow','pdf':f.name,'panel_titles':[],'typography_only':True}

def fig07():
    oldsave=src.save
    def save(fig,name):
        fig.set_size_inches(8.5,7.2)
        for j,ci in enumerate(CIS):
            for offset,row,label in [(0,0,'profit'),(2,1,'P3 accounting'),(1,2,'welfare')]:
                ax=fig.axes[3*j+offset];ax.set_title('');title(ax,chr(97+3*row+j),ci+' / '+label)
        finish(fig,7,'attribution')
    src.save=save
    try:src.attribution()
    finally:src.save=oldsave

def fig13():
    # Execute the archived plotting function while redirecting its exports here.
    # Saved certified observations, positions, shapes, and annotations stay intact.
    import importlib.util,csv
    from matplotlib.figure import Figure
    spec=importlib.util.spec_from_file_location('preserved_frontier',P.parents[1]/'editorial'/'figure17_round7.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with (P.parents[1]/'experiments'/'policy_grid'/'cap_floor_frontier.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
    for r in rows:
        for k in ['cap','floor','profit_gain','welfare']:r[k]=float(r[k])
        r['nondominated']=r['nondominated']=='True'
    captured=[];oldsave=Figure.savefig;oldclose=plt.close;oldrc=plt.rcParams.copy()
    Figure.savefig=lambda fig,*a,**k:captured.append(fig)
    plt.close=lambda *a,**k:None
    try:module.plot(rows)
    finally:Figure.savefig=oldsave;plt.close=oldclose;plt.rcParams.update(oldrc)
    fig=captured[0]
    for i,ax in enumerate(fig.axes):
        ax.set_title('');title(ax,chr(97+i),CIS[i]+' certified P3 outcomes')
        ax.set_xlabel('Profit gain over P0 (CNY thousand/day)',fontsize=9);ax.set_ylabel('Welfare change from P0 (CNY thousand/day)',fontsize=9)
        ax.tick_params(labelsize=8)
        for child in ax.child_axes:child.tick_params(labelsize=8)
    for leg in fig.legends:
        for t in leg.get_texts():t.set_fontsize(8)
    finish(fig,13,'cap_floor_frontier')

def fig17():
    oldsave=src.save
    def save(fig,name):
        fig.set_size_inches(8.5,6.8)
        for j,ci in enumerate(CIS):
            ax=fig.axes[2*j];ax.set_title('');title(ax,chr(97+j),ci+(' (certified)' if ci!='JX' else ' (search witnesses)'))
            ax=fig.axes[2*j+1];title(ax,chr(100+j),ci+' sensitivity ranges')
        finish(fig,17,'calibration_dependence')
    src.save=save
    try:src.calibration_dependence()
    finally:src.save=oldsave

def fig08():
    fig=plt.figure(figsize=(8.3,7.2),layout='constrained');gs=fig.add_gridspec(3,2,height_ratios=[1,1,1.25],width_ratios=[1,1.12])
    loc={'HN':gs[0,0],'WC':gs[1,0],'JX':gs[:,1]}
    for ci in CIS:
        ax=fig.add_subplot(loc[ci]);m=Model(C[ci]);rs=[record(REF[ci],'P3',o) for o in ['profit','welfare']]
        coords=[(s,h) for s in np.flatnonzero(m.adjustable) for h in range(4) if any(r['N'][s][h]>0 for r in rs)]
        ax.axvspan(1.15,1.20,color='#F8E7D7',alpha=.8);ax.axvline(1.2,c=ORANGE,lw=.8,ls='--');ax.axvline(1,c='#BDC8D0',lw=.65)
        for y,(s,h) in enumerate(coords):
            if y%2==0:ax.axhspan(y-.46,y+.46,fc='#F5F7F9',zorder=0)
            active=[i for i,r in enumerate(rs) if r['N'][s][h]>0]
            if len(active)==2:ax.plot([rs[i]['phi'][s][h][0] for i in active],[y]*2,c=CC[ci],lw=.6,alpha=.27)
            for i in active:ax.scatter(rs[i]['phi'][s][h][0],y+(-.10 if i==0 else .10),marker='D' if i==0 else '|',c=CC[ci],s=19 if i==0 else 65,linewidths=.75 if i==0 else 1.4,zorder=3)
            ax.text(1.235,y,' / '.join(f'{int(r["N"][s][h]-m.N0[s,h]):+d}' for r in rs),va='center',fontsize=8,color=CC[ci])
        ax.set(yticks=range(len(coords)),yticklabels=[m.c['products'][s]['id']+'-'+['AM','Day','PM','Night'][h] for s,h in coords],ylim=(len(coords)-.4,-.7),xlim=(.78,1.36),xticks=[.8,.9,1,1.1,1.2],xlabel='G/D fare multiplier')
        title(ax,{'HN':'a','WC':'b','JX':'d'}[ci],ci+'  |  right: departures P / W')
        ax.tick_params(axis='y',labelsize=8)
    ax=fig.add_subplot(gs[2,0]);rr=src.A['headroom']
    for ci in CIS:
        den=Model(C[ci]).N0.sum()
        for var,ls in [(.5,':'),(.7,'-'),(.9,'--')]:
            z=sorted([r for r in rr if r['case_id']==ci and r['objective']=='profit' and r['spec']['lambda']==.95 and r['spec']['variable_share']==var],key=lambda r:r['spec']['ref_load'])
            ax.plot([r['spec']['ref_load'] for r in z],[r['gain']/den/1000 for r in z],c=CC[ci],ls=ls,lw=1.6 if var==.7 else .95,marker='D' if var==.7 else None,ms=3,alpha=1 if var==.7 else .65)
    ax.set(xlabel='Reference peak load',ylabel='Profit gain / observed train (CNY k)');title(ax,'c','Capacity headroom');grid(ax,axis='both')
    ax.legend(handles=[Line2D([],[],c=CC[ci],label=ci) for ci in CIS]+[Line2D([],[],c=INK,ls=ls,label=f'Variable {v:.0%}') for v,ls in [(.5,':'),(.7,'-'),(.9,'--')]],ncols=2,fontsize=8,frameon=False)
    fig.legend(handles=[Line2D([],[],marker='D',ls='',c=INK,label='P: commercial'),Line2D([],[],marker='|',ms=9,ls='',c=INK,label='W: welfare')],loc='outside lower center',ncols=2,frameon=False)
    finish(fig,8,'fares_headroom')

def fig09():
    base=np.array(record(REF['JX'],'P0','profit')['rail_by_od']);p=np.array(record(REF['JX'],'P3','profit')['rail_by_od']);w=np.array(record(REF['JX'],'P3','welfare')['rail_by_od'])
    ids={city:label for city,label in zip(C['JX']['cities'],['Ganzhou','Ji’an','Nanchang','Jiujiang'])}
    labs=[' – '.join(ids[x] for x in od.split('-')) for od in C['JX']['ods']]
    vals=np.array([base,p,w]).T/1000;pct=100*(np.array([p,w]).T/base[:,None]-1)
    fig,(ax,bx)=plt.subplots(1,2,figsize=(8.5,4.0),layout='constrained',gridspec_kw={'width_ratios':[1,1.15]})
    ax.imshow(vals,aspect='auto',cmap=LinearSegmentedColormap.from_list('volume',['#F3F7FA','#BED3DF','#477B98']),vmin=0,vmax=vals.max()*1.7)
    for i in range(6):
        for j in range(3):ax.text(j,i,f'{vals[i,j]:.1f}',ha='center',va='center',fontweight='bold' if j==0 else 'normal',fontsize=10)
    ax.set(xticks=range(3),xticklabels=['P0','P3 profit','P3 welfare'],yticks=range(6),yticklabels=labs);ax.tick_params(length=0);title(ax,'a','Rail trips (thousand/day)')
    target=next(i for i,od in enumerate(C['JX']['ods']) if od.split('-')==[C['JX']['cities'][0],C['JX']['cities'][2]])
    ax.add_patch(Rectangle((-.49,target-.49),2.98,.98,fill=False,ec=INK,lw=1.2))
    for i in range(6):
        if i%2==0:bx.axhspan(i-.45,i+.45,fc='#F4F7F9',zorder=0)
        bx.plot(pct[i],[i,i],c='#BCC8D1',lw=1)
        for j,(col,mk) in enumerate([(ORANGE,'D'),(BLUE,'^')]):
            yy=i+(-.11 if j==0 else .11);bx.scatter(pct[i,j],yy,c=col,marker=mk,s=26,zorder=3)
            bx.annotate(f'{pct[i,j]:+.1f}%',(pct[i,j],yy),xytext=(-6 if j==0 else 6,0),textcoords='offset points',ha='right' if j==0 else 'left',va='center',fontsize=8.5,color=col)
    bx.axvline(0,c=INK,lw=.8);bx.set(yticks=range(6),yticklabels=[],ylim=(5.5,-.5),xlim=(pct.min()-3,pct.max()+3),xlabel='Rail-flow change from P0 (%)');grid(bx);title(bx,'b','Policy response by OD')
    fig.legend(handles=[Line2D([],[],c=ORANGE,marker='D',ls='',label='Commercial P3'),Line2D([],[],c=BLUE,marker='^',ls='',label='Welfare P3')],loc='outside lower center',ncols=2,frameon=False)
    finish(fig,9,'od_comparison')

def fig10():
    xs=np.array([0,.05,.1,.2,.35,.5,.75,1.]);fig,axs=plt.subplots(3,3,figsize=(8.4,5.3),layout='constrained',sharex=True,sharey='col')
    metrics=['L rail share (%)','Absolute L retention','Financial margin / train (CNY k)']
    for i,ci in enumerate(CIS):
        rs=[record(src.e2(ci,'reference',x),'P0','profit') for x in xs];den=Model(C[ci]).N0.sum();refL=record(REF[ci],'P0','profit')['class_trips'][2]
        ys=[[100*r['rail_by_class'][2]/r['class_trips'][2] for r in rs],[r['class_trips'][2]/refL for r in rs],[(r['profit']+r['budget'])/den/1000 for r in rs]]
        for k in range(3):
            ax=axs[i,k];yy=np.array(ys[k]);ax.fill_between(xs,yy,yy[0],color=CC[ci],alpha=.07)
            ax.plot(xs,yy,c=CC[ci],ls=['-','--','-.'][i],lw=1.5,marker=['D','^','v'][i],ms=3.5,mew=.65,mfc='white',markevery=[0,3,5,7])
            ax.scatter([0,1],[yy[0],yy[-1]],c=CC[ci],s=12,zorder=3)
            ax.set_xlim(-.05,1.05);ax.set_xticks([0,.5,1]);grid(ax,axis='both');ax.yaxis.set_major_locator(MaxNLocator(4))
            if i==0:title(ax,chr(97+k),metrics[k])
            if i==2:ax.set_xlabel('Road intensity')
            if k==0:ax.set_ylabel(ci,fontweight='bold',color=CC[ci])
    legend_corridors(fig);finish(fig,10,'shock_profiles')

def fig11():
    fig=plt.figure(figsize=(8.5,5.3),layout='constrained');gs=fig.add_gridspec(2,4,height_ratios=[1.65,1]);metrics=['Fare multiplier','Departures/day','CNY thousand/day','Departures/day'];heads=['Mean G/D fare','Commercial trains','Seat-pricing increment','Welfare K additions'];vals={}
    for ci in CIS:
        gd=Model(C[ci]).adjustable;vv=[]
        for inc in ['reference','uniform','polarized']:
            g=next(g for g in groups('E6') if g['job']['case']==ci and g['job']['income']==inc);p=record(g,'P3','profit');sb=record(g,'P3-sb','profit');w=record(src.e2(ci,inc,0),'P4','welfare')
            vv.append([(np.array(p['N'])[gd]*np.array(p['phi'])[gd,:,0]).sum()/np.array(p['N'])[gd].sum(),np.array(p['N']).sum(),(sb['profit']-p['profit'])/1000,np.array(w['N'])[[x['candidate'] for x in C[ci]['products']]].sum()])
        vals[ci]=vv
    for k in range(4):
        ax=fig.add_subplot(gs[0,k])
        for y,ci in enumerate(CIS):
            ref,u,p=[v[k] for v in vals[ci]];ax.axhspan(y-.43,y+.43,fc='#F4F7F9',zorder=0)
            ax.plot([u,p],[y-.14,y+.14],c='#AAB8C3',lw=1.0,zorder=1)
            ax.scatter(ref,y,marker='|',s=80,c=IC['reference'],zorder=2)
            for value,yy,col,mk,offset in [(u,y-.14,BLUE,'D',8),(p,y+.14,ORANGE,'^',-10)]:
                ax.scatter(value,yy,c=col,marker=mk,s=24,zorder=3)
                ax.annotate(f'{value:.3f}' if k==0 else f'{value:.1f}' if k==2 else f'{value:.0f}',(value,yy),xytext=(0,offset),textcoords='offset points',ha='center',va='top' if offset<0 else 'bottom',color=col,fontsize=8)
        ax.set(yticks=range(3),yticklabels=CIS if k==0 else [],ylim=(2.58,-.58),xlabel=metrics[k]);title(ax,chr(97+k),heads[k]);ax.margins(x=.3);grid(ax)
    ax=fig.add_subplot(gs[1,:]);xs=[0,.05,.1,.2,.35,.5,.75,1.]
    for i,ci in enumerate(CIS):
        yy=[np.array(record(src.e2(ci,'polarized',x),'P3','profit')['N']).sum()-np.array(record(src.e2(ci,'uniform',x),'P3','profit')['N']).sum() for x in xs]
        ax.plot(xs,yy,color=CC[ci],ls=['-','--','-.'][i],lw=1.5,marker=['D','^','v'][i],mfc='white',ms=3.8,label=ci)
    ax.axhline(0,c='#87949E',lw=.65);ax.set(xlabel='Road intensity',ylabel='Departure difference\npolarized − uniform');grid(ax,axis='both');title(ax,'e','Commercial departure response');ax.legend(ncols=3,frameon=False,loc='upper right')
    fig.legend(handles=[Line2D([],[],c=IC['reference'],marker='|',ls='',label='Reference'),Line2D([],[],c=BLUE,marker='D',ls='',label='Uniform'),Line2D([],[],c=ORANGE,marker='^',ls='',label='Polarized')],loc='outside lower center',ncols=3,frameon=False)
    finish(fig,11,'income_composition')

def fig12():
    rr=[r for r in src.D['entry'] if r['departures']];fig=plt.figure(figsize=(8.5,6.3),layout='constrained');gs=fig.add_gridspec(2,2,height_ratios=[1.4,1])
    for k in range(2):
        ax=fig.add_subplot(gs[0,k])
        for y,r in enumerate(rr):
            if y%2==0:ax.axhspan(y-.45,y+.45,fc='#F2F5F8',zorder=0)
            vv=[r['new_revenue_allocation'],r['incumbent_revenue'],r['incumbent_cost_saving'],-r['new_cost']] if k==0 else [r['U_channels'][x] for x in ['fare','schedule','availability','participation']];pos=neg=0
            for v,col in zip(np.array(vv)/1000,PART):
                ax.barh(y,v,left=pos if v>=0 else neg,color=col,height=.56,ec='white',lw=.4,zorder=2);pos+=max(0,v);neg+=min(0,v)
            net=(r['profit_change'] if k==0 else r['U_change'])/1000
            ax.plot([net,net],[y-.30,y+.30],c=INK,lw=.9,zorder=4)
        ax.set(yticks=range(len(rr)),yticklabels=[r['case_id']+' / '+r['objective'][0].upper() for r in rr] if k==0 else [],xlabel='CNY thousand/day',ylim=(len(rr)-.4,-.9));ax.axvline(0,c='#87949E',lw=.65);ax.margins(x=.32);grid(ax)
        for y,r in enumerate(rr):
            net=(r['profit_change'] if k==0 else r['U_change'])/1000
            ax.text(.985,y,f'{net:+,.0f}',transform=ax.get_yaxis_transform(),ha='right',va='center',fontsize=8.5,color=INK,bbox=dict(fc='white',ec='none',pad=1.5))
        ax.text(.985,-.62,'Net',transform=ax.get_yaxis_transform(),ha='right',va='center',fontsize=8.5,fontweight='bold',color=INK)
        title(ax,chr(97+k),'Profit accounting' if k==0 else 'Traveler-surplus channels')
        labs=['Added-cohort revenue*','Incumbent revenue change','Incumbent cost saving','Added-cohort cost'] if k==0 else ['Fare','Schedule','Availability','Participation margin']
        ax.legend(handles=[Rectangle((0,0),1,1,fc=c,label=l) for c,l in zip(PART,labs)]+[Line2D([],[],marker='|',ls='',c=INK,ms=7,label='Net change')],loc='upper center',bbox_to_anchor=(.5,-.20),ncols=2,frameon=False,fontsize=8)
    sub=gs[1,:].subgridspec(1,3);xs=[.1,.25,.5,.75,1.]
    for j,ci in enumerate(CIS):
        ax=fig.add_subplot(sub[0,j])
        for obj,ls,marker in [('profit','-','D'),('welfare','--','^')]:
            yy=[]
            for cost in xs:
                found=[]
                for g in groups('E10'):
                    if g['job']['case']!=ci or g['job']['spec']['k_cost']!=cost:continue
                    p=record(g,'P3',obj);r=record(g,'P4',obj)
                    if p['feasible'] and r['feasible'] and np.array(r['N'])[[x['candidate'] for x in C[ci]['products']]].sum()>0 and r['objective_value']-p['objective_value']>1e-4*max(1,abs(p['objective_value'])):found.append(g['job']['spec']['electric_scale'])
                yy.append(max(found) if found else -.12)
            ax.step(xs,yy,where='mid',color=CC[ci],ls=ls,lw=1.4);ax.scatter(xs,yy,ec=CC[ci],marker=marker,s=18,fc=CC[ci] if obj=='profit' else 'white',zorder=3)
        ax.set(xlabel='K cost multiplier',yticks=[-.12,0,.5,1],yticklabels=['None','0','0.50','1.00'] if j==0 else [],ylim=(-.22,1.14),xticks=[.1,.5,1]);grid(ax,axis='both');title(ax,chr(99+j),ci+' entry domain')
        if j==0:ax.set_ylabel('Highest tested road intensity')
    fig.legend(handles=[Line2D([],[],c=INK,ls='-',marker='D',ms=3,label='Profit'),Line2D([],[],c=INK,ls='--',marker='^',mfc='white',ms=3,label='Welfare')],loc='outside lower center',ncols=2,frameon=False)
    finish(fig,12,'entry_accounting')

def fig14():
    # Separate corridor lanes preserve the sampled step coordinates and prevent overplotting.
    fig=plt.figure(figsize=(8.5,5.7),layout='constrained');gs=fig.add_gridspec(3,2,width_ratios=[1.1,1])
    gg=groups('E9')
    for i,ci in enumerate(CIS):
        ax=fig.add_subplot(gs[i,0])
        for pol,ls,mk in [('P3','-','D'),('P4','--','^')]:
            base=record(REF[ci],pol,'profit');rows=sorted([g for g in gg if g['job']['case']==ci and g['job']['spec']['eta']>=.975],key=lambda g:g['job']['spec']['eta']);good=[g for g in rows if record(g,pol,'profit')['feasible']]
            xx=np.array([base['eta']]+[g['job']['spec']['eta'] for g in good]);yy=np.array([0]+[(base['profit']-record(g,pol,'profit')['profit'])/1000 for g in good]);idx=np.argsort(xx)
            ax.step(xx[idx],yy[idx],where='post',c=CC[ci],ls=ls,lw=1.3 if pol=='P3' else 1.0,alpha=.9 if pol=='P3' else .72)
            ax.scatter(xx,yy,ec=CC[ci],fc=CC[ci] if pol=='P3' else 'white',s=13,marker=mk,lw=.65,zorder=3)
        ax.axvline(1,c='#87949E',lw=.65,ls=':');ax.set_xlim(.972,1.007);grid(ax,axis='both');ax.set_ylabel(ci+'\nprofit cost (CNY k)',color=CC[ci]);ax.yaxis.set_major_locator(MaxNLocator(3))
        if i==0:title(ax,'a','Sampled floor costs by corridor')
        if i==2:ax.set_xlabel('Vulnerable retention floor')
        else:ax.tick_params(labelbottom=False)
    bx=fig.add_subplot(gs[0,1]);cx=fig.add_subplot(gs[1:,1])
    for y,r in enumerate(src.D['floors']):
        bx.plot([r['L_fare'],r['operator_cost_per_trip']],[y,y],c=CC[r['case_id']],lw=1.1)
        bx.scatter(r['L_fare'],y,marker='|',c=CC[r['case_id']],s=65);bx.scatter(r['operator_cost_per_trip'],y,c=CC[r['case_id']],marker='D',s=18)
        bx.annotate(f'{r["operator_cost_per_trip"]/r["L_fare"]:.0f}×',(r['operator_cost_per_trip'],y),xytext=(5,0),textcoords='offset points',va='center',fontsize=8)
        for j,(key,col) in enumerate([('profit_change',COL['profit']),('U_change',COL['U']),('welfare_change',COL['welfare'])]):cx.barh(y+(j-1)*.22,r[key]/1000,height=.18,color=col)
    bx.set(xscale='log',yticks=range(3),yticklabels=CIS,ylim=(2.5,-.5),xlabel='CNY per trip');bx.margins(x=.3);bx.xaxis.set_minor_formatter(NullFormatter());grid(bx);title(bx,'b','Restoration cost versus L fare')
    cx.axvline(0,c='#87949E',lw=.65);cx.set(yticks=range(3),yticklabels=CIS,ylim=(2.5,-.5),xlabel='CNY thousand/day');grid(cx);title(cx,'c','Profit loss and traveler gains')
    cx.legend(handles=[Rectangle((0,0),1,1,fc=COL[k],label=l) for k,l in [('profit',r'$\Delta\Pi$'),('U',r'$\Delta U$'),('welfare',r'$\Delta W$')]],ncols=3,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.17),borderaxespad=0)
    fig.legend(handles=[Line2D([],[],c=INK,ls='-',marker='D',ms=3,label='P3'),Line2D([],[],c=INK,ls='--',marker='^',mfc='white',ms=3,label='P4')],loc='outside lower center',ncols=2,frameon=False)
    finish(fig,14,'mobility_guarantees')

def fig15():
    rr=[r for r in json.loads((SOURCE/'equity_unique.json').read_text(encoding='utf-8')) if r['feasible']];x=np.array([r['dG'] for r in rr]);y=100*np.array([r['deta'] for r in rr])
    fig=plt.figure(figsize=(8.5,5.4),layout='constrained');gs=fig.add_gridspec(2,2,width_ratios=[5,1],height_ratios=[1,4]);ax=fig.add_subplot(gs[1,0]);top=fig.add_subplot(gs[0,0],sharex=ax);right=fig.add_subplot(gs[1,1],sharey=ax)
    xmin=x.min()-.14*np.ptp(x);xmax=x.max()+.14*np.ptp(x);ymin=y.min()-.14*np.ptp(y);ymax=y.max()+.14*np.ptp(y)
    ax.add_patch(Rectangle((xmin,ymin),-xmin,-ymin,fc='#FFF0E7',ec='none',zorder=0))
    hidden=(x< -1e-7)&(y< -1e-5);ax.scatter(x[~hidden],y[~hidden],s=8,fc=BLUE,ec='none',alpha=.23,rasterized=False)
    ax.scatter(x[hidden],y[hidden],s=10,fc=ORANGE,ec='none',alpha=.4,rasterized=False)
    ax.axhline(0,c='#74838F',lw=.8);ax.axvline(0,c='#74838F',lw=.8)
    for sx,sy,tx,ty,va in [(-1,-1,.025,.045,'bottom'),(-1,1,.025,.96,'top'),(1,-1,.975,.045,'bottom'),(1,1,.975,.96,'top')]:
        n=int(np.sum((x*sx>1e-7)&(y*sy>1e-5)));ax.text(tx,ty,f'{n:,} / {len(rr):,}  ({100*n/len(rr):.1f}%)',transform=ax.transAxes,fontsize=9,ha='left' if sx<0 else 'right',va=va,fontweight='bold',color=ORANGE if sx==sy==-1 else INK,bbox=dict(fc='white',ec='none',alpha=.9,pad=3))
    ax.text(.025,.18,'Lower realized cost ratio\nwith lost vulnerable trips',transform=ax.transAxes,fontsize=8.5,color=ORANGE)
    ax.set(xlim=(xmin,xmax),ylim=(ymin,ymax),xlabel='Change in worst-case realized-traveler cost ratio',ylabel='Vulnerable retention change (percentage points)');grid(ax,axis='both')
    top.hist(x,bins=38,color='#7DABBF',ec='white',lw=.25);right.hist(y,bins=38,orientation='horizontal',color='#7DABBF',ec='white',lw=.25)
    top.tick_params(labelbottom=False);right.tick_params(labelleft=False);top.set_ylabel('Designs');right.set_xlabel('Designs');top.yaxis.set_major_locator(MaxNLocator(3));right.xaxis.set_major_locator(MaxNLocator(2))
    on=int(np.sum((abs(x)<=1e-7)|(abs(y)<=1e-5)));fig.suptitle(f'{len(rr):,} unique feasible designs  |  On coordinate axes: {on:,} ({100*on/len(rr):.1f}%)',fontsize=10,fontweight='bold')
    manifest['equity_audit']={'total':len(rr),'lower_left':int(hidden.sum()),'on_axes':on,'jitter':False}
    finish(fig,15,'equity_designs')

def fig16():
    M=json.loads((SOURCE/'round2_mechanisms.json').read_text(encoding='utf-8'));fig,axs=plt.subplots(2,3,figsize=(8.5,6),layout='constrained',gridspec_kw={'height_ratios':[1.2,1]})
    for j,ci in enumerate(CIS):
        rows=[r for r in M['governance'] if r['case_id']==ci];ax=axs[0,j];xx=np.array([-r['profit_gap']/1000 for r in rows]);yy=np.array([r['CS_gap']/1000 for r in rows]);extent=max(abs(xx).max(),yy.max())*1.12
        for level in [0,1000,2000,3000]:
            vx=np.array([-extent,extent*.04]);vy=level-vx;ax.plot(vx,vy,c='#D1D9DF',lw=.6,ls='--',zorder=0)
        zoom=ax.inset_axes([.43,.22,.53,.34]);zoom.set_facecolor('#FAFCFD')
        zoom.tick_params(labelsize=8,pad=1,length=2)
        # Trajectories identify road intensity within each income scenario without moving any observation.
        for inc,mk,ls in [('reference','o',':'),('uniform','D','--'),('polarized','^','-')]:
            ix=sorted([i for i,r in enumerate(rows) if r['income']==inc],key=lambda i:rows[i]['intensity'])
            ax.plot(xx[ix],yy[ix],c=IC[inc],lw=.65,ls=ls,alpha=.65,zorder=1)
            ax.scatter(xx[ix],yy[ix],ec=IC[inc],fc='white' if inc!='polarized' else IC[inc],marker=mk,s=17,lw=.85,zorder=3,alpha=.85)
            zoom.plot(xx[ix],yy[ix],c=IC[inc],lw=.65,ls=ls,alpha=.7)
            zoom.scatter(xx[ix],yy[ix],ec=IC[inc],fc='white' if inc!='polarized' else IC[inc],marker=mk,s=15,lw=.75,zorder=3)
            if ix:
                i=ix[-1];zoom.annotate(f'{rows[i]["intensity"]:g}',(xx[i],yy[i]),xytext=(4,-6),textcoords='offset points',fontsize=8,color=IC[inc])
        r=max(rows,key=lambda r:r['welfare_gap']);mx=-r['profit_gap']/1000;my=r['CS_gap']/1000
        ax.scatter(mx,my,s=85,facecolor='none',edgecolor=INK,lw=.85,zorder=5)
        ax.set(xlim=(-extent,extent*.04),ylim=(-extent*.04,extent),xlabel=r'$\Delta\Pi$ (CNY k)',ylabel=r'$\Delta U$ (CNY k)' if j==0 else '');title(ax,chr(97+j),ci+' governance tradeoff');grid(ax,axis='both');ax.xaxis.set_major_locator(MaxNLocator(4));ax.yaxis.set_major_locator(MaxNLocator(4))
        zoom.set(xlim=(xx.min()-.12*np.ptp(xx),xx.max()+.12*np.ptp(xx)),ylim=(yy.min()-.15*np.ptp(yy),yy.max()+.15*np.ptp(yy)))
        zoom.xaxis.set_major_locator(MaxNLocator(2));zoom.yaxis.set_major_locator(MaxNLocator(2));zoom.grid(color=GRID,lw=.5)
        zoom.set_title('Detail',fontsize=8,pad=3,fontweight='normal')
        ax.text(.04,.025,f'Ring: largest welfare gap\n{r["income"].capitalize()}, road {r["intensity"]:g}',transform=ax.transAxes,fontsize=8,bbox=dict(fc='white',ec='none',alpha=.9))
        bx=axs[1,j];src.waterfall(bx,[r['CS_gap']/1000,r['revenue_change']/1000,-r['cost_change']/1000,None],[r'$\Delta U$',r'$\Delta R$',r'$-\Delta C$',r'$\Delta W$'],{3},[COL['U'],PART[0],'#009E73']);bx.set_ylabel('CNY thousand/day' if j==0 else '');title(bx,chr(100+j),'Largest-gap accounting');grid(bx,axis='y');bx.tick_params(axis='x',rotation=0)
    fig.legend(handles=[Line2D([],[],c=IC[inc],marker=mk,ls=ls,mfc='white' if inc!='polarized' else IC[inc],label=inc.capitalize()) for inc,mk,ls in [('reference','o',':'),('uniform','D','--'),('polarized','^','-')]],loc='outside lower center',ncols=3,frameon=False)
    finish(fig,16,'governance')

def contact():
    nums=[n for n in range(4,18) if str(n) in manifest];cols=3;rows=(len(nums)+cols-1)//cols;sheet=Image.new('RGB',(cols*600,rows*600),'#E9EDF0')
    for i,n in enumerate(nums):
        d=fitz.open(P/manifest[str(n)]['pdf']);pix=d[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((580,550));x=(i%3)*600+(600-im.width)//2;y=(i//3)*600+35;sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text(((i%3)*600+15,(i//3)*600+10),f'Figure {n}',fill=INK)
    sheet.save(P/'新版图总览.png')

if __name__=='__main__':
    if (P/'manifest.json').exists():manifest.update(json.loads((P/'manifest.json').read_text(encoding='utf-8')))
    chosen={int(v) for v in sys.argv[1:]} if len(sys.argv)>1 else set(range(4,18))
    for f in [fig04,fig05,fig06,fig07,fig08,fig09,fig10,fig11,fig12,fig13,fig14,fig15,fig16,fig17]:
        if int(f.__name__[3:]) not in chosen:continue
        print(f.__name__,flush=True);f()
    manifest['style']={'text_font':'Arial','math_font':'Computer Modern','data_source':str(SOURCE),'dpi':300}
    (P/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    contact()
