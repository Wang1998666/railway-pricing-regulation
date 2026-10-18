"""Collect independent joint audits and exact non-improvement certificates."""
import json,hashlib,time
from concurrent.futures import ProcessPoolExecutor
from model import ROOT,dump
from run_round5 import engine
from local_review_audit import audit
def check(item):
    state,r=item;m=engine(state['job']);report=audit(r,engine=m);return dict(report,state=state['key'],evidence='independent_full_evaluation')
def main():
    reports=[];todo=[];start=time.perf_counter()
    for path in (ROOT/'states').glob('*.json'):
        s=json.loads(path.read_text(encoding='utf-8'))
        for r in s['records']:
            if r['policy'] not in ['P3','P4','P3-sb'] or not r['feasible']:continue
            if r['meta'].get('certificate'):
                reports.append(dict(state=s['key'],case_id=r['case_id'],policy=r['policy'],objective=r['objective'],spec=r['spec'],stable=True,evaluated=0,evidence='global_finite_menu_certificate',certificate_gap=r['meta']['certificate_gap']))
            elif r['meta'].get('joint_audit',{}).get('stable'):
                reports.append(dict(r['meta']['joint_audit'],state=s['key'],evidence='independent_joint_audit_at_final_design'))
            else:todo.append((s,r))
    if todo:
        with ProcessPoolExecutor(max_workers=6) as pool:reports+=list(pool.map(check,todo))
    out=dict(unique_feasible_design_objectives=len(reports),checked_candidates=sum(r['evaluated'] for r in reports),global_nonimprovement_certificates=sum(r['evidence']=='global_finite_menu_certificate' for r in reports),reports=reports,failures=[r for r in reports if not r['stable']],seconds=time.perf_counter()-start,program_sha256=hashlib.sha256((ROOT/'local_review_audit.py').read_bytes()).hexdigest(),solver_sha256=hashlib.sha256((ROOT/'model.py').read_bytes()).hexdigest());dump(ROOT/'local_audit.json',out);assert not out['failures'];print('audit evidence',len(reports),'actual candidates',out['checked_candidates'])
if __name__=='__main__':main()
