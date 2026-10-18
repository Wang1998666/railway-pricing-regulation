# 输入数据字典

## 1. 案例清单

清单顶层为 `cases` 数组。每项字段如下：

| 字段 | 必需 | 含义 |
|---|---:|---|
| `id` | 是 | 文件安全的唯一标识，只允许字母、数字、`.`、`_`、`-` |
| `label` | 否 | 报表显示名，可用中文 |
| `case_file` | 是 | 最终 `pattern_case.json` 路径 |
| `aligned_case` | 构造时 | 尚未加入服务模式的基础案例 |
| `trains_csv` | 构造时 | 用于识别历史 K 服务模式的列车 OD 记录 |

路径可为绝对路径，也可为相对于清单文件的路径。

## 2. 完整案例的顶层结构

| 模块 | 核心内容 |
|---|---|
| `sets` | 城市、OD、G/D/K、旅客类别、弱势类别、时段 |
| `network` | 线路区段、区段里程、每个 OD 经过的区段、OD 两端城市 |
| `products` | 各产品的座位容量、舒适度、可靠性、灵活性、车队规模 |
| `attributes` | 铁路票价/时间、接驳、公路和汽车属性 |
| `demand_segments` | 每个 OD×类别×时段的潜在需求 `qbar` |
| `utility` | 嵌套 Logit 系数、尺度参数和常数项 |
| `schedule` | 班次等待与站内等待参数 |
| `electrification_savings` | 不同公路方式每公里节约额 |
| `scenarios` | 收入冲击状态与电动化状态 |
| `reference_scenario` | 用于公平约束基准的收入、电动化状态名 |
| `constraints` | 线路、服务、票价、财务与公平约束参数 |
| `costs` | 产品固定成本、每班成本、列车公里成本 |
| `service_patterns` | 逐路径频率决策的服务模式集合 |
| `pattern_constraints` | 产品最低日开行数和模式生成说明 |
| `pattern_reference_design` | 现状频率矩阵和票价倍率矩阵 |

## 3. `sets`

- `cities`：按线路方向排列的城市列表，至少两个。
- `ods`：需求 OD 标识列表。可用任意字符串；若不是“起点-终点”形式，必须在 `network.od_endpoints` 中给出两端。
- `products`：当前模型必须严格为 `["G", "D", "K"]`。
- `classes`：旅客类别，可任意命名和排序。
- `vulnerable_class`：必须是 `classes` 中的一项，程序不再假设它位于最后。
- `periods`：保持输入顺序。每个时段至少给出正的 `duration_h`；用原始列车表构造模式时还需给出 0–24 小时的 `start`、`end`。

## 4. `network`

- `segments`：线路区段标识列表。
- `segment_lengths_km[segment]`：区段里程，用于构造模式及运行成本。
- `od_segments[od]`：该 OD 经过的线路区段。
- `od_endpoints[od] = [origin, destination]`：推荐显式提供，避免 OD 名称格式假设。

## 5. `products`

G、D、K 每项需要：

- `seat_capacity[seat]`：每列该席别容量，必须为正。
- `seat_comfort[seat]`：效用中的舒适度指标；席别键应与容量和票价一致。
- `reliability_fraction`：运行时间乘数，用于不可靠时间。
- `flexibility`：灵活性指标。
- `fleet_size`：可用车组/车底数量；程序转换为每日可用车底小时。

## 6. `attributes`

- `access_by_city[city]`：`fare`、`time_min`。
- `rail_fare[od][product][seat]`：基准票价；实际票价为该值乘优化倍率 `phi`。
- `rail_runtime_min[od][product]`：车内时间。
- `road_by_od[od]`：`distance_km`、`private_auto_cost`、`auto_duration_min`、`coach_fare`、`coach_duration_min`、`maas_fare`、`business_van_fare`。

若某 OD 某铁路产品没有有效票价或运行时间，该产品不会成为该需求单元的铁路备选。

## 7. `demand_segments`

