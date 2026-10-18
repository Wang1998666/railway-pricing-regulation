"""Publish the review trace, reproduction guide and final artifact hashes."""
import json,hashlib,re,sys,platform
from pathlib import Path
from model import ROOT,VERSION,dump,Model
P=ROOT.parent
def read(n):return json.loads((ROOT/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    checks=read('round3_checks.json');qa=read('pdf_qa.json');audit=read('local_audit.json');assert checks['passed'] and not qa['unresolved_reference_pages'] and not audit['failures']
    tex=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8');assert r'\appendix' not in tex
    response=f'''# 第三轮评审执行记录

日期：2026-10-15。针对 `Case_Study_Review_V3_round3.md` 的 N1–N6、G、H 完成一轮实验、正文和图表修订。最新版为 `TRA-20261014-V3.tex/.pdf`；前一轮文件在 `archive/before_round3_20261015/`，本轮独立档案在 `experiments_v3_round3/`。用户已明确豁免的图 3 和图 4(a) 保留：前者文件 SHA256 一致，后者矢量拼接后 2 倍分辨率逐像素一致。

## N1：票价上限与福利符号

- 新增三廊道 × 三个自身弹性锚（−0.60/−0.80/−1.00）× 三个票价上限（1.10/1.20/1.30），共 27 个情景、270 条政策记录。每个情景重新反演基准截距，维持目标客流和 0.88 峰值。
- §4.3、摘要、引言和结论明确：中央商业 P3 利润增加 1,585.2/1,788.8/1,472.0 千元/日，但旅客剩余损失更大，福利变化为 −398.9/−709.7/−810.3 千元/日。图 7 的商业福利条形直接展示此结果；图 8 展示票价与上限、班次变化和容量余量。
- 图 16 上排把弹性与票价上限作为主要证据，下排以 tornado 比较其他校准。§4.7 报告一个不能省略的反例：WC 在自身弹性锚 −1.00 时，三个上限下商业福利分别增加 716.7/765.0/753.1 千元/日。27 个组合中 24 个福利为负。因此没有照抄评审“任何合理弹性下均如此”的普遍措辞；结论限定中央校准并明确反例。
- 局限补充不允许跨时段替代及其可能提高时段定价权的问题。校准货币收益不作为识别出的经验因果效应。

## N2：压力域与极化的非单调价值

- §4.4 明确中央中等冲击大多被吸收：同状态域 P0 68/72、P4 72/72；不再以分母区分作为摘要主结果。
- 将原档案 E7、前稿文内 E10 的 0–1.5 更宽压力域搬入表 7B：P0 51/75，P3/P4 各 69/75 有配对可行见证；分别给出固定时刻表的容量、保留率、财务违反次数。未解决的优化状态不被标成已证明不可行。
- 图 11 的四指标 dumbbell 同时展示三廊道票价、班次、座席定价利润增量和福利 K 增班，并配道路强度细条。均值相同的统一/极化冲击下，座席定价利润增量分别为 HN 294.3/258.1、WC 436.4/234.8、JX 271.9/168.8 千元/日，均下降。
- 正文直接比较两个重新优化基准的利润变化：HN 公共/座席方案 −36.0/−72.2，WC +122.6/−79.0，JX +169.5/+66.4 千元/日。因此收入离散程度提高不自动增加相对公共定价的增量价值。

## N3：K 的经营账目和时刻机制

- 表 9A 与图 12 上排拆分新增队列收入、原有收入变化、原有成本节约、新增队列成本，并标出净利润。由于需求并入母产品，新增队列收入采用母产品—时段班次份额分摊，明确是会计分摊而非识别的独立客流。
- HN/WC 商业增班 3/2，利润 +91.2/+182.2，但福利 −262.1/−834.9 千元/日。原有成本节约 222.7/436.0 千元/日；固定全部 P3 原有决策、仅加入相同 K 班次时，利润反而 −230.0/−274.9 千元/日，且两反事实均可行。这说明商业收益依赖与 G/D 的联合调整。
- JX 的福利 K 增量按最终更好的 P3 比较：18 班、福利 +1,062.0、旅客剩余 +2,399.4 千元/日；不是沿用旧 P3 的 +1,083 数字。固定 P3 参与规模的三因素 Shapley 分解给出票价 +240.3、排班 +1,032.3、新时段可用性 +1,115.2，参与边际的精确非线性残差 +11.7 千元/日。可用性包含新服务时段的初始排班效用，不能解读为另一个独立产品的纯品种收益。
- 新增 30 个时刻情景、180 条记录：中央、半倍/1.5 倍排班斜率、60/120 分钟位移上限，均区分全部时段与仅原有服务时段。表 9B 报告 JX 全部十种福利比较。仅原有时段中央为 10 班、福利 +596.7 千元；半倍排班斜率或 60 分钟上限均只剩 1 班，福利 +11.5/+2.5 千元。正文明确大额收益对排班假设敏感。
- 原 40 状态筛选的十一类结果用逐类 gains/recoveries 简要列述，完整参数和逐格结果保留 JSON。成本—道路网格改为一张 sampled boundary step 图；最高进入水平不被称为连续阈值。

## N4：运营预算代价与社会福利分开

- 表 10B、图 13 同时报告严格保留率相对 0.95 的利润、旅客剩余和福利变化。
- HN/WC/JX 利润损失 1,033.9/1,087.0/1,314.7 千元/日，旅客剩余增加 1,958.1/2,489.5/2,251.5，福利增加 924.2/1,402.5/936.8 千元/日。
- 每恢复 L 出行 2,211/2,622/4,306 元称为“运营方预算代价”，与 133.2/142.2/82.9 元参考 L 票价用对数轴比较。实际恢复、目标缺口和整数超额恢复明确区分。优惠券只给预算量级，没有假称行为或福利等价。

## N5：实际车队限制与放松实验

- §4.2 直接报告 HN G 475.9/480 小时、WC G 553.1/576 小时，及 JX G/D 的 465.7/480、134.0/144 小时；解释产品—时段 +50% 上界不是可任意扩大的总车队。
- HN G 的整数总量上限仅为 119，对照参考 118；不是严格的零扩张。正文使用“聚合扩张有限”而没有照抄绝对 cut-only。
- 新增三廊道 × 25%/50% 车队放松共 6 情景、36 条记录。参考 P3 商业利润均不变；HN/WC 福利不变；JX 福利从 616.4 增至 895.0/920.6 千元/日，班次增至 193/195。这一约束对福利扩张的影响进入 §4.7。

## N6：公平性背离的规模

- 新图 14 使用 hexbin、两个边缘直方图、四象限占比及坐标轴上设计数量，避免重复点覆盖。
- 当前 1,605 个唯一可行物理设计中 261 个（16.3%）同时降低最坏实现出行成本比和 L 参与率。比前稿多出的一个物理设计来自改进的可行见证，不是重复记数。
- 同一背离象限内，三廊道最大 L 保留率下降分别为 2.48/1.31/0.83 个百分点；按各设计自身人口和状态精确计算，最大新增 L 非出行者分别为 561/449/421 人次/日。没有把一个廊道的最大百分点乘以另一廊道人口来放大损失。两组极值也不声称由同一个方案同时实现。
- 参与保护的必要性进入正文、表 11 和结论；设计库占比不被解释为现实发生概率。单独观测 K 撤减诊断保留在档案和公平性库，主基准仍为观测 K 固定。

## G：核心证据全部回正文

- 删除 appendix 和 A.x 图表；§4 重组为七个小节，分别为校准、求解/资源、上限定价与整合、同均值极化、K 增班、保留率/治理、校准依赖。
- 弹性表改为图 5；精确证书压缩为表 8 星号和 §4.2 两句算法说明；车队数据入 §4.2；治理账目并入表 10A/图 15；碳诊断并入表 10C；数值菜单/轮数检查在表 7C；headroom 并入图 8；网络暴露与校准入图 16。
- JX 碳诊断在道路强度 0/0.35 的设计变化为 4/4、2/4，正文明确报告。增广目标的再优化改善最多 9.20 元/日，与碳修正的千元量级区分，避免把近并列整数解的变化夸大为重大福利变化。
- 所有案例表使用普通 table/tabular* 与 95% 正文宽度，不使用 longtable。表 8C 铺满与其他面板相同的宽度。
- 工作流程按用户后续要求恢复原版 TikZ 四色分区框、实线数据流、虚线搜索反馈和点线核验路径；该要求覆盖评审的十行算法框压缩建议。不再使用几乎全为 P0 的政策热图，逐格材料和原 E 编号映射只保留在代码档案及可用性声明。
- 摘要改为 {checks['abstract_words']} 词的结果导向摘要；引言应用段和结论同步重写。移除评审指出的答辩措辞、程序标签和歧义负数区间。

## H：图形形式与会计校正

新案例图共十四幅（全稿图 3–16）：地图、alluvial/VOT、弹性 dot-range、TikZ 流程图、瀑布/福利条形、票价点图/headroom、OD 弧线、紧凑道路曲线、极化 dumbbell、K 分解/边界阶梯、保留率阶梯/对数比较、公平 hexbin、治理等福利线/瀑布、校准 tornado。

采用固定廊道色和参考灰/统一蓝/极化橙，目标使用线型或标记区分；治理收入状态还用圆/方/三角标记支持灰度阅读。新绘图为矢量 PDF，配 PNG 预览，正文普通标签约 7 pt，数学上下标另计。用户豁免的图 3、图 4(a) 沿用原标签尺度。

评审绘图建议存在两处会计符号问题，已按恒等式校正后实施：

1. Fare Shapley 与 frequency Shapley 已相加等于联合收益，不能再加交互。图 7 使用 standalone fare + standalone frequency + factorial interaction；表 8 另报告 Shapley。
2. 治理福利变化是旅客剩余变化 + 收入变化 − 成本变化，不是 −收入变化。图 15 正确相加三项；上排使用福利减商业利润差与旅客剩余差，等福利线斜率 −1，坐标等比例。

## 完整验证与保存

- 默认扩展重构前稿 4,794 条记录，最大数值差为零；后续嵌套政策/上限/资源见证传递改善了 {checks['baseline_witness_improvements']} 条原有记录。`baseline_witness_improvements.json` 逐条记录差值，避免把搜索改进误报为参数变更。
- 主实验 912 组、5,280 条记录；固定总成本 432、旧已服务时段 K 诊断 24、精确参考 16、道路碳 24、固定原有设计反事实 6，独立核验共 {checks['independently_checked_records']:,} 条。
- 中央/结构校准 96 组及本轮 63 组目标客流/峰值核验通过。主实验标量误差最大约 2.2×10^-7 元；额外记录最大误差 {checks['extra_maximum_error']:.3g}。
- 独立局部审计 {audit['unique_feasible_design_objectives']:,} 个可行设计—目标配置、{audit['checked_candidates']:,} 个候选，无声明邻域内的剩余改进。仅中央 HN/WC 的 16 个有限菜单参考问题有全局证书。
- 编译并逐页渲染 PDF：{qa['pages']} 页，交叉引用全部解析。案例部分无新增越界盒；日志仅保留前文原有约 2.2 pt 的两项提示。图例已移出遮挡区域，瀑布数值与标题错开。

复现入口：`experiments_v3_round3/README_CN.md`；核验汇总：`round3_checks.json`；最终文件指纹：`round3_manifest.json`。
'''
    # Avoid freezing a narrative number without checking the saved result.
    stress=read('review_analysis.json')['stress'];assert sum(s['continuous'] and s['feasible']['P0'] for s in stress)==68
    readme='''# 第三轮修订复现

本轮手稿 `../TRA-20261014-V3.tex/.pdf`。评审逐项响应 `../REVIEW_RESPONSE_V3_round3_20261015.md`。基准保持 50% 观测 G/D 可调整、观测 K 固定、自身产品—时段加权弹性 −0.80、0.025 票价步长、峰值 0.88/上限 0.95、成本 92% 参考收入及 70/30 变动/承诺分配。收入压力和席位比较使用同状态 P0 保留率；宽压力、严格保留率及 K 撤减单独保存。

## 只复核现存档案

在本文件目录，Python 3.13（numpy/scipy/matplotlib/PyMuPDF/Pillow）和 TeX Live 2020 latexmk：

```powershell
python verify.py
python calibration_audit.py
python audit_and_polish.py
python analyze_review.py
python -c "import round2_diagnostics as d; d.elasticities(); d.mechanisms()"
python analyze_round3.py
python figures_round3.py
python write_round3.py
python check_round3.py
Set-Location ../Fig
latexmk -pdf -interaction=nonstopmode -halt-on-error case_fig05.tex
Set-Location ..
latexmk -pdf -interaction=nonstopmode -halt-on-error TRA-20261014-V3.tex
Set-Location experiments_v3_round3
python qa_pdf.py
python finalize_round3.py
```

局部审计只保证声明的邻接产品/时段半径一块，不保证 JX/压力全局最优。`audit_and_polish.py` 在确有改善时会续算并改写该方案，随后必须重做 verify、全部统计和图表。`check_round3.py` 验证固定总成本、已服务时段、碳、精确证书和反事实，并核对守恒、会计、图 3/4(a) 保留与正文结构。

## 重算本轮新增实验

```powershell
python run_round3.py
python close_round3_domains.py
python audit_and_polish.py
```

然后依次执行上一节的 verify、分析、图表、手稿、编译和核验步骤。`run_round3.py` 对已匹配指纹的任务使用保存结果；若需要从零重算，另存已有 runs 后在独立副本运行。不要删除本档案来重跑。`close_round3_domains.py` 向更大票价/车队/可用时段域传递可行见证，并在完全相同行为校准的旧参考任务中核对域约束后传递改善。`baseline_reconstruction.json` 记录扩展前后默认数值一致；`baseline_witness_improvements.json` 与前稿独立包逐条比较搜索改进。

完整旧实验从零重算依次需要 exact_period_benchmark、run_experiments、constant_cost_grid、active_period_K、carbon_sensitivity，然后新增 E13–E15 与上述核验。参考精确枚举先于全矩阵搜索。保留的 write_round2/review_figures/finalize_round2 等旧生成器只用于模块依赖或历史溯源，不能用于覆盖本轮手稿。前稿源码在 baseline_source_round2，原输入模板在 inputs；实际行为输入由 calibration.prepare 重建，不能将 resolved_inputs 解析快照再次输入 Model 造成二次校准。

## 正文问题与档案目录映射

| 正文证据 | 计算目录或文件 |
|---|---|
| 自身/合并弹性阶梯 | elasticities_round2.json |
| 参考工具与相同收入/道路状态 | runs/E2 |
| K 四十状态筛选、成本—道路网格 | runs/E3、runs/E10 |
| 同均值极化和座席定价 | runs/E6、runs/E2 |
| 宽压力域（前稿文内 E10） | runs/E7 |
| 网络成本份额与背景 | runs/E8 |
| 预算/保留率范围 | runs/E4、runs/E9 |
| 绝对/同状态比较、观测 K 撤减 | runs/E11、runs/E12 |
| 结构与数值、固定总成本 | runs/E5、constant_cost_grid.json |
| 精确参考 | exact_period_benchmark.json |
| 已服务时段旧诊断、道路碳 | active_period_K.json、carbon_sensitivity.json |
| 上限 × 弹性锚，27 情景/270 记录 | runs/E13 |
| 排班斜率/位移上限 × 可用时段，30/180 | runs/E14 |
| 车队放松，6/36 | runs/E15 |
| K 收入/成本及旅客剩余渠道、严格预算 | round3_analysis.json |
| 固定原有设计后仅加 K 的 6 个反事实 | round3_counterfactuals.json |

图形源 `figures_round3.py`，正文/表格源 `write_round3.py`。活动矢量资产为 `../fig/round3_*.pdf`、未改动的 `case_fig03.pdf` 和恢复的流程图 `case_fig05.pdf`。流程图的可编辑 TikZ 源为 `../Fig/case_fig05.tex`，按用户后续要求保留原版配色、分区和线型；在当前全稿中编号为图 6。图 4(a) 使用未变的矢量裁片 `round3_fig04a_preserved.pdf`。表格均 95% 普通表。图、表编号以最终 Tex/PDF 为准。

## 解释界限

中央商业福利为负，但 WC 的 −1.00 弹性锚三个上限均为正，不能推广为所有合理校准。K 收入采用班次份额会计分摊；旅客剩余分解是固定参与规模的三因素 Shapley 加非线性参与残差，可用性包含新时段初始排班。严格保留率每出行代价是运营利润损失，不是社会净损失。公平性象限是设计库计数，绝对损失使用各设计自己的参考人口。票价无跨时段替代、规模/偏好/成本/编组/资源/配额/通过客流仍为校准假设。碳只作有限道路诊断。
'''
    (P/'REVIEW_RESPONSE_V3_round3_20261015.md').write_text(response,encoding='utf-8');(ROOT/'RESULTS_SUMMARY_CN.md').write_text(response,encoding='utf-8');(ROOT/'README_CN.md').write_text(readme,encoding='utf-8')
    # Export resolved calibrations for inspection; original templates remain inputs.
    C={ci:read(f'inputs/{ci}.json') for ci in ['HN','WC','JX']};snap=[]
    for i,r in enumerate(read('calibration_checks.json')['reports']):
        m=Model(C[r['case_id']],spec=r['spec']);p=ROOT/'resolved_inputs'/f'calibration_{i:03d}_{r["case_id"]}.json';dump(p,dict(spec=r['spec'],resolved_input=m.c,reference_U=m.state_U));snap.append(p)
    for p in sorted((ROOT/'runs').glob('E1[345]/*.json')):
        g=json.loads(p.read_text(encoding='utf-8'));m=Model(C[g['job']['case']],spec=g['job']['spec']);q=ROOT/'resolved_inputs'/p.name;dump(q,dict(job=g['job'],resolved_input=m.c,reference_U=m.state_U));snap.append(q)
    tables=re.findall(r'\\input\{tables/([^}]+)\}',tex);figs=re.findall(r'\\includegraphics\[[^\]]+\]\{([^}]+)\}',tex)
    files=[p for p in ROOT.rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md'] and not any(x in p.parts for x in ['preview','preview_round3_figures','__pycache__']) and p.name!='round3_manifest.json']
    files +=[P/'tables'/x for x in tables]+[P/x for x in figs]+[p for p in (ROOT/'maps').rglob('*') if p.is_file()]+list((P/'fig').glob('round3_*.png'))+[P/'fig'/x for x in ['round3_fig04a_preserved.pdf']]+[P/'TRA-20261014-V3.tex',P/'TRA-20261014-V3.pdf',P/'REVIEW_RESPONSE_V3_round3_20261015.md',P/'Case_Study_Review_V3_round3.md']+list(P.glob('TRA*references.bib'))
    files.append(P/'Fig/case_fig05.tex')
    jobs=len(list((ROOT/'runs').glob('E*/*.json')));assert jobs==912
    dump(ROOT/'round3_manifest.json',dict(version=VERSION,date='2026-10-15',jobs=jobs,new_jobs=63,checked_records=checks['independently_checked_records'],exact_certificates=16,pdf_pages=qa['pages'],checks=checks,local_candidates=audit['checked_candidates'],unresolved_references=0,python=sys.version,platform=platform.platform(),files={str(p.relative_to(P)):sha(p) for p in sorted(set(files)) if p.exists()}))
    print('FINALIZED',jobs,'jobs;',checks['independently_checked_records'],'checked records;',qa['pages'],'pages')
if __name__=='__main__':main()
