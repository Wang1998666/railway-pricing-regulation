# 第五轮实验修订档案

本档案对应 Case_Study_Review_V3_round5.md 和 TRA-20261014-V3.tex/.pdf。基准仍为50% G/D频率可调、观测K固定；撤减K只用于独立诊断。

- 主实验：966组、5496条记录；固定成本网格54组、432条；已服务时段K检验6组、24条；碳诊断24条。
- 按完整物理模型和决策域去重后求解840个状态，键包含票价上限、菜单、班次上下界、车底周期和约束参数。独立标量复核见verification.json，联合邻域证据见local_audit.json。
- 独立票价区间检查拦截了遗漏fare_cap的早期去重映射，手稿生成前已补全键并补算不同上限的情景。有效计算仅在完整域匹配后复用，迁移校验见domain_key_migration.json；被拦截的中间档案见archive_before_domain_key_fix_20261015。
- HN/WC逐状态逐政策求解；2583个最优证书、206个不可行证书、63个未获证书的问题。完整范围和界限见 certification_scope.csv；禁止将限时求解写成不可行或最优。
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