每个 `od × class × period` 必须恰好出现一次，字段为 `od`、`class`、`period`、`qbar`。`qbar` 是可选择不出行的潜在需求，须非负。验证器会检查缺格、重格和未知格。

## 8. `utility`

`by_class[class]` 需要九个系数：`beta_c`、`beta_iv`、`beta_ac`、`beta_wt`、`beta_sc`、`beta_rel`、`beta_tr`、`gamma_com`、`gamma_flex`。其余字段：

- `rho[class]`：收入变化对成本敏感度的弹性调整。
- `mu`：`rail`、`road`、`auto`、`mode_level`、`top` 五级尺度。
- `alpha_travel[class]`：出行层常数。
- `asc_mode[class]`：`rail`、`road`、`auto` 方式常数。
- `asc_product`：G/D/K 产品常数。
- `asc_seat[product][seat]`：席别常数。
- `asc_alternative`：`private_auto`、`coach`、`maas`、`business_van` 常数。

## 9. 情景

`scenarios.income[state][class]` 给出相对收入冲击，可正可负且必须覆盖全部类别。

`scenarios.electrification[state]` 包含：

- `pass_through`：公路运营节约向票价传递比例。
- `auto_intensity`：私人汽车电动化强度。
- `road_services`：受到节约影响的公路服务，可选 `coach`、`maas`、`business_van`。

`reference_scenario` 的两个名称必须存在于对应状态字典。推荐始终显式填写。

## 10. 约束和成本

`constraints` 至少需要：

- `line_capacity_per_hour`：每线路区段每小时最大路径数。
- `min_od_departures_per_period`：所有铁路产品合计的 OD 最低班次。
- `fare_bounds = [lower, upper]`：票价倍率范围。
- `loss_tolerance_options`：至少两项；批量程序使用第二项。
- `retention_floor_options`：至少两项；批量程序使用第二项。

`costs` 的 `fixed_per_product_day`、`per_run`、`per_train_km` 都必须覆盖 G/D/K。服务模式自身还可有 `activation_cost`，用于表达 K 重开准备成本等路径级成本。

## 11. 服务模式与参考设计

每个 `service_patterns` 元素需要：

- `id`、`product`、`status`；
- `served_ods`、`route_segments`；
- `route_length_km`、`cycle_time_h`；
- 按全部时段给出的 `observed_frequency`、`frequency_max`；
- `activation_cost`，不需要时设 0。

`pattern_constraints.minimum_daily_departures_by_product` 必须覆盖 G/D/K。建议 G、D 为正，K 为 0。这样表示既有高速/动车资产不能完全弃用但可降频，而 K 由选择性重开政策决定。

`pattern_reference_design.N[pattern][period]` 必须覆盖所有模式和时段；`phi[product][period]` 必须覆盖 G/D/K。论文设定下，G/D 填现状频率，K 参考频率填 0；历史 K 班次保留在模式的 `observed_frequency` 中。

## 12. 原始列车 CSV

模板只有四列：

| 列 | 含义 |
|---|---|
| `train_no` | 车次编号；G/C 归入 G，D 归入 D，其余归入 K |
| `od_origin` | 查询 OD 起点，须与城市表一致 |
| `od_dest` | 查询 OD 终点，须与城市表一致 |
| `start_time` | `HH:MM`，用于分配时段 |

同一车次可出现多个 OD 行。构造器先按车次合并，再按其实际覆盖的 OD 集合生成 K 服务模式，因此不会把同一列车的多个查询行重复计为多列车。

## 13. 建议的数据检查顺序

1. 运行 `validate_case.py --no-deep` 做结构检查。
2. 运行不带 `--no-deep` 的验证，构造约束和需求引擎并评价参考方案。
3. 运行 `run_case_study.py --smoke`。
4. 正式批量求解后运行 `verify_results.py`。
5. 对论文关键解运行 `verify_block_neighborhood.py`，并记录搜索轮数、输入指纹和求解器版本。
