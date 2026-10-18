"""Single-OD period enumeration with hard finance/retention and activation costs."""
import itertools,time,bisect,warnings
import numpy as np
from scipy.special import logsumexp,expit
from scipy.optimize import linprog,Bounds,LinearConstraint
from copt_backend import milp
from pareto_kernel import skyline
from scipy.sparse import lil_matrix,vstack
from model import Model
def skyline_reference(a,obj):
    # Exact dominance in profit, welfare and vulnerable participation for fixed N.
    score=a[:,6] if obj=='profit' else a[:,6]+a[:,7]
    order=np.lexsort((-a[:,8],-score,-a[:,6]));keep=[];front=[]
    for idx in order:
        l=a[idx,8];s=score[idx]
        if any(x>=l and y>=s for x,y in front):continue
        keep.append(idx);front=[(x,y) for x,y in front if not(x<=l and y<=s)];front.append((l,s))
    return a[keep]
class Exact:
    def __init__(self,m,seeds=()):
        assert m.W==1 and m.S==4;self.m=m;self.grid=np.round(np.arange(.8,m.fare_cap+.0001,m.spec.get('step',.025)),8)
        self.gd=np.flatnonzero(m.adjustable);assert list(self.gd)==[0,1];self.cache={};self.seeds=list(seeds);self.best_seed=None
        self.ph_pairs=np.array(list(itertools.product(self.grid,self.grid)));self.baseU=[];self.checks=0
        for h in range(4):self.baseU.append(self.period(h,m.N0[:,h][None],np.array([[1.,1.]]))[0,7])
    def period(self,h,counts,fares):
        m=self.m;n=np.repeat(counts,len(fares),axis=0);f=np.tile(fares,(len(counts),1));size=len(n);ph=np.ones((size,4,3));ph[:,:2,:]=f[:,:,None];eff=n.copy();eff[:,2]+=n[:,3];eff[:,3]=0
        from period_kernel import period
        fast=period(m,h,n,ph)
        if fast is not None:
            var=fast[:,0]-(n*m.run_cost).sum(axis=1);U=fast[:,1].copy()
            if hasattr(m,'carbon_ef'):U-=m.carbon_price*fast[:,4]/1000
            paths=n@m.route;service=n@m.serve[:,0];ok=(fast[:,3]<=m.lam+1e-9)&np.all(paths<=m.cap[h]+1e-8,axis=1)&(service>=m.odfloor[0,h]-1e-8);self.checks+=size
            return np.column_stack([n,f,var/1000,U/1000,fast[:,2],ok])
        sc=15*[3,8,3,10][h]/np.maximum(eff,1)
        if m.displacement_cap is not None:sc=np.minimum(sc,m.displacement_cap)
        v=m.fixed_rail[0,:,h][None]-m.beta[None,:,0,None,None]*m.fare[0,None,:,:]*ph[:,None]-m.beta[None,:,4,None,None]*sc[:,None,:,None]
        valid=(eff[:,None,:,None]>0)&m.serve[:,0][None,None,:,None]&(m.seats[None,None]>0);v=np.where(valid,v,-1e100)
        ls=logsumexp(v/m.mu_sc,axis=-1)*m.mu_sc;rail=logsumexp(ls/m.mu_pr,axis=-1)*m.mu_pr;mode=np.concatenate([rail[:,:,None],np.broadcast_to(m.road_logs[0,:,h],(size,3,2))],axis=-1);travel=logsumexp(mode/.75,axis=-1)*.75;part=expit(travel)
        qr=m.qbar[0,:,h][None,:,None,None]*part[:,:,None,None]*np.exp((rail-travel)/.75)[:,:,None,None]*np.exp((ls-rail[:,:,None])/m.mu_pr)[:,:,:,None]*np.where(valid,np.exp((v-ls[:,:,:,None])/m.mu_sc),0.)
        rev=(qr*m.fare[0,None,None]*ph[:,None]).sum(axis=(1,2,3));var=rev-(n*m.run_cost).sum(axis=1);U=(m.qbar[0,:,h]*np.logaddexp(0,travel)/m.beta[:,0]).sum(axis=1);L=m.qbar[0,2,h]*part[:,2]
        if hasattr(m,'carbon_ef'):
            shared_ef=m.road_probs[0,:,h]@m.carbon_ef[1:];Q=m.qbar[0,:,h]*part
            co2=(Q*m.c['road_km'][0]*(np.exp((m.road_logs[0,:,h,1]-travel)/.75)*m.carbon_ef[0]+np.exp((m.road_logs[0,:,h,0]-travel)/.75)*shared_ef)).sum(axis=1)
            U-=m.carbon_price*co2/1000
        loads=qr.sum(axis=1)+m.c['background_fraction']*m.N0[:,h,None]*m.seats;den=eff[:,:,None]*m.seats[None];lf=np.divide(loads,den,out=np.zeros_like(loads),where=den>0).max(axis=(1,2));paths=n@m.route;service=n@m.serve[:,0]
        ok=(lf<=m.lam+1e-9)&np.all(paths<=m.cap[h]+1e-8,axis=1)&(service>=m.odfloor[0,h]-1e-8)
        out=np.column_stack([n,f,var/1000,U/1000,L,ok]);self.checks+=size;return out
    def columns(self,policy,obj,full=False):
        if not full and (policy,obj) in self.cache:return self.cache[(policy,obj)]
        m=self.m;options=[];other=[];p3=[];p3other=[]
        for h in range(4):
            ranges=[range(int(m.Nmin[s,h]),int(m.Nmax[s,h])+1) for s in range(4)]
            if policy in ['P0','P1']:ranges=[ [int(m.N0[s,h])] for s in range(4)]
            elif policy!='P4':ranges[3]=[0]
            # Parent and added K have identical pooled demand, routes, run cost
            # and cycles. Fill available parent departures before paying an
            # increment commitment; other splits are weakly dominated.
            pooled=policy=='P4' and np.isclose(m.run_cost[2],m.run_cost[3],rtol=0,atol=1e-9) and m.fixed_cost[3]>=0 and np.array_equal(m.route[2],m.route[3]) and np.array_equal(m.serve[2],m.serve[3]) and m.cycle[2]==m.cycle[3]
            if pooled:
                ks=[(k,0) for k in ranges[2]]+[(max(ranges[2]),e) for e in ranges[3] if e>0];counts=np.array([(*gd,*k) for gd in itertools.product(*ranges[:2]) for k in ks],float)
            else:counts=np.array(list(itertools.product(*ranges)),float)
            fare=np.array([[1.,1.]]) if policy in ['P0','P2'] else self.ph_pairs;rows=[];orr=[];r3=[];o3=[]
            for start in range(0,len(counts),max(1,4096//len(fare))):
                c=counts[start:start+max(1,4096//len(fare))];a=self.period(h,c,fare).reshape(len(c),len(fare),10)
                for block in a:
                    b=block[block[:,9]>0]
                    if not len(b):continue
                    b=b.copy();b[:,7]-=self.baseU[h]
                    if full:rows.append(skyline(b,obj))
                    else:
                        one=b[[np.argmax(b[:,6] if obj=='profit' else b[:,6]+b[:,7])]];two=b[[np.argmax(b[:,6]+b[:,7] if obj=='profit' else b[:,6])]];rows.append(one);orr.append(two)
                        if policy=='P4' and b[0,3]==0:r3.append(one);o3.append(two)
            options.append(np.concatenate(rows) if rows else np.zeros((0,10)))
            if not full:other.append(np.concatenate(orr) if orr else np.zeros((0,10)));p3.append(np.concatenate(r3) if r3 else np.zeros((0,10)));p3other.append(np.concatenate(o3) if o3 else np.zeros((0,10)))
        if not full:
            self.cache[(policy,obj)]=options;self.cache[(policy,'welfare' if obj=='profit' else 'profit')]=other
            if policy=='P4':self.cache[('P3',obj)]=p3;self.cache[('P3','welfare' if obj=='profit' else 'profit')]=p3other
        return options
    def lower_bound(self,policy,obj):
        m=self.m;best=-np.inf;step=m.spec.get('step',.025);self.best_seed=None
        for r in self.seeds+[dict(N=m.N0,phi=np.ones((4,4,3)))]:
            N=np.clip(np.array(r['N']),m.Nmin,m.Nmax);ph=np.repeat(np.array(r['phi'])[:,:,:1],3,axis=2)
            if policy!='P4':N[m.candidate]=0
            if policy in ['P0','P1']:N=m.N0.copy()
            ph=np.clip(.8+np.round((ph-.8)/step)*step,.8,m.fare_cap);ph[m.tier=='K']=1.
            if policy in ['P0','P2']:ph[:]=1.
            a=m.record(N,ph,obj,policy)
            value=(a[obj]+(m.state_profit if obj=='welfare' else 0))/1000
            if a['feasible'] and value>best:best=value;self.best_seed=a
        return best
    def start_vector(self,options,obj,hard):
        if self.best_seed is None:return None
        m=self.m;N=np.array(self.best_seed['N']);ph=np.array(self.best_seed['phi']);total=N[2]+N[3];N[2]=np.minimum(total,m.Nmax[2]);N[3]=total-N[2];x=np.zeros(sum(len(a) for a in options)+4);offset=0;selected=[]
        for h,a in enumerate(options):
            mask=np.all(abs(a[:,:4]-N[:,h])<1e-8,axis=1)
            if hard:
                fp=np.where(N[:2,h]>0,ph[:2,h,0],1.);t=self.period(h,N[:,h][None],fp[None])[0];mask&=(a[:,6]>=t[6]-1e-8)&(a[:,8]>=t[8]-1e-8)
                if obj=='welfare':mask&=(a[:,6]+a[:,7]>=t[6]+t[7]-self.baseU[h]-1e-8)
            ids=np.flatnonzero(mask)
            if not len(ids):return None
            j=ids[np.argmax(a[ids,6]+(a[ids,7] if obj=='welfare' else 0))];x[offset+j]=1.;selected.append(a[j]);offset+=len(a)
        rows=np.array(selected);x[-4:]=[np.any(rows[:,0]>0),np.any(rows[:,1]>0),np.any(rows[:,2]+rows[:,3]>0),np.any(rows[:,3]>0)];return x
    def master(self,options,obj,hard,time_limit=120,incumbent=-np.inf):
        m=self.m
        if any(not len(x) for x in options):return None
        cols=[(h,r) for h,a in enumerate(options) for r in a];n=len(cols);mat=lil_matrix((4+3+2+2+8,n+4));score=np.zeros(n+4)
        for j,(h,r) in enumerate(cols):
            mat[h,j]=1
            for t,k in [('G',0),('D',1),('K',2)]:mat[4+k,j]=sum(r[s] for s in range(4) if m.tier[s]==t)
            mat[7,j]=r[6];mat[8,j]=r[8];mat[9,j]=r[0];mat[10,j]=r[1]
            flags=[r[0]>0,r[1]>0,r[2]+r[3]>0,r[3]>0]
            for s,flag in enumerate(flags):mat[11+2*s,j]=int(flag);mat[12+2*s,j]=-int(flag)
            score[j]=r[6]+(r[7] if obj=='welfare' else 0.)
        for s in range(4):
            mat[7,n+s]=-m.fixed_cost[s]/1000;score[n+s]=-m.fixed_cost[s]/1000;mat[11+2*s,n+s]=-4;mat[12+2*s,n+s]=1
        lower=[1]*4+[-np.inf]*3+([-m.budget/1000,m.eta_floor*m.ref_vul] if hard else [-np.inf,-np.inf])+[1,1]+[-np.inf]*8
        # One cycle per tier permits exact integer tightening of daily fleets.
        upper=[1]*4+[np.floor(m.fleet[k]/m.cycle[k]+1e-8) for k in range(3)]+[np.inf]*4+[0]*8
        mat=mat.tocsr();lb=np.zeros(n+4);ub=np.ones(n+4)
        # G/D must be served daily; protected K forces its parent commitment.
        lb[n:n+2]=1.
        if m.Nmin[2:].sum()>0:lb[n+2]=1.
        if not any(np.any(a[:,3]>0) for a in options):ub[n+3]=0.
        kept=np.arange(n+4);lp_upper=None;start_vector=self.start_vector(options,obj,hard)
        if start_vector is not None:
            lhs=mat@start_vector
            if np.any(lhs<np.array(lower)-1e-6) or np.any(lhs>np.array(upper)+1e-6):start_vector=None
        if n>1000:
            lo=np.array(lower);hi=np.array(upper);ii=np.flatnonzero(np.isfinite(hi[4:]))+4;jj=np.flatnonzero(np.isfinite(lo[4:]))+4;Au=vstack([mat[ii],-mat[jj]],format='csr');bu=np.r_[hi[ii],-lo[jj]]
            with warnings.catch_warnings():
                warnings.simplefilter('ignore');lp=linprog(-score,A_ub=Au,b_ub=bu,A_eq=mat[:4],b_eq=np.ones(4),bounds=np.column_stack([lb,ub]),method='highs',options={'time_limit':30.,'threads':1,'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
            if lp.status==2:return dict(success=False,status=2,upper=None,columns=n+4,lp_infeasible=True)
            if lp.success:
                lp_upper=-lp.fun
                if np.isfinite(incumbent):
                    gap=max(0.,lp_upper-incumbent);keep=lp.lower.marginals[:n]<=gap+1e-7
                    if start_vector is not None:keep|=start_vector[:n]>.5
                    kept=np.r_[np.flatnonzero(keep),np.arange(n,n+4)]
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');res=milp(-score[kept],integrality=np.ones(len(kept)),bounds=Bounds(lb[kept],ub[kept]),constraints=LinearConstraint(mat[:,kept],lower,upper),options={'mip_rel_gap':0.,'time_limit':time_limit,'threads':1,'mip_start':None if start_vector is None else start_vector[kept]})
        if res.x is None:
            bound=float(res.mip_dual_bound)
            upper=-bound*1000-(m.state_profit if obj=='welfare' else 0.) if np.isfinite(bound) else None
            return dict(success=False,status=int(res.status),upper=upper,columns=n+4,backend=res.backend)
        x=np.zeros(n+4);x[kept]=res.x;N=m.N0.copy();ph=np.ones((4,4,3))
        for j,(h,r) in enumerate(cols):
            if x[j]>.5:N[:,h]=r[:4];ph[:2,h,:]=r[4:6,None]
        record=m.record(N,ph,obj,'P3');upper=-float(res.mip_dual_bound)*1000-(m.state_profit if obj=='welfare' else 0.);gap=upper-record[obj]
        return dict(success=bool(res.success and record['feasible'] and abs(gap)<.01),status=int(res.status),upper=upper,gap=gap,columns=n+4,retained_columns=len(kept),lp_upper=lp_upper,backend=res.backend,record=record)
    def solve(self,policy,obj):
        start=time.perf_counter();options=self.columns(policy,obj);result=self.master(options,obj,False,incumbent=self.lower_bound(policy,obj));hard=False
        if result is None:return None
        if not result['success']:
            options=self.columns(policy,obj,True);result=self.master(options,obj,True,time_limit=180,incumbent=self.lower_bound(policy,obj));hard=True
        if result and 'record' in result:
            r=result['record'];r['policy']=policy;r['meta'].update(exact_single_od=True,certificate=result['success'],upper_bound=result['upper'],certificate_gap=result['gap'],master_columns=result['columns'],retained_columns=result.get('retained_columns'),solver_backend=result.get('backend'),enumerated=self.checks,seconds=time.perf_counter()-start,finance_retention_hard=hard);self.seeds.append(r)
        return result
