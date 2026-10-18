# 正式案例数据来源与引用台账

本台账对应 `manifest.json` 中的三个正式案例。论文正文需要引用的位置已经给出可直接使用的 BibTeX 标记；动态接口数据的采集日期、原始响应、派生表和 SHA-256 文件指纹均保存在本目录。高德密钥只保存在本机忽略文件中，不进入数据包或论文。

| 数据或论证用途 | 状态 | 官方来源 | 论文引用标记 | 需要引用的位置 |
|---|---|---|---|---|
| 2026-08-03 至 2026-08-09 列车时刻、公布票价和站点 | 观测快照 | [中国铁路 12306](https://kyfw.12306.cn/otn/leftTicketPrice/init) | `\citep{ChinaRailway12306}` | 数据来源、采集窗和基准日说明 |
| 城市中心间驾车里程、规划时间、收费及城市中心至铁路站接驳 | 观测快照 | [高德 Web 服务路径规划 API](https://lbs.amap.com/api/webservice/guide/api/direction/) | `\citep{AmapWebService2026}` | 公路与接驳属性的来源说明 |
| 杭州—南京作为成熟高密度高铁案例；宁杭高铁 256 km、11 站，开通初期 51.5 对动车组 | 案例选择背景 | [常州市政府网站转载人民日报报道](https://zg.changzhou.gov.cn/html/czzg/2013/CIBLKPQE_0702/19289.html) | `\citep{NinghangHSR2013}` | 杭州—南京案例选择理由 |
| 武汉—长沙为客流相对集中的热门区间 | 案例选择背景 | [武汉市人民政府，2026 年清明运输报道](https://www.wuhan.gov.cn/sy/whyw/202604/t20260404_2749518.shtml) | `\citep{WuhanChangshaPopularOD2026}` | 武汉—长沙案例选择理由 |
| 昌赣高铁连接南昌、吉安、赣州，全长 418 km、设计时速 350 km | 案例选择背景 | [中国政府网/新华社](https://www.gov.cn/xinwen/2019-12/26/content_5464244.htm) | `\citep{ChinaGovChanggan2019}` | 江西案例选择理由 |
| 昌赣高铁 13 站、初期 300 km/h；南昌—赣州和赣州—九江旅行时间变化 | 案例选择背景 | [南昌市人民政府](https://www.nc.gov.cn/ncszf/hygq/201912/fc8339566dbb4b20b675b5ef643b0100.shtml) | `\citep{NanchangGovChanggan2019}` | 江西多节点及延伸至九江的理由 |
| 2025 年全国居民收入和交通通信消费宏观背景 | 情景背景，不直接估计廊道参数 | [国家统计局](https://www.stats.gov.cn/sj/zxfbhjd/202601/t20260119_1962321.html) | `\citep{NBSIncome2025}` | 说明收入分组和冲击是情景输入而非廊道样本估计 |
| 杭州 2025 GDP、常住人口和居民收入 | 城市背景，不进入求解器 | [杭州网转载市统计局公报](https://hznews.hangzhou.com.cn/chengshi/content/2026-04/30/content_9214808.htm) | `\citep{HangzhouStats2025}` | 八城市背景数据的来源说明 |
| 南京 2025 GDP、常住人口和居民收入 | 城市背景，不进入求解器 | [南京市统计局（链接 DOCX）](https://tjj.nanjing.gov.cn/bmfw/njsj/202604/t20260403_5818444.html) | `\citep{NanjingStats2025}` | 八城市背景数据的来源说明 |
| 武汉 2025 GDP、常住人口和居民收入 | 城市背景，不进入求解器 | [武汉市统计局](https://tjj.wuhan.gov.cn/tjfw/tjgb/202604/t20260408_2750693.shtml) | `\citep{WuhanStats2025}` | 八城市背景数据的来源说明 |
| 长沙 2025 GDP、常住人口、城镇和农村居民收入 | 城市背景，不进入求解器 | [湖南省统计局转载长沙市统计局公报](https://tjj.hunan.gov.cn/hntj/tjfx/tjgb/szgb/zss_1/202605/t20260512_33975356.html) | `\citep{ChangshaStats2025}` | 八城市背景数据的来源说明 |
| 赣州 2025 GDP、常住人口和居民收入 | 城市背景，不进入求解器 | [赣州市人民政府](https://www.ganzhou.gov.cn/gzszf/c100022/202604/38a12f964da545109b1b16697faee249.shtml) | `\citep{GanzhouStats2025}` | 八城市背景数据的来源说明 |
| 吉安 2025 GDP、常住人口和居民收入 | 城市背景，不进入求解器；官方署名公报的公开镜像 | [吉安市统计局、国家统计局吉安调查队公报 PDF 镜像](https://tjgb.hongheiku.com/wp-content/uploads/2026/05/1779205233-430ea0d9f5.pdf) | `\citep{JianStats2025}` | 使用时同时披露镜像证据等级 |
| 南昌 2025 GDP、城乡居民收入及全体居民收入 | 城市背景，不进入求解器 | [南昌市人民政府图片版公报](https://www.nc.gov.cn/ncszf/tjgb/202604/b6221a4fa0104604bdc4aacaae0f32ba.shtml)、[“南昌发布”政务号收入稿](https://m.thepaper.cn/newsDetail_forward_32481648) | `\citep{NanchangStats2025,NanchangIncome2025}` | 八城市背景数据的来源说明；2025 常住人口未在公报中报告，保持缺失 |
| 九江 2025 GDP、常住人口、城镇和农村居民收入 | 城市背景，不进入求解器；市级政务新闻平台刊载 | [九江新闻网刊载统计公报](https://www.jjxw.cn/article/2026/05/29/779574.html) | `\citep{JiujiangStats2025}` | 八城市背景数据的来源说明 |

## 不应被引用为“观测事实”的参数

以下字段属于模型构造，不应仅因写入 JSON 就被称为经验观测：G/D/K 载客率、距离带铁路份额、85% 基准参与率、20%/60%/20% 收入分组、效用系数、嵌套尺度、车底规模、线路能力、成本率、票价边界、收入冲击、电动化渗透和监管阈值。正文统一称为 **calibrated parameters** 或 **scenario inputs**，并通过敏感性分析处理。

公路客运票价、私人汽车成本和接驳票价由 `collect_road_amap.py` 中公开可复现的公式从高德距离、时间和收费派生；它们是 **derived monetary attributes**，不是高德返回的市场成交价。需求总量由列车服务、设定载客率和设定铁路份额构造；它是 **calibrated market size**，不是 12306 客流。

八城市 2025 背景表保存在 `city_context_2025.csv`，字段级证据和缺失值政策保存在 `city_context_2025_sources.json`。其中长沙、九江的可访问公报未给出“全体居民”收入，南昌图片版公报未给出 2025 常住人口；这些字段保持空值，不用城乡收入加权、上一年数值或非官方估计填补。

## 文件级证据

- `formal_weekly_rail_summary.csv`：21 个“案例×日期”采集摘要和错误数。
- `formal_reference_od_product_summary.csv`：基准日逐 OD、逐产品的列车数、中位运行时间、中位代表席别票价及公路属性。
- `formal_case_summary.csv`：论文案例表所需的案例级统计。
- `formal_files_sha256.csv`：99 个案例文件与 4 个共享来源/背景文件（共 103 个）的 SHA-256 指纹。
- `formal_data_audit.json`：完整日期窗、产品分类规则和验证状态。
- `city_context_2025.csv`：八城市统一 2025 GDP、年末常住人口和居民收入背景字段，明确缺失值。
- `city_context_2025_sources.json`：八城市逐字段来源、引用键、证据等级和“不进入求解器”标记。
