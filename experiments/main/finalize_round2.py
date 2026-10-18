"""Finalize auditable results, response and artifact hashes after PDF QA."""
import hashlib,json,platform,re,sys
from pathlib import Path
import numpy as np
from model import ROOT,Model,VERSION,dump
from calibration import prepare
from run_experiments import tasks
from analyze import record,pair_feasible
from verify import scalar

P=ROOT.parent
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def num(x,d=2):return f'{x:,.{d}f}'

def main():
    V=read('verification.json');A=read('review_analysis.json');M=read('round2_mechanisms.json');EL=read('elasticities_round2.json');EX=read('exact_period_benchmark.json');AK=read('active_period_K.json');CO=read('carbon_sensitivity.json');CC=read('constant_cost_grid.json');LA=read('local_audit.json');CA=read('calibration_checks.json');QA=read('pdf_qa.json')
    assert V['passed'] and CA['passed'] and not LA['failures'];assert all(r['certificate'] and r['scalar_error']<1e-5 for c in EX['cases'] for r in c['results']);assert all(r['feasible'] and r['scalar_error']<1e-5 for r in CO['records']);assert all(all(e<1e-5 for e in g['scalar_errors']) for g in AK);assert not QA['unresolved_reference_pages']
    expected=tasks();paths=[ROOT/'runs'/j['experiment']/(j['id']+'.json') for j in expected];assert all(p.exists() for p in paths);assert len(paths)==len(list((ROOT/'runs').glob('E*/*.json')))
    C={ci:read(f'inputs/{ci}.json') for ci in ['HN','WC','JX']};R={ci:read(f'runs/E2/{ci}_reference_none.json') for ci in C};strict=[r for r in M['strict'] if r['objective']=='profit']; exactrecords=[r for c in EX['cases'] for r in c['results']]
    # Recheck extra outputs against the final independent scalar implementation.
    extra_checked=0
    for g in CC['groups']:
        spec=g['job']['spec'];m=Model(C[g['job']['case']],spec=spec);factor=.88/spec['ref_load']
        for p in m.c['products']:p['run_cost']*=factor;p['fixed_cost']*=factor
        base=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',spec)
        for r in g['records']:
            a=scalar(m.c,np.array(r['N']),np.array(r['phi']),'reference','none',spec);assert abs(a['profit']-r['profit'])<1e-5 and abs(a['U']-base['U']+a['profit']-base['profit']-r['welfare'])<1e-5;extra_checked+=1
    for g in AK:
        for r in g['records']:
            c=prepare(C[g['case_id']],r['spec']);n0=np.array([p['N0'] for p in c['products']]);base=scalar(c,n0,np.ones((len(n0),4,3)),'reference','none',r['spec']);a=scalar(c,np.array(r['N']),np.array(r['phi']),'reference','none',r['spec']);assert abs(a['profit']-r['profit'])<1e-5 and abs(a['U']-base['U']+a['profit']-base['profit']-r['welfare'])<1e-5;extra_checked+=1
    for c in EX['cases']:
        raw=prepare(C[c['case_id']],{});n0=np.array([p['N0'] for p in raw['products']]);base=scalar(raw,n0,np.ones((len(n0),4,3)),'reference','none',{})
        for er in c['results']:
            r=er['record'];a=scalar(raw,np.array(r['N']),np.array(r['phi']),'reference','none',{});assert abs(a['profit']-r['profit'])<1e-5 and abs(a['U']-base['U']+a['profit']-base['profit']-r['welfare'])<1e-5;extra_checked+=1
    total=V['records']+extra_checked+len(CO['records'])
    tex=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8');case=tex.split(r'\section{Case study}',1)[1].split(r'\section{Discussion and conclusion}',1)[0]
    assert not re.search(r'\\(?:begin\{(?:equation|align)|\[)',case);assert 'unallocated model' not in tex and '\textquotesingle' not in tex;assert '\t' not in case;assert not re.search(r'\\paragraph\{[^}]*\.\}',case)
    assert sha(P/'fig/case_fig03.pdf')==sha(P/'archive/before_round2_20261015/fig/case_fig03.pdf')
    for file in (P/'tables').glob('*.tex'):
        if file.name.startswith(('v3_','round2_','review_')) and file.name in re.findall(r'\\input\{tables/([^}]+)\}',tex):assert '\t' not in file.read_text(encoding='utf-8')
    assert 'P0P' not in (P/'tables/v3_reference.tex').read_text(encoding='utf-8') and (P/'tables/v3_reference.tex').read_text(encoding='utf-8').count(r'\begin{tabular*}{\linewidth}')==4
    abstract=tex.split(r'\begin{abstract}',1)[1].split(r'\end{abstract}',1)[0];abstract_words=len(abstract.split());assert abstract_words<=200
    snapshots=[]
    for i,r in enumerate(CA['reports']):
        c=prepare(C[r['case_id']],r['spec']);m=Model(C[r['case_id']],spec=r['spec']);c=dict(c,reference_U=m.state_U);path=ROOT/'calibrated_inputs'/f'reference_{i:03d}_{r["case_id"]}.json';dump(path,dict(spec=r['spec'],resolved_input=c));snapshots.append(path)
    for i,g in enumerate(CC['groups']):
        spec=g['job']['spec'];c=prepare(C[g['job']['case']],spec);c=json.loads(json.dumps(c));factor=.88/spec['ref_load']
        for p in c['products']:p['run_cost']*=factor;p['fixed_cost']*=factor
        c['full_reference_cost']*=factor;path=ROOT/'calibrated_inputs'/f'constant_{i:03d}_{c["id"]}.json';dump(path,dict(spec=spec,resolved_input=c));snapshots.append(path)
    dump(ROOT/'inputs/calibration_audit.json',CA)
    for ci in C:dump(ROOT/f'inputs/{ci}_calibration.json',dict(version=VERSION,calibration=next(x for x in CA['reports'] if x['case_id']==ci and x['spec']=={}),elasticity=next(x for x in EL if x['case_id']==ci)))
    fea=sum(s['continuous'] and s['feasible']['P4'] for s in A['stress']);pol=sum(s['continuous'] and s['income']=='polarized' and s['feasible']['P4'] for s in A['stress']);abs_groups=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'runs/E11').glob('*.json')];abs_count=sum(pair_feasible(g,'P4') for g in abs_groups)
    oldgov=read('legacy_governance.json');var=read('variety_decomposition.json');resp=['# Case Study Review V3 — Round 2 修复记录','', '日期：2026-10-15。最新版仍为 `TRA-20261014-V3.tex/.pdf`。前一轮完整手稿和图表已备份至 `archive/before_round2_20261015/`；本轮程序、结果和证明在 `experiments_v3_round2/`。按照用户要求，图 3 的图像和图注保持不变。','', '## A. 六项核心修复','',f'1. **极化可比较性。** 主压力矩阵及席位定价实验改为同状态 P0 保留率分母，宏观绝对分母作为单独对照。当前 {fea}/72 个压力状态、{pol}/24 个极化状态有 P4 可行见证。48 个匹配衰退状态的绝对分母对照有 {abs_count}/48 个可行见证。正文明确 L 在极化中承受 −15%、统一冲击中承受 −7.56%，绝对目标机械地混合宏观损失与设计效果；新增同均值票价/班次/绝对参与率图与完整 E6 可行配对表。','', '2. **K 与母产品合并。** 同覆盖候选不再是独立 logit 选项；全部新增班次并入母产品频率、排班成本和座席容量。另在母产品已服务时段内限制增班以区分频率与新增时段可用性。母产品仍服务时，其固定承诺成本保留，避免用“撤减原班次、改称增班”节省固定成本。最终标量实现独立重算了这一处理。']
    for ci in C:
        p=record(R[ci],'P3','welfare');w=record(R[ci],'P4','welfare');ak=next(g for g in AK if g['case_id']==ci and g['k_cost']==1.);ap=next(r for r in ak['records'] if r['policy']=='P3' and r['objective']=='welfare');aw=next(r for r in ak['records'] if r['policy']=='P4' and r['objective']=='welfare');resp+=['',f'   {ci}：合并口径参考福利增量 {num((w["welfare"]-p["welfare"])/1000)} 千元/日；仅已服务时段的福利增量 {num((aw["welfare"]-ap["welfare"])/1000)} 千元/日。两者均为重优化结果，不能把全部收益解释为“纯品种”。']
    resp+=['',f'   旧 JX 四班设计的有序路径账目为：票价 {num(var[0]["fare_CS"]/1000)}、合并后的班次/可用性 {num(var[0]["schedule_availability_CS"]/1000)}、表示方式残差 {num(var[0]["representation_residual_CS"]/1000)} 千元。最后一项同时改变候选表示和频率聚合，不能称为纯品种分解；旧保存设计合并后峰值 {var[0]["merged_maxlf"]:.5f}，因此必须重优化。原摘要的 JX 福利进入结论已替换为框架和条件机制表述。','', '3. **商业 K 与道路竞争。** 表 9A 报告三廊道全部参考 P3/P4 增量和已服务时段对照；表 9B 汇总完整 5×8 网格中每一个正商业增量，按成本系数合并展示对应的道路水平、班次数和利润范围。删除“必须大幅降本”的统一结论。精确求解还发现 HN/WC 参考商业增班，不再沿用局部搜索的零进入判断。','', '4. **弹性口径。** 中央锚改为“一次改变一个 G/D 产品—时段公共倍率，其他产品和 K 固定”的自身数量弹性。按基准 G/D 流量加权均值为每廊道 −0.800（有限差分核验），另报告逐阶层自身范围、所有 G/D 同变且 K 固定的全铁路弹性、所有铁路票价同变的诊断。−0.60/−1.00 为敏感性锚。郑等的列车 OD 估计仍只是可比层级的参考范围，不是本项目的实证估计。','', '5. **票价网格与归因。** 0.025 成为中央菜单；全部参考 P0/P1/P2/P3/P4、Shapley 与二因素交互重新计算。新增 0.0125、保留 0.05/0.10 的带符号比较。HN/WC 的参考单工具与联合工具均以精确证书取值；精确解也作为其他搜索的起点。原“HN 票价贡献几乎为零”结论已删除。','', '6. **有利边界与可迁移量。** 摘要改写为 '+str(abstract_words)+' 词，删除中央货币收益作为普适头条。正文同时报告固定总成本 headroom 网格、网络暴露范围，以及每基准班次每个百分点容量余量的平均收益变化。明确零背景、全成本分摊是有利暴露边界。','', '## B. 机制与政策含义','',f'- **工具切换。** 图 10 现在直接对比绝对/同状态分母的相同 48 个衰退情景。在修正弹性及分母后，旧图的切换位置发生变化；正文只报告本轮重新计算的切换，避免把旧 F/N/J 位置搬到新校准。全部同状态压力矩阵及票价/班次响应均在档案中。','', '- **严格保留率与每出行成本。** 以下均为保存可行 P3 利润设计的比较；严格约束的目标不具有额外全局证书，故代价是保存方案之间的差值。']
    for r in strict:resp+=['',f'  {r["case_id"]}：利润代价 {num(r["sacrifice"]/1000)} 千元/日；目标缺口 {num(r["reference_shortfall"])} 人次，实际恢复 {num(r["actual_trips_restored"])} 人次；每恢复出行 {num(r["cost_per_restored"] or 0,0)} 元；净班次变化 {num(r["net_departures"],0)}；相当于 {num(r["departure_cost_equivalent"])} 个参考平均 G/D 班次的边际成本。L 平均铁路票价 {num(r["L_reference_rail_fare"])} 元。按该票价补偿目标缺口的算术预算 {num(r["voucher_arithmetic"]/1000)} 千元，未建模转移支付接受率或行为响应，不声称是已验证可行替代政策。']
    resp+=['', '- **互补性与绑定席位。** 表 8B/8C 和图 7 使用新网格及产品弹性。正文以 WC 的单工具/联合班次与票价组合解释交互，并分别指出商业、福利的峰值席位。前一轮“WC 商业 G business 绑定”的说法没有直接沿用，因为新校准/精确设计改变了峰值。','', '## C. 定点核查','', f'- **旧 HN 治理异常点已确认。** 同一旧校准的独立标量复算给出 ΔU={num(oldgov["CS_gap"]/1000)}、利润补偿={num(oldgov["profit_compensation"]/1000)}、福利差={num(oldgov["welfare_gap"]/1000)} 千元；收入增加 {num(oldgov["revenue_change"]/1000)}、成本增加 {num(oldgov["cost_change"]/1000)} 千元。按先换票价再换班次的解释路径，ΔU 分为 {num(oldgov["fare_first_CS"]/1000)} 与 {num(oldgov["frequency_after_fare_CS"]/1000)} 千元；中间路径不是单独可行政策。它来自较广泛的 0.95 倍率及更高班次，而不是错误混合参考 U。新稿附录按新校准重报三个最大福利差状态的收入、成本、CS 与补偿恒等式。','', '- **车队。** 附录列出每个廊道/等级的最大利用率、具体收入/道路情景、政策目标、已用和可用小时；接近或达到 1 的资源明确视为瓶颈，不再笼统称不绑定。','', '- **背景/成本份额组合。** χ=1 且背景为正的组合从“可接受暴露”范围剔除，用斜线单独标识，保留原始计算用于审计；这些组合在全费用归属廊道、部分乘客归属廊道外的本轮约定中不一致，和“搜索未解决”分开。','', '- **表 9。** 以新合并口径重做，参考增量统一列一次；商业 cost×road 正增量按系数组合，完整屏幕和福利结果保存在 JSON。','', '## D. 程序和呈现','', '- 所有方向箭头均用 raw string；表格、正文和图注无 TAB+extquotesingle，直接采用正常英文撇号或合法 LaTeX。','- 恢复 full-route endpoints、through occupancy、model reference cost 等实际含义。','- 摘要和引言改成论文叙述；数据边界集中到一段、表 11 与局限。','- 附录精确算法之前保留空行；表 7 按 E1--E10 顺序呈现，README 记录档案目录映射；表 8C 的 P0P 改为 P0。','- 图 12 使用等宽分类格，并与主压力轴共用 8 个 x 水平；图 13 将未解决标记移到独立灰带。图 14 图例继续外置。','- 图 3 根据用户明确要求完全保留，本轮不执行评审关于替换地图的意见。','', '## E. 精确计算与验证','',f'- HN/WC 的完整参考 P1/P2/P3/P4、利润/福利共 {len(exactrecords)} 项均获得枚举—车队整数主问题证书；仅这些参考有限菜单问题具有全局保证。主问题松弛去掉财务和保留率，重构最优解满足原约束并达到松弛上界，因此是原问题证书。','- 该证书揭示旧邻域搜索的参考缺口；中央值已更换为证书解，非仅附加一个不影响结论的 P1 检查。',f'- 主任务 {len(paths)} 个；固定总成本网格 54 个、432 条决策；已服务时段 K 诊断 6 组、24 条；道路碳诊断 24 条、其中 {sum(r["changed"] for r in CO["records"])} 条设计有变化，最大增广目标额外改善 {num(max(r["optimization_gain"] for r in CO["records"]),3)} 元/日。',f'- **独立数值核验保存决策共 {total:,} 条**：{V["records"]:,} 主/预算诊断 +432 固定成本 +24 K 限制 +24 碳诊断 +{len(exactrecords)} 精确参考。局部审计 {LA["unique_feasible_design_objectives"]:,} 个配置、{LA["checked_candidates"]:,} 个候选，无所声明邻域内的改进。',f'- PDF 已编译渲染，共 {QA["pages"]} 页；交叉引用未解析数为零。图 3 PDF 与前一轮备份的 SHA256 完全一致。','', '复现：`experiments_v3_round2/README_CN.md`。输入、代码、结果、图表及手稿哈希：`round2_manifest.json`。票价文献：[Zheng et al. (2017)](https://onlinelibrary.wiley.com/doi/10.1155/2017/6237642)。']
    for i,text in enumerate(resp):
        if text.startswith('3. **商业 K'):resp[i]+=' 本轮 JX 商业增量仅出现在成本系数 0.10/0.25，强道路竞争下 cost≥0.50 的旧边界没有保留下来；HN/WC 则在中央成本的低道路强度状态出现商业增班。旧图的 JX 强道路边界不能直接移植到修正后的模型。'
    repairs=read('audit_repairs.json')
    if repairs:resp.insert(-2,'独立邻域审计曾发现 '+', '.join(r['file']+' 的 '+r['policy']+' '+r['objective']+' 存在未收敛块' for r in repairs)+'；续算共改善 '+num(sum(r['improvement'] for r in repairs)/1000)+' 千元/日。修复后重新进行标量核验、全量邻域审计和统计生成，最终失败数为零。')
    response='\n'.join(resp)+'\n';(P/'REVIEW_RESPONSE_V3_round2_20261015.md').write_text(response,encoding='utf-8');(ROOT/'RESULTS_SUMMARY_CN.md').write_text(response,encoding='utf-8')
    readme='''# 第二轮实验复现

基准：50% 观测 G/D 可调、观测 K 固定；产品—时段 G/D 自身弹性流量加权锚 −0.8；0.025 公共票价步长；同覆盖 K 与母产品合并。压力和席位比较采用同状态 P0 保留率分母；绝对分母、K 撤减为单独实验。

原始 `inputs/HN.json` 等是不可变来源模板，包含旧中间参数。实际行为输入由 `calibration.prepare` 重建。`calibrated_inputs` 是本轮分辨率下的解析快照，供检查/标量复算，不要再次传入 Model.prepare 进行二次校准。

依次运行（PowerShell；Python 3.13、numpy/scipy/matplotlib/PyMuPDF，TeX Live latexmk）：

```powershell
python exact_period_benchmark.py
python run_experiments.py --reference-only --workers 8
python run_experiments.py --workers 8
python constant_cost_grid.py
python active_period_K.py
python carbon_sensitivity.py
python calibration_audit.py
python audit_and_polish.py
python verify.py
python analyze_review.py
python round2_diagnostics.py
python review_figures.py
python write_round2.py
Set-Location ..
latexmk -pdf -interaction=nonstopmode -halt-on-error TRA-20261014-V3.tex
Set-Location experiments_v3_round2
python qa_pdf.py
python finalize_round2.py
```

参考精确枚举必须先于全矩阵搜索。控制器保存输入/程序指纹并从嵌套政策、精确参考和先前方案继续；历史解只作起点，不能代替重算。`source_before_commitment_fix` 保留一次固定承诺处理完善前的源码；未开放 K 撤减的结果在新源下逐条重构相同数值，迁移记录保存在各 JSON 的 `source_reconstruction`。开放撤减的任务按最终规则重跑。标量验证再独立核对全部保存输出。

文内实验编号与原档案目录映射：E1=elasticities_round2；E2=reference E2；E3=E2 stress；E4=E3/E10/active_period_K；E5=E6；E6=E8；E7=E9/E11/E12；E8=E5/constant_cost/exact；E9=E4；E10=E7。

精确证书只适用于 HN/WC 的列示参考有限菜单，不覆盖压力情景、JX 或严格保留率最小代价。局部审计仅保证所声明块邻域。诊断未发现可行解不构成不可行证明。补贴率、成本、偏好、载荷、车队、分摊和碳参数具有情景假设。目标设计中的小数消费者流是期望量。

本轮入口为 write_round2.py / review_figures.py / finalize_round2.py。复制保留的旧生成器仅用于模块依赖或来源追溯，不应运行它们覆盖手稿。图 3 根据用户要求未修改。
''';(ROOT/'README_CN.md').write_text(readme,encoding='utf-8')
    files=list(ROOT.glob('*.py'))+list(ROOT.glob('*.json'))+list(ROOT.glob('*.md'))+list((ROOT/'inputs').glob('*.json'))+snapshots+paths+list((ROOT/'source_before_commitment_fix').glob('*.py'))+[p for p in (ROOT/'maps').rglob('*') if p.is_file()]
    inputs=re.findall(r'\\input\{tables/([^}]+)\}',tex);files +=[P/'tables'/x for x in inputs]+list((P/'fig').glob('case_fig*'))+list((P/'fig').glob('review_appendix_*'))+list((P/'fig').glob('round2_polarization*'))
    files +=[P/'TRA-20261014-V3.tex',P/'TRA-20261014-V3.pdf',P/'REVIEW_RESPONSE_V3_round2_20261015.md',P/'Case_Study_Review_V3_round2.md']+list(P.glob('TRA*references.bib'))
    manifest=dict(version=VERSION,date='2026-10-15',primary_jobs=len(paths),independently_checked_decisions=total,exact_reference_certificates=len(exactrecords),abstract_words=abstract_words,pdf_pages=QA['pages'],baseline=dict(GD_authority=.5,observed_K_fixed=True,product_period_elasticity=-.8,tariff_step=.025,stress_retention='same-state P0',K_representation='parent frequency and pooled capacity; retained parent commitment'),checks=dict(scalar=True,calibration=True,local_failures=0,exact_reference=True,map3_unchanged=True,unresolved_references=False),python=sys.version,platform=platform.platform(),files={str(x.relative_to(P)):sha(x) for x in sorted(set(files)) if x.exists() and x.name!='round2_manifest.json'})
    dump(ROOT/'round2_manifest.json',manifest);print('FINALIZED',len(paths),'jobs;',total,'independent decisions;',QA['pages'],'pages;',len(manifest['files']),'hashed files')

if __name__=='__main__':main()
