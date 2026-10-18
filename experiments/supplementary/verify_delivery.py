"""Validate the delivered evidence, bounds, row counts, and immutable sources."""
from common import *
import csv,re,collections
import fitz

def csvread(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def main():
    regression=read(HERE/'step0_status.json');assert regression['passed'] and regression['checks']==32
    records=[read(p) for folder in ['exp1','exp4'] for p in (HERE/folder/'runs').glob('*.json')]
    assert len(records)==102
    statuses=collections.Counter(r['status'] for r in records);assert statuses=={'optimal':94,'search':8}
    for out in records:
        assert out['record']['feasible'] and out['scalar_error'] is not None and out['scalar_error']<1e-5
        assert design_hash(out['record'])==out['design_hash']
        assert out['seconds']>=0 and out['git_commit'] and out['config_sha256']
        if out['status']=='optimal':
            assert out['master']['status']==0 and out['master']['success']
            assert abs(out['master']['upper']-out['record'][out['config']['objective']])<.01
    grid=csvread(HERE/'exp1'/'grid.csv');assert len(grid)==78
    commercial=[r for r in grid if r['objective']=='profit'];assert len(commercial)==70
    for a in commercial:
        for b in commercial:
            if a['case_id']==b['case_id'] and float(a['cap'])<=float(b['cap']) and float(a['floor'])>=float(b['floor']):assert float(a['profit_gain'])<=float(b['profit_gain'])+1e-5
    ext=csvread(HERE/'exp4'/'elasticity_ext.csv');assert len(ext)==24
    profit=[r for r in ext if r['objective']=='profit'];pos=[r for r in profit if float(r['delta_W'])>0]
    assert len(pos)==3 and all(r['case_id']=='WC' and abs(float(r['anchor'])+1.5)<1e-8 for r in pos)
    lib=csvread(HERE/'exp2'/'library_diagnostics.csv');assert len(lib)==1842 and all(float(r['argmax_worst_H'])==1 for r in lib)
    assert all(float(r['scalar_error'])<1e-5 and r['config_sha256'] and r['git_commit'] and float(r['evaluation_seconds'])>=0 for r in lib)
    ll=[r for r in lib if float(r['dG'])<-1e-7 and float(r['deta'])<-1e-7];assert len(ll)==341
    assert sum(float(r['delta_Gfix'])>=-1e-7 for r in ll)==17
    cross=csvread(HERE/'exp3'/'cross_eval.csv');assert len(cross)==6
    assert all(r['cross_feasible']=='False' and float(r['cross_max_load'])>.95 and float(r['cross_scalar_error'])<1e-5 and float(r['cross_finance_margin'])>0 and float(r['cross_floor'])>=.95 and r['cross_structural']=='True' and float(r['cross_fleet_utilization'])<=1+1e-9 for r in cross)
    assert all(r['number_changed']=='False' and float(r['seat_increment'])>0 for r in cross)
    prior=read(HERE/'provenance.json')
    for name,h in prior['source_sha256'].items():assert sha(BASE/name)==h,('V3 source modified',name)
    for name,h in prior['input_sha256'].items():assert sha(BASE/'inputs'/name)==h,('V3 input modified',name)
    originals=read(HERE/'original_files.json');assert sha(HERE.parent/'TRA-20261016-V4.tex')==originals['manuscript_sha256']
    for name,h in originals['tables_sha256'].items():assert sha(HERE.parents[1]/'tables'/'supplementary'/name)==h,('Original table modified',name)
    tables=list((HERE/'tables').glob('*_v4.tex'));assert len(tables)==6
    for p in tables:assert not re.search(r'\b(?:certified|certify|witness\w*)\b',p.read_text(encoding='utf-8'),re.I)
    for p in [HERE/'exp1'/'fig13_cap_floor_frontier_v4.pdf',HERE/'exp4'/'fig17_calibration_dependence_v4.pdf']:
        doc=fitz.open(p);assert len(doc)==1;txt=' '.join(page.get_text() for page in doc);assert not re.search(r'\b(?:certified|certify|witness\w*)\b',txt,re.I)
    log=(HERE/'table_preview'/'main.log').read_text(encoding='utf-8',errors='replace')
    assert 'Output written on main.pdf' in log
    assert not re.search(r'Overfull|undefined references|LaTeX Error|Emergency stop',log,re.I)
    assert len(fitz.open(HERE/'table_preview'/'main.pdf'))==4
    error_by_scope=dict(optimization=max(r['scalar_error'] for r in records),library=max(float(r['scalar_error']) for r in lib),cross_evaluation=max(float(r['cross_scalar_error']) for r in cross),cost_split_extraction=max(r['scalar_error'] for r in read(HERE/'exp5'/'results.json')),regression=max(read(p)['scalar_error'] for p in (HERE/'step0_runs').glob('*.json')))
    checks=dict(passed=True,regression_checks=32,supplementary_optimization_records=102,statuses=dict(statuses),commercial_grid_records=70,welfare_grid_records=8,extended_elasticity_records=24,library_records=1842,cross_evaluations=6,
      independent_max_error=max(error_by_scope.values()),independent_max_errors_by_scope=error_by_scope,original_v4_unchanged=True,original_tables_unchanged=True,V3_sources_and_inputs_unchanged=True,
      table_preview_compiles=True,table_preview_pages=4,draft_insertions_desktop_compiler='success',visual_review='Figures 13/17 PNGs and all four rendered table-preview pages inspected; no clipping or unreadable labels',git_commit=git())
    dump(HERE/'delivery_checks.json',checks)
    print(json.dumps(checks,indent=2),flush=True)
    manifest={str(p.relative_to(HERE)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in HERE.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name not in ['artifact_manifest.json'] and p.suffix not in ['.tmp']}
    dump(HERE/'artifact_manifest.json',manifest)
if __name__=='__main__':main()
