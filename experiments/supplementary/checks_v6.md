# V6 remaining CHECK items

Checked on **16 October 2026 (Asia/Shanghai)**. Target: `D:/Paper-M/TRA/TRA-R4/TRA-20261016-V6.tex`. This file records findings and proposed text only. The manuscript, bibliography, model, calibration, inputs and existing result files were not edited. The optional sensitivity below used a separate in-memory input and wrote no replacement result files.

The four substantive markers are at manuscript lines **43, 76, 601 and 816**. They concern an unused affiliation, financial figures, the van tariff unit and the archive identifier. They are addressed below in the order of the requested financial and tariff checks, followed by the other two markers.

## 1. China State Railway Group: full-year 2024 financials

**Finding: the rounded amounts are supported by the audited consolidated statements, but “outstanding debt” should be “total liabilities”, and the existing bibliography entry is not an adequate audit citation.**

### Audited figures and evidence

The issuer's **2024 audit report**, 中兴财光华审会字（2025）第207262号, is signed **30 April 2025**. Its opinion covers the consolidated balance sheet at 31 December 2024 and the full-year consolidated income and cash-flow statements. The audit opinion is unmodified. The China Money disclosure was posted on **26 May 2025, 16:50**. These are annual figures, not January–September results.

| Item | Amount read from the audited statements | Conversion / interpretation |
|---|---:|---|
| 2024 consolidated net profit, 净利润 | 388,060.95 万元 | CNY **3,880,609,500**, or **3.8806095 billion**; rounds to **3.9 billion** |
| Total liabilities at 31 December 2024, 负债合计 | 620,017,169.80 万元 | CNY **6,200,171,698,000**, or **6.200171698 trillion** |
| Total assets at 31 December 2024, 资产总计 | 976,269,370.13 万元 | CNY **9,762,693,701,300**, or **9.7626937013 trillion** |
| Liabilities-to-assets ratio, 资产负债率 | Derived from the two audited balance-sheet amounts | **63.5088213120%**, rounding to **63.51%** |

Primary evidence, accessed **2026-10-16**:

