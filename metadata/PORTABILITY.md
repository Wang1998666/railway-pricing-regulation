# 统一目录与路径说明

目录已按用途重组。主模型和数值结果保持不变，修改仅限导入路径、数据／图表位置及说明文档，没有执行研究代码、求解器、绘图或采集。

## 当前路径

| 用途 | 路径 |
| --- | --- |
| 主实验及模型 | `experiments/main/` |
| 政策网格 | `experiments/policy_grid/` |
| 补充实验 | `experiments/supplementary/` |
| 原始数据 | `data/corridors/` |
| 数据采集及用户 `.env` | `data_collection/` |
| 输入准备 | `preprocessing/` |
| 图形与代码 | `visualization/main_figures/`、`case_figures/`、`model_diagrams/` |
| 表格 | `tables/main/`、`tables/supplementary/` |
| 文字与图标签修订 | `editorial/` |
| 最终插图 | `reference_figures/` |

主模型仍以自身目录为 `ROOT`，输入与结果位于其旁。政策网格及补充实验从同级 `main/` 导入模型。输入构造与预处理审计程序改为读取 `data/corridors/`。案例绘图依赖改为 `experiments/main/`、`experiments/policy_grid/` 和 `editorial/`；主图输出改为 `visualization/main_figures/`。这些路径以代码位置解析。案例绘图仍需要 Arial 字体。

## 最终插图来源

| 最终稿图号 | 相同 PDF 的当前位置 |
| --- | --- |
| 1 | `reference_figures/` 保留最终 PDF；未找到哈希相同的上游 PDF。相关源文件为 `visualization/model_diagrams/nested_logit_tree_v2.tex` |
| 2 | `visualization/model_diagrams/bilevel_railway_design_architecture.pdf` |
| 3 | `visualization/main_figures/case_fig03.pdf` |
| 4—9 | `visualization/case_figures/` 中相应同号 PDF |
| 10 | `visualization/case_figures/fig14_mobility_guarantees.pdf` |
| 11 | `experiments/supplementary/exp1/fig13_cap_floor_frontier_v4.pdf` |
| 12 | `visualization/case_figures/fig15_equity_designs.pdf` |
| 13 | `visualization/case_figures/fig12_entry_accounting.pdf` |
| 14 | `visualization/case_figures/fig10_shock_profiles.pdf` |
| 15 | `visualization/case_figures/fig11_income_composition.pdf` |
| 16 | `visualization/case_figures/fig16_governance.pdf` |
| 17 | `experiments/supplementary/exp4/fig17_calibration_dependence_v4.pdf` |

最终插图由多轮资产组合而成，单独运行旧案例绘图入口不能重建全部最终插图。政策／弹性更新图应使用补充实验的绘图代码。

## 历史材料与指纹

原日志、科学报告和历史清单中的来源路径保留，用于核对最初实验。`layout_migration.json` 中的 `previous_path` 与原来源字段仅用于追溯，不是当前可执行路径。

历史文稿生成、排版及交付检查程序可能需要未打包的手稿、备份或早期实验；这些既有依赖不属于本次重组范围。主计算和绘图数据路径已更新，未新建历史稿件。

路径调整改变了部分 Python 文件的 SHA-256。历史清单保留原求解时的源码指纹，当前指纹以 `SHA256SUMS.txt` 为准；目录调整前后哈希见 `layout_migration.json`。没有重新生成求解证书或验证数值结果。
