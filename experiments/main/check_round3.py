"""Independent checks of promoted accounting and all extra saved designs."""
import json,hashlib,re
import numpy as np
import fitz
from model import ROOT,Model,dump
from calibration import prepare
from analyze import groups,record
from verify import scalar
from carbon_sensitivity import factors,scalar_carbon
from analyze_round3 import channels
P=ROOT.parent
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    C={ci:read(f'inputs/{ci}.json') for ci in ['HN','WC','JX']};V=read('verification.json');LA=read('local_audit.json');CA=read('calibration_checks.json');D=read('round3_analysis.json')
    assert V['passed'] and not LA['failures'] and CA['passed'];extra=0;errors=[];counter=[];improvements=[]
    for g in read('constant_cost_grid.json')['groups']:
        s=g['job']['spec'];m=Model(C[g['job']['case']],spec=s);factor=.88/s['ref_load']
        for p in m.c['products']:p['run_cost']*=factor;p['fixed_cost']*=factor
        b=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',s)
        for r in g['records']:
            z=scalar(m.c,np.array(r['N']),np.array(r['phi']),'reference','none',s);err=max(abs(z['profit']-r['profit']),abs(z['U']-b['U']+z['profit']-b['profit']-r['welfare']));assert err<1e-5;extra+=1;errors.append(err)
    for g in read('active_period_K.json'):
        for r in g['records']:
            s=r['spec'];m=Model(C[g['case_id']],spec=s);b=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',s);z=scalar(m.c,np.array(r['N']),np.array(r['phi']),'reference','none',s);err=max(abs(z['profit']-r['profit']),abs(z['U']-b['U']+z['profit']-b['profit']-r['welfare']));assert err<1e-5;extra+=1;errors.append(err)
    certs=0
    for g in read('exact_period_benchmark.json')['cases']:
        m=Model(C[g['case_id']]);b=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',{})
        for e in g['results']:
            r=e['record'];assert e['certificate'] and abs(e['gap'])<1e-5;z=scalar(m.c,np.array(r['N']),np.array(r['phi']),'reference','none',{});err=max(abs(z['profit']-r['profit']),abs(z['U']-b['U']+z['profit']-b['profit']-r['welfare']));assert err<1e-5;extra+=1;certs+=1;errors.append(err)
    for x in read('carbon_sensitivity.json')['records']:
        r=x['record'];s=r['spec'];m=Model(C[x['case_id']],'reference',r['electric'],s);ef=factors(m,x['baseline_ev']);z,co=scalar_carbon(m.c,np.array(r['N']),np.array(r['phi']),'reference',m.electric,s,ef);b,bc=scalar_carbon(m.c,m.N0,np.ones((m.S,4,3)),'reference',m.electric,s,ef);w=z['U']-b['U']+z['profit']-b['profit'];aug=w-x['price']*(co-bc)/1000;err=max(abs(w-x['railway_welfare']),abs(aug-x['augmented_welfare']),abs((co-bc)/1000-x['road_CO2_change_tonnes']));assert err<1e-5;extra+=1;errors.append(err)
    for ci in C:
        m=Model(C[ci]);g=next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none')
        for obj in ['profit','welfare']:
            p=record(g,'P3',obj);r=record(g,'P4',obj);ch=channels(m,p,r);assert abs(sum(ch[k] for k in ['fare','schedule','availability','participation'])-ch['total'])<1e-6
            n=np.array(p['N']);n[m.candidate]=np.array(r['N'])[m.candidate];ph=np.array(p['phi']);ph[m.tier=='K']=1.;cf=m.record(n,ph,obj,'P4');z=scalar(m.c,n,np.array(cf['phi']),'reference','none',{});assert abs(z['profit']-cf['profit'])<1e-5;counter.append(cf)
    for path in (ROOT/'runs').glob('E*/*.json'):
        old=P/'experiments_v3_round2/runs'/path.parent.name/path.name
        if not old.exists():continue
        g=json.loads(path.read_text(encoding='utf-8'));h=json.loads(old.read_text(encoding='utf-8'));lookup={(r['policy'],r['objective']):r for r in h['records']}
        for r in g['records']:
            b=lookup[(r['policy'],r['objective'])]
            if abs(r['objective_value']-b['objective_value'])>1e-5:
                assert r['objective_value']>=b['objective_value']-1e-5
                improvements.append(dict(file=str(path.relative_to(ROOT)),policy=r['policy'],objective=r['objective'],old_value=b['objective_value'],new_value=r['objective_value'],gain=r['objective_value']-b['objective_value']))
    negative=sum(record(g,'P3','profit')['welfare']<0 for g in groups('E13'));assert negative==24
    # Exact preservation of the exempted assets.
    assert sha(P/'fig/case_fig03.pdf')==sha(P/'archive/before_round3_20261015/fig/case_fig03.pdf')
    old=fitz.open(P/'archive/before_round3_20261015/fig/case_fig04.pdf');new=fitz.open(P/'fig/round3_calibration.pdf');clip=fitz.Rect(0,0,old[0].rect.width,220)
    a=old[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,alpha=False);b=new[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,alpha=False);assert a.samples==b.samples
    tex=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8');case=tex.split(r'\section{Case study}',1)[1].split(r'\section{Discussion and conclusion}',1)[0]
    assert r'\appendix' not in tex and case.count(r'\subsection{')==7 and '\t' not in case
    assert not re.search(r'\\(?:begin\{(?:equation|align)|\[)',case)
    for name in re.findall(r'\\input\{tables/([^}]+)\}',case):
        t=(P/'tables'/name).read_text(encoding='utf-8');assert r'\begin{longtable}' not in t and r'\begin{minipage}{.95\textwidth}' in t
    abstract=tex.split(r'\begin{abstract}',1)[1].split(r'\end{abstract}',1)[0];assert len(abstract.split())<=200
    prohibited=['Appendix A','avoiding a blanket','rather than a mechanical failure','without a duplicate','grid05','mu sc low','slope75','P0P','uniform x0.05']
    assert not any(x in case for x in prohibited)
    dump(ROOT/'round3_counterfactuals.json',counter);dump(ROOT/'baseline_witness_improvements.json',improvements)
    dump(ROOT/'round3_checks.json',dict(passed=True,main_saved_records=V['records'],extra_saved_records=extra,counterfactual_records=len(counter),independently_checked_records=V['records']+extra+len(counter),exact_central_reference_certificates=certs,extra_maximum_error=max(errors),baseline_witness_improvements=len(improvements),negative_commercial_welfare_cap_anchor_states=negative,map3_sha256=sha(P/'fig/case_fig03.pdf'),fig4a_pixel_identical=True,abstract_words=len(abstract.split()),subsections=7))
    print('ROUND3 checks passed;',V['records']+extra+len(counter),'saved records;',len(improvements),'improved baseline witnesses')
if __name__=='__main__':main()