- [China Money: 中国国家铁路集团有限公司2024年度审计报告](https://www.chinamoney.com.cn/chinese/cwbg/20250526/3120521.html).
- [The disclosure's actual PDF attachment](https://www.chinamoney.com.cn/dqs/cm-s-notice-query/fileDownLoad.do?mode=open&contentId=3120521&priority=0). The attachment was retrieved and its scanned pages were visually inspected. **PDF page 6 / printed page 4**, “合并资产负债表”, gives assets and liabilities; **PDF page 7 / printed page 5**, “合并利润表”, gives net profit. Both tables use **万元**, not yuan or 亿元. **PDF pages 3–5 / printed pages 1–3** give the opinion and signature date. Retrieved attachment: 25 PDF pages, SHA256 `45dd7e124b40ad53f1dd8f32f6daa634025d3e6268cd161eff3ce9f70784b34f`.

Independent disclosure cross-check, accessed **2026-10-16**:

- [CCXI 2025 tracking rating report hosted by the Shanghai Stock Exchange](https://static.sse.com.cn/disclosure/bond/announcement/corporate/c/new/2025-06-18/127996_20250618_X8D0.pdf), **PDF/printed page 18**, Appendix III. It reports 2024 liabilities of **62,001.72 亿元**, assets of **97,626.94 亿元**, net profit of **38.81 亿元**, and a liabilities-to-assets ratio of **63.51%**, consistent with the audited amounts after rounding. Its separately defined **total debt** is **51,206.77 亿元**, approximately **5.120677 trillion yuan**. This distinction is why the manuscript's **6.2 trillion** should not be described as outstanding interest-bearing debt.

The official annual-report landing page is also available: [China Money: 2024 annual report, posted 30 April 2025](https://www.chinamoney.com.cn/chinese/cwbg/20250430/3106892.html), accessed **2026-10-16**. The separately identified audit attachment above provides the direct numerical evidence.

### Comparison with `ChinaRailway2025`

[TRA-references.bib:170](D:/Paper-M/TRA/TRA-R4/TRA-references.bib:170) contains a generic entry titled *2024 Financial and Operating Statistics*, described as “Reported via gov.cn and press releases, January 2025” (lines 170–176). It supplies no URL, report number or identifiable audited document. The stated January timing precedes the signed annual audit. **That entry does not presently provide a traceable source for the audited financial figures**, even though the manuscript's rounded amounts can now be substantiated from the actual audit.

For the operating statistics, the [2024 statistical communiqué reproduced by the China Academy of Railway Sciences Group](https://www.rails.cn/html/news/2/2025/20250307_66135.html), posted 7 March 2025 and accessed **2026-10-16**, attributes its source to the national railway group's website. Under “运输生产” it gives **40.85 亿** national-railway passenger trips; under “路网规模” it gives **4.8 万 km** of HSR **nationwide**. The manuscript's approximately **4.08 billion** is retained as requested. It should not imply that all of these trips were HSR trips, or that the entire nationwide HSR mileage is a separate company-only mileage measure.

### Proposed replacement LaTeX

Replace the final sentence of Introduction paragraph 1, [V6:75](D:/Paper-M/TRA/TRA-R4/TRA-20261016-V6.tex:75), with the following. The citation keys require the proposed bibliography correction below; no bibliography file has been changed here.

```latex
In 2024, China's national railway operator carried approximately 4.08~billion passenger trips, while the country's HSR network reached about 48{,}000~km \citep{ChinaRailwayStats2025}. Its audited consolidated statements report net profit of 3.9~billion yuan and year-end total liabilities of 6.20~trillion yuan, equivalent to a liabilities-to-assets ratio of 63.51\% \citep{ChinaRailway2025}.
```

Proposed traceable bibliography metadata, to replace the existing financial entry and add a separate statistical entry if the authors adopt the sentence:

```bibtex
@misc{ChinaRailway2025,
  author       = {{China State Railway Group}},
  title        = {2024 Audit Report},
  year         = {2025},
  howpublished = {Audited consolidated financial statements},
  url          = {https://www.chinamoney.com.cn/chinese/cwbg/20250526/3120521.html},
  note         = {Audit report dated 30 April 2025, report no. 207262;
                  disclosed 26 May 2025. In Chinese. Accessed 16 October 2026}
}

@misc{ChinaRailwayStats2025,
  author       = {{China State Railway Group}},
  title        = {2024 Statistical Communique},
  year         = {2025},
  howpublished = {Reproduced by China Academy of Railway Sciences Group},
  url          = {https://www.rails.cn/html/news/2/2025/20250307_66135.html},
  note         = {Published 7 March 2025. In Chinese. Accessed 16 October 2026}
}
```

The English titles above are translations of the identified Chinese documents. No DOI is asserted for either document. If the authors elect to omit the financial comparison, the supported fallback is:

```latex
In 2024, China's national railway operator carried approximately 4.08~billion passenger trips, while the country's HSR network reached about 48{,}000~km \citep{ChinaRailwayStats2025}.
```

## 2. Business-van tariff: documented unit and recoverable origin

**Finding: the implemented per-traveler unit is explicitly documented in a later V7 data dictionary, but the same formula is inherited from an earlier charter-car rule. There is no documented occupancy conversion or independently verifiable tariff source connecting those two interpretations.** The default has not been changed.

### Evidence chain

1. **Recoverable legacy rule:** [TRA-V7/Case study/calc_ridehailing.py:50](<D:/Paper-M/TRA/TRA-V7/Case study/calc_ridehailing.py:50>) labels the exact coefficients **“跨城快车(包车)”**: 2.2 CNY/km, 0.40 CNY/min and a 50-CNY minimum (lines 50–57). `calc_fare` applies that rule directly (lines 61–70); the output column is **`kuaiche_baoche`** (lines 123–132). The label denotes an intercity charter-car service and supports a vehicle/booking interpretation of the old quote, **not evidence of an observed shared-seat tariff**. The file does not explicitly state “CNY/vehicle” or an occupancy assumption, so the label alone cannot establish the external quote's unit beyond doubt.

2. **Claimed commercial source, not an independently verified source:** the same file's docstring says “滴滴出行公开计价标准（山东地区）” ([lines 1–4](<D:/Paper-M/TRA/TRA-V7/Case study/calc_ridehailing.py:1>)), and line 53 describes an approximate 2.0–2.5 CNY/km intercity-car rate. There is no tariff URL, dated tariff sheet, screenshot, vehicle-class specification or explicit seat/vehicle unit in that attribution. **The claimed Didi/Shandong provenance cannot be independently substantiated from the supplied archive.** Amap is the source of route distance and duration; this code does not retrieve a commercial van fare from Amap.

3. **Direct field transfer:** [TRA-V7/Case study_TRA-V7_aligned/build_case.py:260](<D:/Paper-M/TRA/TRA-V7/Case study_TRA-V7_aligned/build_case.py:260>) maps `ride_row["kuaiche_baoche"]` directly to `business_van_fare`, with no occupancy division. The surrounding lines 255–260 also distinguish the other road-cost fields.

4. **Later explicit modeling contract:** [TRA-V7_FINAL_ALGORITHM_PACKAGE/DATA_DICTIONARY_CN.md:143](D:/Paper-M/TRA/TRA-V7/TRA-V7_FINAL_ALGORITHM_PACKAGE/DATA_DICTIONARY_CN.md:143) labels `business_van_fare` **元/人次** at line 150. This is positive evidence that the later model interface intended the field as **per passenger trip**. It does not validate the legacy commercial quote as a per-seat fare. The package's [data_pipeline/README_CN.md:49](D:/Paper-M/TRA/TRA-V7/TRA-V7_FINAL_ALGORITHM_PACKAGE/data_pipeline/README_CN.md:49) nevertheless calls the service **商务包车**. The archive therefore contains a charter-service label and an explicitly per-person data field without documenting their conversion.

5. **Generalized pipeline:** [data_pipeline/collect_road_amap.py:32](D:/Paper-M/TRA/TRA-V7/TRA-V7_FINAL_ALGORITHM_PACKAGE/data_pipeline/collect_road_amap.py:32) calculates the formula and rounds it to two decimals. Its defaults repeat the van coefficients at lines 55–60 and apply them directly at line 105. Amap route collection returns distance, duration and tolls at lines 182–197. [SOURCE_AUDIT_CN.md:7](D:/Paper-M/TRA/TRA-V7/TRA-V7_FINAL_ALGORITHM_PACKAGE/data_pipeline/SOURCE_AUDIT_CN.md:7) identifies `calc_ridehailing.py` as the earlier calculation being replaced by this configurable implementation; this establishes code ancestry, not empirical tariff validity.

6. **Formal HN input:** [hangzhou_nanjing_road_cost_rules.json:18](D:/Paper-M/TRA/TRA-V7/TRA-V7_REUSABLE_R1_KINCUMBENT_20260812/cases/formal/hangzhou_nanjing/raw_data/hangzhou_nanjing_road_cost_rules.json:18) records the same parameters at lines 18–23. [hangzhou_nanjing_road_passenger.csv:2](D:/Paper-M/TRA/TRA-V7/TRA-V7_REUSABLE_R1_KINCUMBENT_20260812/cases/formal/hangzhou_nanjing/raw_data/hangzhou_nanjing_road_passenger.csv:2) gives **279.388 km**, **202.117 minutes** and **695.50 CNY**. The arithmetic is `max(50, 2.2*279.388 + 0.4*202.117) = 695.5004`, rounded to 695.50; “about 696” is correct.

7. **Current pipeline application:** [TRA-R2/experiments_v3_round5/build_inputs.py:102](D:/Paper-M/TRA/TRA-R2/experiments_v3_round5/build_inputs.py:102) places `business_van_fare` in the individual travel alternative's monetary-cost attribute. [calibration.py:57](D:/Paper-M/TRA/TRA-R2/experiments_v3_round5/calibration.py:57) divides only private-auto cost by occupancy; [model.py:93](D:/Paper-M/TRA/TRA-R2/experiments_v3_round5/model.py:93) through line 105 applies no van-occupancy divisor. The later model therefore uses the full derived charge per traveler. The prior V4 forward check records reference van shares of **0.5400% / 0.5400% / 0.5845%** in HN/WC/JX: [TRA-R4/exp_v4/checks_data.json:2](D:/Paper-M/TRA/TRA-R4/exp_v4/checks_data.json:2).

Earlier-version and notes searches located the above code ancestry; they did not locate a separately identified, dated commercial tariff sheet or an author instruction explaining an occupancy conversion. The older [TRA-V6.txt:108](D:/Paper-M/TRA/TRA-V6/TRA-V6.txt:108) distinguishes vehicle operating costs from quoted passenger fares but does not establish the unit of these particular coefficients.

### Proposed replacement LaTeX

For the van portion of [V6:600](D:/Paper-M/TRA/TRA-R4/TRA-20261016-V6.tex:600), the following states the verified modeling unit and the unresolved empirical provenance:

```latex
Business-van monetary costs are modeled per traveler, as specified in the archived data dictionary, using the stylized rule $\max\{50,\,2.2d+0.4t\}$~CNY, where $d$ is road distance in kilometres and $t$ is driving time in minutes. The coefficients originate in an earlier intercity charter-car cost rule, for which no occupancy conversion or verified per-seat tariff source is documented; they are therefore treated as modeling assumptions rather than observed passenger tariffs. Vans account for approximately 0.5--0.6 percent of reference trips.
```

A shorter fallback, if the authors do not wish to describe the historical mapping in the main text, is:

```latex
Business-van costs follow a stylized per-traveler assumption of 2.2~CNY/km plus 0.4~CNY/min, with a minimum of 50~CNY; the unit and commercial provenance of the underlying tariff have not been independently verified.
```

### Optional occupancy-four sensitivity: completed without changing defaults

The archived van monetary cost was divided by four **in a deep-copied raw input**, and the normal reference-flow/intercept calibration was rerun. The input was assigned a unique sensitivity case ID to prevent reuse of a cached default calibration. All other settings remained at the central specification: reference income, no road-cost shock, P3 common pricing, cap 1.20, floor 0.95, the 0.025 menu and the original operating/finance constraints. No modified input, design record or CSV was saved over an existing file.

The **six central commercial/welfare P3 cases** were re-solved. HN/WC used the existing exact enumerator and COPT 8.0.6 with the V3 tolerances; JX used the existing deterministic multi-start search, seeded with the archived central records. Each final design passed the existing independent scalar/domain check. Status counts: **4 optimal, 2 search, 0 open, 0 infeasible**.

Money in this table is **thousand CNY/day**, one direction. Each “original → occupancy four” pair is evaluated relative to its corresponding same-state P0.

| Corridor | Objective | Profit gain: original → occupancy four | ΔW: original → occupancy four | L retention | Daily departures | Solve/search seconds |
|---|---|---:|---:|---:|---:|---:|
| HN | Commercial | 1,585.2 → 1,585.2 | −398.9 → −398.9 | 0.9810630664 | 129 | 1.25 |
| HN | Welfare | 523.7 → 523.7 | 562.2 → 562.2 | 1.0006651500 | 138 | 0.13 |
| WC | Commercial | 1,788.8 → 1,788.8 | −709.7 → −709.7 | 0.9882432475 | 164 | 0.65 |
| WC | Welfare | 852.5 → 852.5 | 769.6 → 769.6 | 0.9997538813 | 175 | 0.04 |
| JX | Commercial | 1,598.4 → 1,598.4 | −941.2 → −941.2 | 0.9932355840 | 174 | 19.79 |
| JX | Welfare | 163.3 → 163.3 | 833.7 → 833.7 | 1.0009904205 | 186 | 19.77 |

For all six cases, the computed changes in profit gain, ΔW and retention were **0.0**, including at the unrounded output precision. All departure arrays were identical; the maximum multiplier difference was **2.22e−16**. Maximum independent scalar error was **9.32e−8 CNY/day**; maximum reference rail-flow reproduction error was **5.10e−10 trips/day**. The 0.88 reference peak load was reproduced within **1.64e−12**. HN/WC objective-to-upper-bound gaps were below **6.1e−8 CNY/day**, well within the 0.01-CNY criterion. JX remains a search result.

**Interpretation:** this central invariance is a consequence of the calibration, not empirical evidence that the tariff unit is immaterial. [calibration.py:59](D:/Paper-M/TRA/TRA-R2/experiments_v3_round5/calibration.py:59) through line 73 re-inverts road intercepts to match the same reference participation and road-choice targets. At reference income and zero road shock, the reduction in the van's monetary utility term is exactly offset by the new intercept. The maximum change in calibrated road utility was **4.44e−16**. Consequently rail choices, rail accounts and utility-based welfare are unchanged across central rail designs. This test does not establish invariance under income/electrification shocks or for monetary-cost burden measures, and it does not validate the external tariff's unit.

Optional sentence that can follow the default assumption if the authors wish to report the sensitivity:

```latex
Dividing the van charge by four and recalibrating the reference intercepts leaves the six central commercial and welfare P3 outcomes unchanged, because reference-state road utilities are preserved by construction; this check does not identify the empirical tariff unit or establish invariance under income and road-cost shocks.
```

Reproduction details are included in the appendix below, within this findings file. In-memory modified-input SHA256 hashes were:

| Corridor | Modified raw-input SHA256 |
|---|---|
| HN | `291bc23db813c336dd6839e92723ad288b36e311868bf707defbe7cffe65838c` |
| WC | `c40d016e4d6a2472dde218112982c38c47776ee65956144e5fca6a083b599cc7` |
| JX | `9503b854a44b658f9b4c4e30e5357af6cde439b9b39f927eb53e9fd1836e9705` |

## 3. Unused address [4]

**Finding: this is an unused commented front-matter entry, not an active author affiliation. No new author–institution assignment can be verified from the supplied V6 manuscript.**

Evidence:

- [V6:34](D:/Paper-M/TRA/TRA-R4/TRA-20261016-V6.tex:34) through line 37 contains four **commented-out** author commands. Their example indices are `[1,2]`, `[3]`, `[1]` and `[1]`; none references `[4]`.
- [V6:39](D:/Paper-M/TRA/TRA-R4/TRA-20261016-V6.tex:39) through line 42 contains **commented-out** address commands. Line 42 is the Yanshan entry identified by the CHECK at line 43.
- A search of the entire V6 source found no active `\author`, `\address` or `\affiliation` command and no other assignment to address `[4]`. The commented example names and institutions are not evidence of current authors' confirmed affiliations.

Recommended resolution: omit the unused commented address [4] when cleaning the front matter; do not assign any author to Yanshan University by inference. The complete active author block still requires author-supplied confirmation. No institution or author name has been added here.

Because this item belongs in front matter rather than the paper's prose, the safe proposed LaTeX replacement is a comment:

```latex
% Omit the unused address [4]; include only affiliations confirmed and assigned by the authors.
```

If an author actually requires affiliation `[4]`, there is no verified replacement affiliation to provide from the available material; the author must supply the confirmed name and address. The above omission/comment is the fallback, not an invented affiliation.

## 4. Public repository DOI or URL

**Finding: no verified public identifier was supplied or located in the current package. This CHECK cannot be completed with a real public link without additional author evidence.**

Evidence:

- [V6:815](D:/Paper-M/TRA/TRA-R4/TRA-20261016-V6.tex:815) still contains the literal placeholder `[DOI to be added]`; line 816 requests a repository DOI or URL.
- [exp_v4/交付说明.md:13](D:/Paper-M/TRA/TRA-R4/exp_v4/交付说明.md:13) records that a public repository DOI/URL had not been provided.
- [exp_v4/.git/config:1](D:/Paper-M/TRA/TRA-R4/exp_v4/.git/config:1) through line 8 contains only local core settings and **no remote**. The scoped Git repository is a local provenance archive, not evidence of a public deposit or a DOI.
- Searches of the current R4 manuscript and archive metadata for repository links and Zenodo/Figshare identifiers did not locate an attributable public project deposit. DOIs in the literature bibliography do not identify this project's archive. This is a statement about the supplied materials, not proof that no external repository exists.

Proposed honest fallback for the opening availability sentence, retaining the rest of the existing computational description as appropriate:

```latex
The computational materials are retained in a local archive containing the inputs, scenario definitions, designs and independent verification records; no public repository DOI or URL has been provided.
```

A public-availability claim should be inserted only after a deposited record or repository URL is supplied and checked. No DOI, repository URL, promise of future release or “available on reasonable request” commitment is invented here. The fallback is transparent about the present evidence; it is not a substitute for a journal-mandated public-data deposit.

## Appendix: read-only sensitivity reproduction and integrity

The optional run used Python 3.13.2 and the unchanged engine in `D:/Paper-M/TRA/TRA-R2/experiments_v3_round5`. The raw road charge was changed only in a deep copy, before `Model` invoked the existing `prepare` recalibration. The additional spec key is a provenance annotation; the actual cost change is `road[3][0] /= 4`. The unique case ID prevents the calibration cache from silently returning the default input.

Source hashes checked against the existing V4 provenance manifest:

| Source | SHA256 |
|---|---|
| `model.py` | `17d75f36c673b1dc4e10c35ae138654a4f69df8da0d2e2110c187f9c0ae65177` |
| `calibration.py` | `de5ce4c8eb6bb4b5c1461a9b4047fe8d8791b897f60e0e82ea4ab565abf9090b` |
| `verify.py` | `93c26a443a04950b867a994130f98d5e3808d812ce5eb7ed979c0495b0370173` |
| `exact_single_od.py` | `5bbd8af7099a923d12e0088ff071b6abbcab4041278b7e131efdd450f2bd9700` |
| `copt_backend.py` | `d5ad4071f6784dfed386cc2cc0763a5d3710f9bcd32129998263eefce5fb503a` |
| `run_round5.py` | `f22a99aa1dbb6dca43ee73ae85af6fa72165fc0f869a65d224f6ad2d1d0b8b8c` |

All V3 Python-source and input hashes matched `TRA-R4/exp_v4/provenance.json` after the optional run. The R4 integrity check excludes only this newly created findings file and Git's internal metadata. The **490 pre-existing files** had aggregate SHA256 `30ef1d1059ec859f356aaeb5e3097814865ddd4673669ba0a819412a6c45c7f4` before this task. V6 manuscript SHA256: `39b3b6a53c1e1a6351bf2459bd5afb926101a969f050cbb094f3b0913b56359e`.

The final hash comparison confirmed that all 490 pre-existing R4 files and the V6 manuscript retained the above hashes. Only this findings file was added. No public upload or affiliation assignment was performed.

The executed sensitivity script follows. It prints findings to stdout, does not call a result-writing function, and disables Python bytecode writes. It was executed through stdin from the system temporary directory.



```python
import sys,os,json,copy,time,hashlib
sys.dont_write_bytecode=True
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
BASE=Path('D:/Paper-M/TRA/TRA-R2/experiments_v3_round5')
sys.path.insert(0,str(BASE))
import numpy as np
from model import Model
from analyze import groups,record
from exact_single_od import Exact
from run_round5 import multistart
from verify import scalar
sys.path.insert(0,str(BASE.parent/'experiments_v3_round6'))
from run_round6 import check
out=[]
for ci in ['HN','WC','JX']:
    g=next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none')
    raw=json.loads((BASE/'inputs'/f'{ci}.json').read_text(encoding='utf-8'))
    spec=dict(g['job'].get('spec',{}))
    original=Model(raw,spec=spec)
    altered=copy.deepcopy(raw)
    altered['id']=ci+'_v6_van_occ4_readonly'
    for road in altered['road']:road[3][0]/=4
    config={**spec,'van_occupancy_sensitivity':4}
    m=Model(altered,spec=config)
    one=np.ones((m.S,4,3))
    z=m.evaluate(m.N0,one,True)
    flowerr=float(np.max(abs(z['qr'][0]-np.array(m.c['target_rail']))))
    roaderr=float(np.max(abs(m.roadU-original.roadU)))
    assert flowerr<1e-6 and abs(float(z['maxlf'][0])-.88)<1e-8
    warm=g['records']
    ex=Exact(m,warm) if ci in ['HN','WC'] else None
    forward_errors=[]
    for r0 in warm:
        v=m.record(np.array(r0['N']),np.array(r0['phi']),r0['objective'],r0['policy'])
        forward_errors.append(max(abs(v['profit']-r0['profit']),abs(v['welfare']-r0['welfare'])))
    for obj in ['profit','welfare']:
        start=time.perf_counter()
        if ex:
            result=ex.solve('P3',obj)
            assert result and result.get('success'),result
            r=result['record'];r['policy']='P3';status='optimal';gap=result['gap']
        else:
            r=multistart(m,'P3',obj,warm,strong=True);status='search';gap=None
        err=check(m,r)
        old=record(g,'P3',obj)
        out.append(dict(case=ci,objective=obj,status=status,seconds=time.perf_counter()-start,
            baseline_profit_gain=(old['profit']-original.state_profit)/1000,
            alternative_profit_gain=(r['profit']-m.state_profit)/1000,
            delta_profit_gain=((r['profit']-m.state_profit)-(old['profit']-original.state_profit))/1000,
            baseline_delta_W=old['welfare']/1000,alternative_delta_W=r['welfare']/1000,
            delta_delta_W=(r['welfare']-old['welfare'])/1000,
            retention=r['eta'],retention_change=r['eta']-old['eta'],
            departures=int(np.array(r['N']).sum()),N_identical=bool(np.array_equal(r['N'],old['N'])),
            phi_max_change=float(np.max(abs(np.array(r['phi'])-np.array(old['phi'])))),
            scalar_error=err,reference_flow_error=flowerr,reference_peak_load=float(z['maxlf'][0]),
            road_utility_max_change=roaderr,all_central_saved_forward_max_error=max(forward_errors),
            upper_gap_CNY=gap,config=config,modified_raw_sha256=hashlib.sha256(json.dumps(altered,sort_keys=True).encode()).hexdigest()))
        print(json.dumps(out[-1],ensure_ascii=False),flush=True)
print('FINANCIAL_RATIO',620017169.80/976269370.13*100,flush=True)
```

