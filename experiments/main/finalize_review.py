"""Freeze review evidence and write a point-by-point Chinese response."""
import json,hashlib,re,copy,sys,platform,importlib.metadata
from pathlib import Path
import numpy as np
import fitz
from model import ROOT,Model,dump,VERSION
from calibration import KEYS
from run_experiments import tasks

P=ROOT.parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,s): p.write_text(s,encoding='utf-8')
A=json.loads((ROOT/'review_analysis.json').read_text(encoding='utf-8')); V=json.loads((ROOT/'verification.json').read_text(encoding='utf-8')); L=json.loads((ROOT/'local_audit.json').read_text(encoding='utf-8')); C=json.loads((ROOT/'constant_cost_grid.json').read_text(encoding='utf-8')); B=json.loads((ROOT/'exact_fare_benchmark.json').read_text(encoding='utf-8')); E=json.loads((ROOT/'carbon_sensitivity.json').read_text(encoding='utf-8')); K=json.loads((ROOT/'calibration_checks.json').read_text(encoding='utf-8'))
assert V['passed'] and not L['failures'] and K['passed']
assert C['program_sha256']==sha(ROOT/'constant_cost_grid.py')
assert len(C['groups'])==54 and all(a['stable'] for g in C['groups'] for a in g['local_audits'])
assert B['global_floors_slack_for_every_capacity_admissible_combination'] and max(abs(r['gap']) for r in B['records'])<1e-6
assert len(E['records'])==24 and all(r['scalar_error']<1e-6 for r in E['records'])
assert all(abs(e['profit_change']-(e['own_revenue']+e['incumbent_revenue_change']-e['activation_cost']-e['incumbent_cost_change']))<1e-6 for e in A['events'])
for ci in ['HN','WC','JX']:
    vals=[g['full_reference_cost'] for g in C['groups'] if g['job']['case']==ci]; assert max(vals)-min(vals)<1e-6
source=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8'); case=source.split(r'\section{Case study}',1)[1].split(r'\section{Discussion and conclusion}',1)[0]
assert not re.search(r'\\begin\{(?:equation|align|gather)\*?\}',case)
assert not re.search(r'\\paragraph\{[^{}]*\.\}',case)
assert 'longtable' not in source
pdf=fitz.open(P/'TRA-20261014-V3.pdf'); assert not any('??' in p.get_text() for p in pdf)
assert not any('Appendix Appendix' in p.get_text() for p in pdf)
assert sha(P/'fig'/'case_fig03.pdf')==sha(P/'archive'/'before_review_20261015'/'fig'/'case_fig03.pdf')
assert (P/'tables'/'v3_reference.tex').read_text(encoding='utf-8').count(r'\begin{tabular*}{\linewidth}')==4

# Export resolved reference cases; these snapshots are for inspection/scalar use.
seen=set(); exports=[]
for job in tasks():
    spec={k:v for k,v in job.get('spec',{}).items() if k in KEYS}; ci=job['case']; key=json.dumps([ci,spec],sort_keys=True)
    if key in seen: continue
    seen.add(key); raw=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')); m=Model(raw,spec=spec); c=copy.deepcopy(m.c); c['reference_U']=m.state_U
    c['source_calibration_metadata']={k:c.pop(k) for k in ['cost_rescale','calibration_rescale'] if k in c}; c['resolved_spec']=spec; c['input_role']='Resolved reference snapshot; do not pass through prepare() a second time.'
    path=ROOT/'calibrated_inputs'/f'{ci}_{hashlib.sha256(key.encode()).hexdigest()[:12]}.json'; dump(path,c); exports.append(path)
for g in C['groups']:
    ci=g['job']['case']; spec=g['job']['spec']; raw=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')); m=Model(raw,spec=spec); c=copy.deepcopy(m.c); factor=.88/spec['ref_load']
    for p in c['products']: p['run_cost']*=factor; p['fixed_cost']*=factor
    c['full_reference_cost']*=factor; c['reference_profit']=c['reference_revenue']-c['full_reference_cost']; c['reference_U']=m.state_U; c['resolved_spec']=spec; c['input_role']='Resolved constant-total-cost reference snapshot; do not recalibrate.'
    for k in ['cost_rescale','calibration_rescale']: c.pop(k,None)
    path=ROOT/'calibrated_inputs'/(g['job']['id']+'_constant_cost.json'); dump(path,c); exports.append(path)
