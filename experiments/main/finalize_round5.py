"""English response, reproducibility notes and final artifact integrity."""
import json,hashlib,platform,sys,re
from pathlib import Path
import numpy as np,scipy,matplotlib,fitz
import coptpy
from model import ROOT,dump
from analyze import groups,record
P=ROOT.parent;BK=P/'archive/before_round5_20261015'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def f(x,d=1):return f'{x:,.{d}f}'
def sl(v,d=1):return '/'.join(f(x,d) for x in v)
def main():
    R=read(ROOT/'round5_analysis.json');V=read(ROOT/'verification.json');AU=read(ROOT/'local_audit.json');D=read(ROOT/'round3_analysis.json');CL=read(ROOT/'reference_closure.json');QA=read(ROOT/'pdf_qa.json');DK=read(ROOT/'domain_key_verification.json');assert V['passed'] and DK['passed'] and CL['central_known_dominance_closed'] and not AU['failures'] and not QA['unresolved_reference_pages']
    refs={ci:next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none') for ci in ['HN','WC','JX']};jx=record(refs['JX'],'P3','welfare');kp=record(refs['JX'],'P4','welfare');assert jx['welfare']>=780218.69169-1e-5
    # Author-preserved map, original TikZ workflow, and Fig. 4(a).
    preserved={}
    for name in ['case_fig03.pdf','case_fig05.pdf','case_fig05.tex']:
        assert sha(P/'Fig'/name)==sha(BK/'Fig'/name),name;preserved[name]=sha(P/'Fig'/name)
    old=fitz.open(BK/'Fig/round3_calibration.pdf');new=fitz.open(P/'Fig/round3_calibration.pdf');clip=fitz.Rect(0,0,old[0].rect.width,220);assert old[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,alpha=False).samples==new[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,alpha=False).samples;preserved['Fig4a_pixels_equal']=True
    tex=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8');prior=(BK/'TRA-20261014-V3.tex').read_text(encoding='utf-8');core=lambda s:s[s.index(r'\section{Literature review}'):s.index(r'\clearpage'+'\n'+r'\section{Case study}')];assert core(tex)==core(prior),'sections 2--3 changed';case=tex[tex.index(r'\section{Case study}'):];assert r'\begin{equation}' not in case and r'\begin{longtable}' not in case and 'Archived 12306 responses' in case and '616.4' not in case
    # Refresh the reference certificate extract using the final reference set.
    exact=[]
    for ci in ['HN','WC']:
        rr=[]
        for r in refs[ci]['records']:
            if r['policy']=='P0':continue
            assert r['meta'].get('certificate');rr.append(dict(policy=r['policy'],objective=r['objective'],certificate=True,relaxed_master_upper=r['meta']['upper_bound'],gap=r['meta']['certificate_gap'],record=r))
        exact.append(dict(case_id=ci,results=rr))
    dump(ROOT/'exact_period_benchmark.json',dict(cases=exact,source='round5 final central records'))
    sr=R['strict'];caps=[r for r in R['tradeoffs'] if r['lever']=='Tighter cap 1.10'];mainrecords=sum(len(g['records']) for exp in (ROOT/'runs').iterdir() if exp.is_dir() for g in groups(exp.name));cc=sum(len(g['records']) for g in read(ROOT/'constant_cost_grid.json')['groups']);ak=sum(len(g['records']) for g in read(ROOT/'active_period_K.json'))
    text=f'''# Response to the fifth review of Section 4

This response concerns `Case_Study_Review_V3_round5.md`. The revised manuscript is `TRA-20261014-V3.tex/.pdf`; final calculations and reproduction scripts are in `main`. The baseline retains 50% G/D frequency authority and fixed observed K; K withdrawal remains a separate diagnostic. Figure 3, Figure 4(a), and the original TikZ workflow are preserved.

## A1. Remove known-dominated JX results

JX P1–P4 were re-solved for both objectives using the stronger feasible designs, independent starts, and simultaneous fare–frequency moves. Improved reference designs were propagated throughout the sensitivity states and checked for known dominance. The final JX P3 welfare witness is **{f(jx['welfare']/1000)} thousand CNY/day**, and matched P4 welfare is **{f(kp['welfare']/1000)}**; the K increment is **{f((kp['welfare']-jx['welfare'])/1000)}**. Tables 8–10, attribution and K figures, operating counts, welfare shares, and accounting decompositions all use this same reference set. JX results remain search witnesses, not global certificates.

Every discovered JX physical design is also projected into the reference authority and tariff menu and reevaluated there. Reference improvement and propagation repeat until no tested projected design dominates the reference. This closure protects against known-dominated reporting; it does not certify global optimality in JX.

Evidence: `runs/E2/JX_reference_none.json`, `reference_closure.json`, `round3_analysis.json`, `tables/v3_reference.tex`, and `tables/v3_events.tex`.

## A2. Rebuild Figure 16 from current calculations

The upper panel now plots commercial welfare over all six elasticity anchors and three caps, with certified HN/WC optima distinguished from JX search witnesses. Every tornado range is recomputed from the updated experiment records, including elasticity, cap, schedule, fleet and cost assumptions. The caption presents the results directly; it no longer asks readers to reconcile superseded numerical profiles.

Evidence: `commercial_profile.csv`, `Fig/round3_calibration_dependence.pdf`, and `figures_round5.py`.

## A3. Strengthen the solution evidence and revise headline claims

The single-OD engine is applied throughout the HN/WC domains. When the relaxed bound is not attainable, the coupled master imposes daily finance and vulnerable participation directly. Equivalent pooled K allocations, exact integer fleet limits and valid LP reduced-cost screening reduce the search without changing the feasible optimum. There are **{R['certificate_count']} certified state–policy–objective optima**, **{R['infeasibility_count']} certified infeasible problems**, and **{len(R['unresolved_certification'])} problems without a certificate**. The complete ledger reports feasibility, values, available upper bounds and remaining gaps; no time limit is interpreted as proof.

The strict-floor HN/WC profit designs are certified. Their welfare is **{sl([r['welfare_gain']/1000 for r in sr[:2]])} thousand CNY/day**, or **{sl([100*r['benchmark_fraction'] for r in sr[:2]])}%** of the certified reference P3 welfare benchmarks. These recalculated percentages replace the previous headline shares. Common-pricing HN/WC polarization baselines are certified; differentiated pricing uses coordinated multi-start searches. The abstract and conclusion no longer assert a universal reduction in the seat-pricing increment across all three corridors.

The elasticity grid is described as **36 certified HN/WC commercial optima and 18 JX search witnesses**. Other uncertified designs retain explicit search scope.

Evidence: `exact_single_od.py`, `certification_scope.csv`, `round5_analysis.json`, `period_engine_verification.json`, and `local_audit.json`.

An equivalent positive-weight demand kernel accelerates the nested probability calculations. Sixty scenario–period tests have a maximum numerical difference below 0.0000001 CNY; the measured kernel speedup is about twofold. Stable log-sum-exp remains the fallback outside the tested safe exponent range. This changes computational implementation rather than scenarios or search coverage. See `period_kernel_verification.json` and `benchmark_acceleration.py`.

The integer master uses COPT, with feasible MIP starts and an equivalent sorted Pareto filter. Twenty reference and strict-floor checks reproduce independently verified optimum values within 0.01 CNY. The previously difficult polarized HN withdrawal diagnostic is certified in 222.8 seconds in the single-case benchmark; this is not an estimate of whole-batch speed. See `copt_verification.json`, `pareto_kernel_verification.json`, and `copt_benchmark.json`.

## A4. Present the final results without revision narration

Removed the abstract and conclusion sentences about an apparent reversal or an optimization gap, the paragraph comparing earlier WC values, the obsolete Figure 16 caption, and the parallel archived/stronger JX comparisons. Section 4.2 explains once why coordinated moves and exact single-OD checks are required. The discussion addresses the economic results and their scope.

## B. Compare the fare cap with the participation floor

Table 7D now reports profit gains and welfare changes together for every anchor–cap cell. Table 10D compares the central cap, cap 1.10 and floor 1.00 against the same commercial benchmark. At the central anchor, tightening the cap reduces welfare losses by **{sl([100*r['welfare_loss_reduction'] for r in caps])}%** and retains **{sl([100*r['profit_retained'] for r in caps])}%** of commercial profit gains in HN/WC/JX. The tighter cap still leaves welfare below P0; strict HN/WC participation protection instead yields positive welfare while retaining **{sl([100*r['profit_retained'] for r in sr[:2]])}%** of the central profit gains. The text states that discrete fares and departures make a smooth elasticity threshold ill-defined.

Evidence: `cap_floor_tradeoff.csv`, Tables 7D/10D, the abstract, Section 4.7 and the conclusion.

## C. Correct the small accuracy items

1. Restored **12306** as the China Railway platform name.
2. Applied thousands separators consistently to case-study prose and numeric tables.
3. Figure 4(b) now uses plain major log ticks and suppresses minor scientific-notation labels. Figure 4(c) retains separated endpoint labels.
4. Figure 14 uses a visible lowest density color, with the design library and quadrant counts recomputed from the final records. Existing figure layouts are retained while affected numerical content is updated.

## Validation and deliverables

- Independently reconstructed **{mainrecords} main records**, **{cc} constant-cost records**, **{ak} active-period K records**, and 24 road-carbon scenarios.
- Complete-domain cache regressions distinguish all three fare caps, preserve reuse for metadata-only changes, and reject out-of-band or off-menu projected tariffs. The independent verification checks every final saved tariff against its own scenario menu and cap.
- Joint-neighborhood evidence covers **{AU['unique_feasible_design_objectives']}** feasible state–policy–objective designs and **{AU['checked_candidates']:,}** evaluated local candidates; global certificates establish non-improvement for certified optima.
- The manuscript compiles to **{QA['pages']} pages**, with no unresolved references. All pages are rendered under `main/preview` for visual inspection.
- Figure 3, Figure 4(a), the TikZ workflow and Sections 2–3 pass preservation checks. Tables remain ordinary compact tables at 95% text width; case-study numerical explanations do not introduce numbered display equations.
'''
    (P/'REVIEW_RESPONSE_V3_round5_20261015_EN.md').write_text(text,encoding='utf-8')
    readme=f'''# 第五轮实验修订档案

本档案对应 Case_Study_Review_V3_round5.md 和 TRA-20261014-V3.tex/.pdf。基准仍为50% G/D频率可调、观测K固定；撤减K只用于独立诊断。

- 主实验：966组、{mainrecords}条记录；固定成本网格54组、{cc}条；已服务时段K检验6组、{ak}条；碳诊断24条。
- 按完整物理模型和决策域去重后求解{R['states']}个状态，键包含票价上限、菜单、班次上下界、车底周期和约束参数。独立标量复核见verification.json，联合邻域证据见local_audit.json。
- 独立票价区间检查拦截了遗漏fare_cap的早期去重映射，手稿生成前已补全键并补算不同上限的情景。有效计算仅在完整域匹配后复用，迁移校验见domain_key_migration.json；被拦截的中间档案见archive_before_domain_key_fix_20261015。
- HN/WC逐状态逐政策求解；{R['certificate_count']}个最优证书、{R['infeasibility_count']}个不可行证书、{len(R['unresolved_certification'])}个未获证书的问题。完整范围和界限见 certification_scope.csv；禁止将限时求解写成不可行或最优。
- 界限表将COPT的有限数值无穷哨兵识别为unavailable，不将其写成有意义的有限上界；states保留原始求解输出以供追溯。
- JX和分席票价采用多起点及联合票价—班次搜索，不宣称全局最优。所有发现的JX物理设计投影至基准权限和票价菜单后重新评估，改善的基准再回传敏感性域，直至交叉检查稳定。记录见reference_closure.json；此检查消除已知支配，并非全局最优证明。
- 实现加速包括8进程并行、物理状态去重、时段缓存、等价K分配剔除、整数车底界及LP约化成本筛选。period_kernel.py的等价概率内核在60个情景—时段组合中通过误差校验，内核基准约快2倍；超出保守指数范围时退回稳定log-sum-exp计算。基准测试见benchmark_acceleration.py，不能将内核速度视为整批实验速度。
- 整数主问题使用COPT，并提供可行MIP起点；LP筛选使用HiGHS。COPT通过20项基准与严格保留率对照校验，等价Pareto筛选通过200组随机及重复值校验。困难HN诊断在单案例测试中用222.8秒获得最优证书；这不是整批耗时预测。证据见copt_verification.json、pareto_kernel_verification.json及copt_benchmark.json。
- commercial_profile.csv：54个弹性—上限状态的商业利润、福利与证书；cap_floor_tradeoff.csv：同一商业基准下的上限与严格参与率权衡。
- historical_baseline保存原求解器；before_round5备份位于 ../archive/before_round5_20261015。旧轮档案不作本轮最终结果使用。
- 从旧包继承、且本轮流程不使用的检查日志和结果已移入historical_baseline/inherited_results；本轮结论以round5_manifest.json、round5_analysis.json、certification_scope.csv和delivery_checks.json为准。
- layout_preview和design_preview仅用于版式测试，沿用继承数值；preview是最终PDF的逐页渲染。论文数值应以最终runs、states和分析CSV为准。

复现（本目录，Python 3.13、有效的本机COPT许可及LaTeX工具）：

```powershell
python verify_domain_keys.py
python run_round5.py --workers 8
python verify_period_engines.py
python verify_copt_backend.py
python verify_pareto_kernel.py
python finish_round5.py
```

run_round5.py支持状态缓存；源指纹或决策域变化会触发重算。等价前驱求解证书的来源保留在source_hashes_at_solve；未证问题重新求解。finish_round5.py依次完成参考设计回传、重点证书、独立复核、分析、绘图、正文生成、编译与交付检查。

图3、图4(a)、原TikZ流程图及第2—3节保留检查见 delivery_checks.json。逐项英文修复说明见 ../REVIEW_RESPONSE_V3_round5_20261015_EN.md。
''';(ROOT/'README_CN.md').write_text(readme,encoding='utf-8')
    dump(ROOT/'environment.json',dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,pymupdf=fitz.VersionBind,copt=str(coptpy.COPT.VERSION_MAJOR)+'.'+str(coptpy.COPT.VERSION_MINOR)+'.'+str(coptpy.COPT.VERSION_TECHNICAL),workers=8))
    dump(ROOT/'delivery_checks.json',dict(passed=True,preserved=preserved,sections_2_3_equal=True,case_numbered_equations=False,case_longtable=False,pages=QA['pages'],records=mainrecords,unresolved_references=QA['unresolved_reference_pages']))
    paths=[P/'TRA-20261014-V3.tex',P/'TRA-20261014-V3.pdf',P/'REVIEW_RESPONSE_V3_round5_20261015_EN.md']+list((P/'tables').glob('v3_*.tex'))+list((P/'Fig').glob('round3_*.pdf'))+[P/'Fig/case_fig03.pdf',P/'Fig/case_fig05.pdf',P/'Fig/case_fig05.tex']+[p for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() in ['.py','.json','.csv','.md'] and p.name!='artifact_manifest.json'];dump(ROOT/'artifact_manifest.json',dict(files={str(p.relative_to(P)):sha(p) for p in paths}));print('Delivery integrity passed; English response written')
if __name__=='__main__':main()
