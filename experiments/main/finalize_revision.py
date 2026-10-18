"""Freeze evidence, provenance, and a concise Chinese revision report."""
import json,hashlib,platform,sys,re
from pathlib import Path
import numpy as np
import fitz
from model import ROOT,VERSION

P=ROOT.parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,s): p.write_text(s,encoding='utf-8')
def dump(p,o): write(p,json.dumps(o,ensure_ascii=False,indent=2))
A=json.loads((ROOT/'analysis.json').read_text(encoding='utf-8'))
V=json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))
L=json.loads((ROOT/'local_audit.json').read_text(encoding='utf-8'))
assert V['passed'] and not L['failures']
runs=sorted((ROOT/'runs').glob('E*/*.json')); assert len(runs)==813
old4=P/'archive'/'before_visual_revision_20261014'/'fig'/'case_fig04.pdf'
assert sha(old4)==sha(P/'fig'/'case_fig04.pdf'),'Figure 4 changed'
source=(P/'TRA-20261014-V3.tex').read_text(encoding='utf-8'); case=source.split(r'\section{Case study}',1)[1].split(r'\section{Discussion and conclusion}',1)[0]
assert not re.search(r'\\begin\{(?:equation|align|gather)\*?\}',case)
assert 'longtable' not in source
for f in (P/'tables').glob('v3_*.tex'): assert 'longtable' not in f.read_text(encoding='utf-8')
assert (P/'tables'/'v3_reference.tex').read_text(encoding='utf-8').count(r'\begin{tabular*}{\linewidth}')==3
assert all(abs(e['own_revenue']+e['incumbent_revenue_change']-e['activation_cost']-e['incumbent_cost_change']-e['profit_change'])<1e-6 for e in A['events'])
doc=fitz.open(P/'TRA-20261014-V3.pdf'); assert not any('??' in p.get_text() for p in doc)
files=list(ROOT.glob('*.py'))+list(ROOT.glob('*.tex'))+list((ROOT/'inputs').glob('*.json'))+list((ROOT/'maps').glob('*'))+[P/'TRA-20261014-V3.tex',P/'TRA-20261014-V3.pdf',P/'TRA-v3-map-references.bib']+list((P/'fig').glob('case_fig*.*'))+list((P/'tables').glob('v3_*.tex'))
manifest=dict(version=VERSION,authority=.5,observed_K_fixed=True,groups=len(runs),main_records=V['records'],python=sys.version,platform=platform.platform(),figure4_preserved=True,pdf_pages=len(doc),files={str(p.relative_to(P)):sha(p) for p in files if p.is_file()},run_files={str(p.relative_to(ROOT)):sha(p) for p in runs},checks=dict(no_numbered_case_equations=True,no_longtables=True,table8_three_full_width_panels=True,scalar=V['passed'],local_failures=len(L['failures']),event_accounting=True))
dump(ROOT/'revision_manifest.json',manifest)
write(ROOT/'README_CN.md',r'''# V3 第二轮修改：部分频率权限与图表重构

正式手稿：`../TRA-20261014-V3.tex` 和同名 PDF。旧实验包 `../experiments_v3/` 保留，不覆盖。修改前 V3 与图表在 `../archive/before_visual_revision_20261014/`。

## 用户确认的权限

- 基准：每个观测 G/D 产品—时段的 50% 参考班次可调整；K 观测班次固定。
- 保护下限向上取整；上限为参考班次加可调份额向下取整，正权限时至少容许 2 班，以允许空时段新增。0% 权限严格固定原供给。
- G/D 产品每日最低 1 班，OD 时段覆盖、路径、车队、座席、财务和保留率约束仍有效。25%/75% 及 0% 是 E5 权限敏感性。
- 这是产品—时段聚合权限情景，不声称识别了具体的始发终到或过境列车。

## 复现顺序

在本目录运行，使用本机 Python（NumPy、SciPy、Matplotlib、GeoPandas、PyMuPDF、Pillow）及 TeX Live：

```powershell
python run_experiments.py --experiments E2 E6 E8 E9 E10 E3 E4 E5 E7 --workers 8
python analyze.py
python verify.py
python auxiliary.py
python revision_figures.py
python -c "import figures; figures.main(8); figures.main(9)"
pdflatex -interaction=nonstopmode -halt-on-error revised_case_fig05.tex
python revise_paper.py
```

在上一级目录运行 `latexmk -pdf -interaction=nonstopmode -halt-on-error TRA-20261014-V3.tex`，再回到本目录运行 `python qa_pdf.py` 和 `python finalize_revision.py`。

`write_paper.py` 保留上一轮生成逻辑，仅供新脚本导入辅助函数，**不要运行它覆盖新版手稿**。图 4 使用归档资产，未重新生成。`figures.py` 的旧 3/6/7/10--14 入口已由 `revision_figures.py` 替代。网络抓取脚本不是每次复现所需步骤；地图使用归档到 `maps/` 的素材。

## 数据和审计

813 个状态任务，3,498 条主实验记录，102 条取消财务下限记录；另有 E1 的 12 个部分重优化和 E3 的 14 个复核决策。`verification.json` 独立逐层计算需求、财务、福利、容量和保留率，检验权限上下限、固定 K、票价菜单、嵌套政策支配、输入及程序哈希。`local_audit.json` 独立重构规定的半径一邻域。`revision_manifest.json` 固化输入、代码、所有实验文件、图表与手稿哈希。

E8--E10 为本次图表诊断的扩展，不冒充最初实验计划：E8 使用 1,400 万预算；E9 细化保留率阈值与四分之一强度极化；E10 细化弱公路竞争与 K 成本。原 E2--E7 网格及无效应结果全部保留。

## 地图来源

`maps/reference_geometry.json` 从上一版 `TRA-V10/V1/Fig/corridor_od_trajectories.pdf` 的矢量线恢复实际 Amap 公路轨迹，并通过刻度反算经纬度；底图直接提取自该归档 PDF。没有使用旧脚本中的密钥或伪造新查询。当前输入距离标签与历史轨迹长度可能因查询快照不同而不同，正文已说明。

铁路背景：Natural Earth 1:10m 铁路图层（公共领域），JX 补充 OpenStreetMap/Overpass 的京九、昌赣、昌九几何（ODbL）。这不是每列观测列车的运行路径。底图署名 OpenStreetMap contributors / CARTO，图内保留署名。OSM 原始铁路响应与 Natural Earth ZIP 归档在 `maps/`。
''')
report=f'''# 本轮修改结果（2026-10-14）

最新文件：`TRA-20261014-V3.tex` / `TRA-20261014-V3.pdf`。原版本已完整备份，旧实验包保留。

## 图形不明显的原因与处理

1. 原先“所有观测列车固定”使 P2=P0、P3=P1，频率与联合控制在决策集合上完全重合。按用户确认改为 50% G/D 可调、K 固定，并检验 0/25/75% 权限。
2. 原冲击幅度与预算不匹配，多数输出没有可行见证，不能把最小违约解当作有效政策。保留原网格；增加弱冲击、K 成本、保留率阈值与扩大预算的分析，分别标明条件。
3. 绝对利润坐标压缩了政策差异。图 6 改为相对 P0 增益；图 7 只呈现发生改变的产品；图 10 展示充分预算；图 11 展示 K 成本阈值和座席定价；图 12 展示细化进入区间；图 13 展示保留率边界并聚合重合点；图 14 展示同情景治理差额并计数零差额重合点。
4. 零响应不等于绘图错误。HN 参考联合增量为零，WC 测试区间未进入额外 K，HN 治理方案重合，均在图文中明示，不人为调整数据。

## 主要结果

| 廊道 | P3 利润增益（万元/日） | P3 福利增益（万元/日） | 联合优于最佳单一工具：利润/福利（万元） |
|---|---:|---:|---:|
| HN |31.34|30.14|0 / 0|
| WC |47.21|41.80|2.34 / 2.21|
| JX |28.24|19.24|2.93 / 0.53|

基准 54 个情景仅 3 个参考情景找到可行解，不能声称部分权限解决了全部压力。取消财务下限后 P3/P4 分别在 45/46 个受冲击情景找到满足其他约束的方案；其亏损可给出充分预算上界。原 E7 仍有两处 JX 福利进入，新增细化网格显示更多阈值细节。

E3 有 7 个额外 K 事件（HN 2、JX 5），均已用 8 轮复核。频率可调以后，进入利润必须同时计入既有 G/D 的成本变化；正文和图 12 已从原三项分解改为四项分解，并以数值叙述替代编号公式。

## 排版与地图

- 图 3 恢复历史实际公路轨迹和地图底图，增加铁路/公路图标、参考列车及假设座席运力、可调/保护班次。铁路地理背景与列车实际路径明确区分。
- 图 4 的 PDF 与修改前哈希一致，原样保留。
- 图 5 为可编辑 TikZ，采用 4 条彩色泳道、独立框、实线/虚线/点线，并检查了重叠。
- 案例部分没有新增编号或展示公式；需求分配、均值匹配、K 进入核算改为数值说明。
- 表 8 A/B/C 各自使用同宽普通 tabular*，外层宽度 0.95 正文；所有案例表取消 longtable。参数表用普通续表，治理表在结论前排出。

## 验证

- 主任务 {len(runs)} 个，独立复算 {V['records']:,} 条记录全部通过。
- 本轮独立邻域审计 {L['unique_feasible_design_objectives']:,} 个唯一可行设计—目标组合、{L['checked_candidates']:,} 个候选，无改进块。
- 最大利润误差 {V['maximum_errors']['profit']:.2g} 元，最大流量守恒误差 {V['maximum_errors']['conservation']:.2g} 人次。
- 手稿已编译，未发现未解析交叉引用；图表页已渲染检查。地图归档、实验记录及程序哈希见 `experiments_v3_revision2/revision_manifest.json`。

这些仍是基于假定需求、编组、成本和权限的校准反事实，不是旅客数据估计，也没有全局最优或不可行证明。全部条件与原始无效应结果保留，避免为了图形差异改变结论。
'''
write(P/'REVISION_NOTES_20261014.md',report)
write(ROOT/'RESULTS_SUMMARY_CN.md',report)
write(ROOT/'Case_Study_Plan_V3_Revision_Addendum.md',r'''# 原 Case_Study_Plan_V3 的本轮补充

原计划 E1--E7 保留。本次由用户明确允许部分观测班次调整，并确认基准“50% G/D 可调、K 固定”。新增 0/25/75% 权限敏感性，不改变原参考票价、需求或成本校准。

- E8：3 廊道×3 收入×6 公路状态，预算 1,400 万，P3/P4、两目标，共 216 记录。用途：在约束一致且存在可行方案的状态内比较治理，不替代基准预算。
- E9：参考保留率 0.98/0.99/0.995/1/1.0025/1.005；四分之一极化的对数收入冲击下保留率 0.90/0.92/0.94/0.95/0.96/0.98/1。参考预算 50 万，弱极化预算 1,400 万；共 156 记录。
- E10：参考收入，K 成本 0.10/0.25/0.40/0.55/0.70/0.85/1，公路节省强度 0/0.02/0.04/0.06/0.08/0.12/0.20；高传导率，基准预算 50 万；共 588 记录。K 成本同比调整观测与候选服务。用途：解析 E3 发现的进入机制，避免原网格大部分超出可行域。

所有网格点均归档。细化范围是基于第一轮结果的诊断扩展，不属于事前确认性检验；不以细化图取代原压力情景，不删除零效应或未找到可行见证的结果。
''')
print(json.dumps({k:manifest[k] for k in ['version','groups','main_records','figure4_preserved','pdf_pages','checks']},ensure_ascii=False,indent=2))