dump(ROOT/'inputs'/'calibration_audit.json',K)
for ci in ['HN','WC','JX']: dump(ROOT/'inputs'/f'{ci}_calibration.json',dict(version=VERSION,reports=[r for r in K['reports'] if r['case_id']==ci],role='Review calibration audit; raw template is transformed by calibration.prepare.'))
total=V['records']+sum(len(g['records']) for g in C['groups'])+len(E['records'])+len(B['records'])
eq=A['equity_stats']; hstats={ci:[min(r['gain']/1000 for r in A['headroom'] if r['case_id']==ci and r['objective']=='profit'),max(r['gain']/1000 for r in A['headroom'] if r['case_id']==ci and r['objective']=='profit')] for ci in ['HN','WC','JX']}
report=f'''# Case_Study_Review_V3 逐条处理结果

日期：2026-10-15。依据 `Case_Study_Review_V3.md` 修改 `TRA-20261014-V3.tex`，并重新编译同名 PDF。修改前完整手稿、图表、参考文献已备份到 `archive/before_review_20261015/`。旧实验包保持不动；本轮程序和数据在 `experiments_v3_review/`。

## 结论与边界

- 基准仍为 **50% G/D 可调、观测 K 固定**。用户另行同意的 K 撤减仅用于诊断。
- 中央校准的 P3 利润增益为 HN/WC/JX **51.91/87.69/53.97 万元/日**；福利增益为 **50.24/80.50/38.07 万元/日**。这些是有假设条件的数值，不能解读为实证识别的效率收益。
- 72 个连续道路强度情景中，45 个找到 P4 可行见证（17/16/12）。不可行搜索不被当成证明。
- 费用、需求、阶层偏好、权限和预算率均有未识别部分；图表和结论明确标注。福利主指标仍是铁路中心指标，道路碳诊断不等于完整社会福利。

## A. 实质意见

1. **容量余量和成本机制：已重做。** 正文明示收益主要来自利用假定空余座席削减边际成本。中央载荷 0.88，不声称来自观测；同时测试 0.85/0.88/0.92、上限 0.95/1.00、可变成本 50/70/90%。主结构检验另把分摊前模型总成本固定在 0.88 中央值，避免每个载荷都按收入重新归一化。三廊道利润增益范围分别为 {hstats['HN'][0]:.0f}–{hstats['HN'][1]:.0f}、{hstats['WC'][0]:.0f}–{hstats['WC'][1]:.0f}、{hstats['JX'][0]:.0f}–{hstats['JX'][1]:.0f} 千元。座席级上限也已解释：公共折扣对昂贵席位产生更大的绝对节省，可能先触发商务/一等座容量。

2. **弹性与汽车口径：已诊断并重校准。** 初始全铁路票价弹性为 −1.65/−1.89/−1.19；用文献范围内的 −0.8 作情景锚，检验 −0.6/−1.0。它不是逐廊道实证估计，文献的列车 OD 与全铁路口径也不同。共同缩放全部效用斜率，保留 VOT 比值，并重校准常数。附录逐廊道、阶层报告铁路票价、产品、自驾成本交叉和出行收入弹性。汽车成本与节省均按 **2 人/车** 分摊，另测 1/3 人。HN/WC/JX 最长 OD 的车辆通行费为 110/140/235 元；人均自驾成本为 178.7/216.7/341.7 元。旧图 4 的 JX 点用了短 OD，现已改为最长 OD。道路 x=0 是无额外降本，不代表现有 EV 存量为零；当前车队构成未被识别。

3. **工具交互：已替换。** 表 8B 用二因素交互和 Shapley 贡献，取消把块坐标重优化当成交互证明。中央利润交互 HN/WC/JX 为 −2.4/+67.1/−3.1 千元，福利为 0/+56.2/−8.4 千元。只有 WC 有明确正交互；HN/JX 近加性或略有替代。联合增量仍可报告，但不叫互补性。

4. **过境列车：完成 χ/背景占用检验。** 没有用今日时刻表回填历史列车属性。测试 χ=0.25/0.50/1.00 与背景占用 0/0.15/0.30。背景情景保持参考总占用，减少廊道可归属需求，频率变化时背景流固定；分摊前模型成本不会按降低后的廊道收入重设。χ 作用于校准成本包，不识别真实全程账户。正文明确 50% 权限是规划反事实，不能据此声称能取消实际长途列车。

5. **阶层异质性：已加入。** 参与率 H/M/L 为 0.90/0.85/0.80，铁路份额和产品/座席配置也不同；比例拟合保持总座席流不变。表 8D 显示 H 的高等级席位比例与 L 明显不同，并有同质目标敏感性。偏好倾斜是维护假设，不是调查估计。E6 的完整可行配对也已展示：JX 统一收入下降时席位差异定价额外增加利润/福利 6.54/1.17 万元，参考状态为 0.33/0.22 万元；极化状态无可行配对，不把其最小违约目标当成收益。

6. **保留率机制：已补充，但不夸大。** K 撤减诊断单列。{eq['unique_feasible']} 个唯一可行物理设计中，最坏成本比与保留率同降的有 {eq['divergent']} 个；均值成本比检验为 {eq['mean_divergent']} 个。最坏比值象限内最大参与损失约 167 人、0.33 个百分点，仍属有限量级。正文不再宣称证明了大规模排除。JX 参考全撤减权限下，严格保留率恢复约 173 个弱势出行，牺牲约 26.44 万元利润，而最坏成本比基本不变；强调整数决策下保证的财务代价。

7. **宏观和运营效应：已分开。** 绝对参考分母保留；另测同状态 P0 分母。24 个匹配收入冲击/道路状态中，绝对分母有 11 个 P4 见证，同状态分母有 18 个。绝对目标要求补偿宏观损失，同状态目标保护当期基准；正文说明两者政策含义不同。

8. **退化网格与预算：已调整。** 连续 x 轴 0/0.05/0.10/0.20/0.35/0.50/0.75/1.00，另在 x=0.35 比较道路类型和传导率。预算用观察到的参考列车数乘以假定 2,000 元/班次，得到 29.4/37.0/38.0 万元，并测 0/5,000。列车暴露量可观察，预算率不是观察值；没有伪造实际补贴依据。

9. **反常结果：已逐项解释。** 旧 WC 逆序来自相同运行成本下收入反向变化：all-high 无财务下限时，参考收入/成本为 8.769/13.744 百万元，统一下降为 9.424/13.744；铁路出行增加而自驾减少。原高汽车车辆成本在基准常数中被补偿，收入提高货币敏感性后又使相对便宜的铁路受益，这是校准内机制。修正后 x=1 的 WC 统一下降比参考收入少 2.24 百万元收入、节省 1.38 百万元成本，利润下降 0.86 百万元。收入-only 超载位置在 K 硬座：新 WC 极化 K01 白天为 0.9897；附录列出全部峰值。HN 福利方案现在与商业方案有别；参考 CS 损失分别为约 0.64/6.13 万元。主可行情景路径利用率最大 0.75，G/D/K 车队最大 0.992/0.931/0.391，均未绑定。

10. **K 进入：已按新结果改写。** 基准没有商业增益，但 JX 福利选 4 班，新增 CS 约 19.23 万元、利润减少 10.81 万元、净福利增加 8.41 万元。商业进入仍需要大降本：HN 成本系数 0.10，JX 为 0.10/0.25。E3 全部维度已检验：8 个成本比较、4 个权限比较、3 个重启成本比较、2 个道路状态比较及 1 个基准福利比较有正增量；非成本行可能只是延续基准进入，不声称都是因果触发。表 9 增加 ΔW、ΔU；其他维度无额外可行改进的结果也说明。所有道路强度共用同一无量纲单位。

11. **严格保留率前沿：已提升。** η=1.00 的 P3 利润牺牲为 5.83/8.24/14.80 万元，即参考增益的 11.2/9.4/27.4%。福利牺牲为 2.81/4.03/0，JX 原已超过完整参考参与。加入实际达到的 η 和密集邻近点；只画样本点，不线性插值到未知前沿。

## B. 新增检验的完成情况

| 项目 | 处理 |
|---|---|
| B1 弹性验证 | 全部四类导数、逐阶层/廊道/产品；票价文献校准锚及斜率敏感性。交叉和收入导数是诊断，未伪称已估计或有同口径文献目标。 |
| B2 载荷×成本 | 54 个总成本固定检验、432 条决策，独立复算和 108 个 P3 邻域检验；同时保留共同重标成本的配套网格。 |
| B3 尺度重校准 | 4 个尺度变体×3 廊道，24 个 P3 目标均可行；所有份额重现。 |
| B4 过境暴露 | χ/背景占用敏感性替代未识别的历史全程分类。 |
| B5 压力与预算 | 连续强度与有内部可行区间的矩阵；以观测班次归一化，预算率仍明确为假设。 |
| B6 K 撤减 | 经用户同意增加；基准不变。未开放软卧自由定价，仍用保守的 K 公共倍率限制。 |
| B7 同状态保留率 | 24 个匹配情景，18 对 11 个可行见证。 |
| B8 道路外部性 | 24 个道路碳增广福利重优化：100/500 元每吨、基准 EV 份额 0.25/0.50；全部可行且设计不变，福利调整绝对值最多约 0.50 万元/日。能源/乘员数为假设；不含铁路排放、道路利润、拥堵、生命周期。 |
| B9 阶层目标 | 参与、铁路、产品及高等级席位异质性；保持总座席流，报告同质对照。 |
| B10 精确基准 | 完整 HN 参考 P1：利用时段可分和全域财政/保留率下界，324 局部组合覆盖 43,046,721 名义联合菜单，精确值与搜索一致；仅此子问题有全局证书。 |
| B11 带符号网格 | 0.025 网格相对 0.05 全部非负，HN 最大利润/福利增量 7.24/5.17 万元；八轮对六个参考 P3 目标没有额外变化。 |

## C. 表述与图表

- 删除案例修订历史措辞；段落标题内不加句号，避免双句点。
- 表 7 按研究目的组织设计；E4/E5/E7 的细节与数值敏感性移入附录。
- 表 6 明确方向、水平收入冲击、成本系数、70/30 拆分及人均汽车口径；表 8 用四个同宽普通面板报告目标、Shapley、运行和异质组成。表 10 不再输出 −0.0。
- 图 13 加密实得阈值、显示 >1 的值、轴内标不可行点、取消 P0 图例，并按同一行为状态下的物理 N/φ 去重；成本/预算/目标重复记录不重复计数。
- 图 12 标注无 K 进入的 WC 区域，所有测试刻度均显示。图 4 为修正单位和 OD 选择更新数据，保留 alluvial/VOT/成本结构。
- 表 11 为政策含义与证据边界表。

### C8 地图核查

已核查[《地图管理条例》](https://www.gov.cn/zhengce/zhengceku/2015-12/14/content_10403.htm)第十五、十六条及[地图审核管理规定](https://ghzrzyw.beijing.gov.cn/zhengwuxinxi/zcfg/gz/202205/t20220530_2724733.html)。现有归档底图没有经过本项目核验的审图号；署名与数据许可不等于审图批准。为尊重之前要求，轨迹图仍作为工作稿图 3 保留，同时提供 `fig/review_corridor_schematic.pdf` / PNG 的无地理底图网络示意备选。没有宣称示意图自动获得审图豁免。正式公开发表前，应由作者与出版方确认适用流程、采用有审图依据的底图或提交审核；本轮不代办出版审图，也不把未核实的批准状态写成已合规。

## 验证与文件

- 主任务 774 个、总成本固定网格 54 个、碳诊断 24 个。
- 保存政策决策共 **{total:,}** 条：4,260 主/无财务下限 +432 固定成本网格 +24 碳诊断 +2 精确基准，全部通过相应独立数值核验。
- 主邻域审计 {L['unique_feasible_design_objectives']:,} 个配置、{L['checked_candidates']:,} 个候选，无改进块；固定成本网格另审计 108 个 P3 输出。
- 手稿、普通 95% 宽度表格和全部图已编译渲染；未解析交叉引用为零。最终 PDF {len(pdf)} 页。
- 复现说明 `experiments_v3_review/README_CN.md`；输入、程序、实验和文档哈希 `experiments_v3_review/review_manifest.json`。

主要来源：[中国铁路票价弹性研究](https://onlinelibrary.wiley.com/doi/10.1155/2017/6237642)、[世界银行中国高铁研究](https://documents1.worldbank.org/curated/en/933411559841476316/pdf/China-High-Speed-Rail-Development.pdf)、[生态环境部 2023 电力因子](https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202512/t20251231_1139517.html)、[EPA 燃料碳含量](https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle)。这些来源只支持对应参数或参考范围，不证明本项目的未知需求、成本、车队或权限。
'''
write(P/'REVIEW_RESPONSE_V3_20261015.md',report); write(ROOT/'RESULTS_SUMMARY_CN.md',report)
write(ROOT/'README_CN.md',r'''# Review V3 实验包

基准保持 50% G/D 可调、观测 K 固定。仅 E12 撤减诊断放开观测 K。手稿在上一级 `TRA-20261014-V3.tex/pdf`；逐条处理见 `../REVIEW_RESPONSE_V3_20261015.md`。原项目和各轮备份均保留。

## 复现顺序

核心输入为 `inputs/HN.json`、WC/JX 同名文件，属于不可变的源模板。每次模型创建时，`calibration.prepare` 重新生成需求、偏好常数、车辆人均成本和成本拆分；模板里的旧 alpha/qbar 和参考总额不直接用于本轮响应，旧单位成本只提供新成本包的相对分配权重。`calibrated_inputs/` 导出了 96 个参考校准和 54 个总成本固定网格的已解析快照，仅供检查或 scalar 复算，**不要再次交给 Model/prepare 重校准**。

```powershell
python run_experiments.py --experiments E2 --reference-only --workers 3
python run_experiments.py --workers 8
python constant_cost_grid.py
python analyze_review.py
python elasticity.py
python calibration_audit.py
python verify.py
python local_review_audit.py
python carbon_sensitivity.py
python exact_fare_benchmark.py
python review_figures.py
python -c "from review_figures import schematic_alternative; schematic_alternative()"
python -W ignore write_review.py
```

在上一级运行 `latexmk -pdf -interaction=nonstopmode -halt-on-error TRA-20261014-V3.tex`，完成后回本目录运行 `python qa_pdf.py` 和 `python finalize_review.py`。需 NumPy、SciPy、Matplotlib、PyMuPDF、Pillow、GeoPandas 与 TeX Live；版本在 manifest 中。

第一步参考搜索是必要的，后续设计会加入已达到的 retention 阈值。若修改 Model/calibration/controller，应提升 VERSION 后重算，避免复用旧结果；独立审计检查所有核心哈希。`constant_cost_grid.py` 在冻结主模型外固定总成本，重设同状态财务基准，并用相应既有网格和中央解作起点。

## 审计口径

- `verification.json`：4,260 个主/无财务下限决策，独立标量需求、成本、福利、容量、保留率、权限、菜单和嵌套支配。
- `calibration_checks.json`：96 个目标重现及成本拆分。
- `constant_cost_grid.json`：54 任务、432 决策；每条标量复算，108 个 P3 邻域检查。总成本固定在 L0=0.88，变量成本比例仍变动。
- `carbon_sensitivity.json`：24 条道路碳增广福利优化及独立排放/目标复算。
- `exact_fare_benchmark.json`：HN P1 的可分性全域证书和两个精确决策，不能外推至完整模型。
- `equity_unique.json`：行为状态与 N/phi 的物理去重，合并不同政策、目标、预算和成本标签；忽略不存在座席的票价槽并消除数值表示噪声。可行表示至少一个被测试设置下可行，比例不是现实发生率。
- `review_manifest.json`：完整哈希和检查记录。

目录内 `write_paper.py`、`revise_paper.py`、旧 `auxiliary.py`/旧图入口为历史辅助代码，不要运行覆盖本轮结果。正式入口是以上清单。源地图继续使用归档实际公路轨迹；主稿地图审批状态未核验，另有网络示意备选。该说明不代替公开发表时的审图流程。
''')
files=list(ROOT.glob('*.py'))+list(ROOT.glob('*.json'))+list(ROOT.glob('*.md'))+list((ROOT/'inputs').glob('*.json'))+list((ROOT/'maps').glob('*'))+exports+[P/'TRA-20261014-V3.tex',P/'TRA-20261014-V3.pdf',P/'TRA-v3-review-references.bib',P/'REVIEW_RESPONSE_V3_20261015.md',P/'Case_Study_Review_V3.md']+list((P/'tables').glob('*.tex'))+list((P/'fig').glob('case_fig*.*'))+list((P/'fig').glob('review_*.*'))
runs=sorted((ROOT/'runs').glob('E*/*.json')); assert len(runs)==774
manifest=dict(version=VERSION,date='2026-10-15',primary_jobs=774,constant_cost_jobs=54,carbon_jobs=24,verified_saved_decisions=total,baseline=dict(GD_authority=.5,observed_K_fixed=True,load=.88,variable_share=.7,rail_fare_elasticity=-.8,car_occupancy=2,budget_per_observed_train=2000),python=sys.version,platform=platform.platform(),dependencies={name:importlib.metadata.version(name) for name in ['numpy','scipy','matplotlib','pymupdf','pillow','geopandas']},checks=dict(scalar=V['passed'],calibrations=K['passed'],local_failures=0,constant_total_cost=True,exact_HN_P1=True,carbon_scalar=True,unresolved_refs=False,no_numbered_case_equations=True,map_approval_verified=False),files={str(p.relative_to(P)):sha(p) for p in files if p.is_file() and p.name!='review_manifest.json'},runs={str(p.relative_to(ROOT)):sha(p) for p in runs})
dump(ROOT/'review_manifest.json',manifest)
print(json.dumps({k:manifest[k] for k in ['version','primary_jobs','constant_cost_jobs','carbon_jobs','verified_saved_decisions','checks']},ensure_ascii=False,indent=2))
