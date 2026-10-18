# Railway pricing and scheduling — code and data

公开仓库：[Wang1998666/railway-pricing-regulation](https://github.com/Wang1998666/railway-pricing-regulation)。

本仓库整理了论文 **Regulating Commercial Discretion in Railway Pricing and Scheduling: Fare Caps, Mobility Guarantees and Frequency Delegation** 最终手稿对应的计算代码、原始数据、运行结果和票价采集流程。

整理日期：**2026-10-18（北京时间）**。目录统一按用途命名。此次仅整理文件、调整路径及进行静态检查，**没有重新运行实验、求解器、绘图或数据采集**；原项目文件未改动。

## 目录结构

```text
.
├── experiments/
│   ├── main/                 # 主模型、校准、输入、主实验及结果
│   ├── policy_grid/          # 票价上限与出行保留率政策网格
│   └── supplementary/        # 最新补充实验及分析结果
├── data/
│   └── corridors/            # 三个走廊的原始快照、配置与上游案例
├── data_collection/          # 铁路票价、高德道路及接驳数据采集
├── preprocessing/            # 上游案例构造与数据审计程序
├── visualization/
│   ├── main_figures/         # 既有主实验图形资产
│   ├── case_figures/         # 案例图绘制代码与图形资产
│   └── model_diagrams/       # 模型示意图源文件
├── tables/
│   ├── main/                 # 主实验表格
│   └── supplementary/        # 补充分析使用的配套表格
├── reference_figures/        # 最终手稿的 17 张 PDF 插图
├── editorial/                # 历史文字和图标签修订支持材料
├── metadata/                 # 来源、文件清单、目录映射及校验记录
├── requirements-computation.txt
├── requirements-optional.txt
└── README.md
```

`experiments/main/` 中的 `inputs/` 是校准输入模板，`runs/` 是分组实验结果，`states/` 是去重求解状态。`historical_baseline/` 是历史审计材料，不作为最终模型入口。部分脚本文件名保留原名，以便追溯既有记录。

## 版本选择

| 部分 | 目录 | 现存结果文件的最近修改时间（北京时间） | 内容 |
| --- | --- | --- | --- |
| 主实验 | `experiments/main/` | 2026-10-15 20:29:48 | 主模型、966 组实验记录、840 个去重求解状态 |
| 政策网格 | `experiments/policy_grid/` | 2026-10-15 22:21:59 | 原始 60 点票价上限／出行保留率网格及补充检查 |
| 最新补充 | `experiments/supplementary/` | 2026-10-16 16:27:42 | 细化政策网格、指标分解、跨状态评价和弹性实验 |

这些是文件系统时间，不等同于精确的进程结束时间。补充实验来源清单记录的 76 个主实验源码哈希、7 个输入哈希在首次整理时均与原目录一致。最终稿后续更新不代表重新运行模型。

目录重组只调整路径与说明文档，原始数据、数值结果及核心模型算法保持不变。来源与新目录对应关系见 [selection_evidence.json](metadata/selection_evidence.json)、[file_manifest.csv](metadata/file_manifest.csv) 和 [layout_migration.json](metadata/layout_migration.json)。历史报告中的旧路径仅表示当时来源。

## 主要代码与结果

- `experiments/main/model.py`、`calibration.py`：需求响应、目标、约束与情景校准。
- `experiments/main/run_round5.py`：主实验组织、完整决策域去重与缓存。
- `experiments/main/exact_single_od.py`、`copt_backend.py`：单 OD 有限菜单枚举、COPT 主问题与 LP 筛选。
- `experiments/main/period_kernel.py`、`fast_evaluator.py`、`pareto_kernel.py`：计算加速。
- `experiments/main/verify.py`、`local_review_audit.py`：独立标量复核和局部邻域检查。
- `experiments/policy_grid/run_round6.py`：政策网格计算；`cap_floor_frontier.csv` 为结果。
- `experiments/supplementary/exp1.py`—`exp4.py`：最新补充实验；`checks_and_exp5.py` 包含原有事实及成本分摊检查。

主结果可先查看 `experiments/main/round5_analysis.json`、`certification_scope.csv`、`commercial_profile.csv` 和 `cap_floor_tradeoff.csv`；补充结果见 `experiments/supplementary/RESULTS_V4.md`、`exp1/grid.csv`、`exp2/analysis.json`、`exp3/cross_eval.csv` 和 `exp4/elasticity_ext.csv`。

最优性范围以归档证书清单为准。限时问题不能当作已证明最优或不可行；JX 和分席定价搜索不能当作全局最优证明；前后网格有重叠，不能直接相加作为唯一问题数量。

## 数据与票价来源

`data/corridors/` 包含杭州—南京、武汉—长沙和江西多 OD 三个走廊。铁路查询日期覆盖 **2026-08-03 至 2026-08-09**，基准日期为 **2026-08-05**。出行查询日期与实际采集时刻不同，以配置和原始 JSON 的 `collected_at_utc`（如有）为准。

各走廊 `raw_data/` 中包含：

- `*_trains_YYYYMMDD.csv`、`*_prices_YYYYMMDD.csv`：时刻与公布票价；
- `*_rail_raw_YYYYMMDD.json`：归档响应及错误记录；
- `*_amap_od.csv`、`*_amap_access.csv`、`*_amap_raw.json`：高德道路和接驳快照；
- `*_road_passenger.csv`、`*_access_fares.csv`、`*_road_cost_rules.json`：派生费用与规则。

`data_collection/collect_rail_12306.py` 调用随附客户端的 `query_tickets_validated` 与 `query_ticket_price_validated`，保存时刻、票价和原始 JSON。客户端位于 `data_collection/vendor/mcp-server-12306/`，归档票价接口为 `leftTicketPrice/queryAllPublicPrice`；原许可证一并保留。

`experiments/main/build_inputs.py` 按车次等级、停站覆盖和时段构造产品，采用可用公布票价的中位数，缺失席别按明示继承值或比例插补。最终情景还经过 `calibration.py` 校准，不能把全部输入当作直接观测。

`data_collection/collect_road_amap.py` 获取里程、规划时间、过路费和接驳属性，再按规则推算私家车、大巴、MaaS、商务车和接驳费用。**派生费用并非高德提供的市场成交票价。** 系数见各走廊费用规则和校准代码。`data/corridors/SOURCE_LEDGER_CN.md` 区分了观测、派生、校准和情景参数。

## 高德 API Key

**作者的高德 Key 未收录。复现者应使用自己的高德 Web 服务 Key。** 可设置：

```powershell
$env:AMAP_API_KEY = "YOUR_OWN_AMAP_WEB_SERVICE_KEY"
```

也可将 `data_collection/.env.example` 复制为同目录 `.env` 后填写自己的 Key；不要提交填写后的文件。使用归档输入离线计算不需要高德 Key。

接口日期窗、动态票价和接口变化会影响重新采集，核查论文应使用历史快照。另行采集时，复制走廊配置到新目录，将其 `query_date` 改为可查询日期，铁路 `--date` 与之保持一致，再采集高德属性。例如在仓库根目录：

```powershell
python -m pip install -r .\data_collection\requirements.txt
python .\data_collection\collect_rail_12306.py --config .\new_data\corridor_config.json --output-dir .\new_data --date YYYY-MM-DD
python .\data_collection\collect_road_amap.py --config .\new_data\corridor_config.json --output-dir .\new_data
```

## 软件环境与运行入口

归档环境为 Windows 11 64 位、Python **3.13.2**、NumPy **2.5.0**、SciPy **1.18.0**、Matplotlib **3.11.0**、PyMuPDF **1.28.0**、COPT/coptpy **8.0.6**，SciPy 内部 HiGHS **1.12.0**。版本、线程和容差见 `experiments/policy_grid/environment.json`。求解需要使用者自己的有效 COPT 许可。

主依赖见 `requirements-computation.txt`，辅助绘图／地图依赖见 `requirements-optional.txt`，采集依赖见 `data_collection/requirements.txt`。下列是原有入口说明，**本次未执行**；运行会使用或更新缓存，建议在完整副本中操作。

```powershell
python -m pip install -r requirements-computation.txt

Push-Location .\experiments\main
python run_round5.py --workers 8
Pop-Location

Push-Location .\experiments\policy_grid
python run_round6.py --workers 4
Pop-Location

Push-Location .\experiments\supplementary
python step0.py
python exp1.py
python exp2.py
python exp3.py
python exp4.py
Pop-Location
```

`step0.py` 会执行计算检查及必要的求解，不是本次目录检查。历史文稿生成、编译及排版检查脚本可能依赖未收录的手稿或备份，不作为最终论文的一键生成入口。绘图与路径说明见 [PORTABILITY.md](metadata/PORTABILITY.md)。此次未安装环境或进行端到端复现。

## 校验与追溯

`reference_figures/` 保留最终稿 17 张 PDF，16 张可与归档实验图哈希精确对应；Fig. 1 未找到哈希相同的上游 PDF。详见 `metadata/final_figure_sources.json`。

`metadata/file_manifest.csv` 保存原始来源和当前路径；`layout_migration.json` 记录目录调整与文件变化；`packaging_checks.json` 记录静态检查；`SHA256SUMS.txt` 覆盖当前文件（清单自身除外）。历史日志和科学报告保留其来源含义，当前路径以本 README 和元数据为准。

公开仓库地址见本文开头；未创建 DOI 或新的作者许可证，第三方代码保留原许可证。
