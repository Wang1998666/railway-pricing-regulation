# Policy grid

本目录保存 60 个票价上限／出行保留率政策网格点及 JX 补充检查，模型与求解器从同级 `../main/` 导入。后续细化网格位于 `../supplementary/exp1/`。

原有入口为 `python run_round6.py --workers 4`，分析入口为 `python analyze_round6.py`。此次未执行。环境见 `environment.json`，结果见 `grid/`、`variants/`、`cap_floor_frontier.csv` 和 `round6_analysis.json`。

证书范围及运行计数保持历史含义，网格与主实验重叠，不能简单相加作为唯一问题数量。文稿生成与排版检查脚本可能依赖未打包的历史手稿。统一说明见根目录 README。
