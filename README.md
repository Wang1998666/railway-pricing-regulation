# Railway pricing and scheduling — code and data

Public repository: [Wang1998666/railway-pricing-regulation](https://github.com/Wang1998666/railway-pricing-regulation).

This repository contains the computational code, source data, archived results, and fare collection workflows accompanying the final manuscript of **Regulating Commercial Discretion in Railway Pricing and Scheduling: Fare Caps, Mobility Guarantees and Frequency Delegation**.

Archive preparation date: **2026-10-18 (Asia/Shanghai)**. Directories are organized by function. Preparation involved copying files, updating path references, and performing static checks. **No experiments, solvers, plotting scripts, or data collection workflows were rerun.** The original project files were left unchanged.

## Repository structure

```text
.
├── experiments/
│   ├── main/                 # Core model, calibration, inputs, experiments, and results
│   ├── policy_grid/          # Fare-cap and trip-retention policy grid
│   └── supplementary/        # Latest supplementary experiments and analyses
├── data/
│   └── corridors/            # Source snapshots, configurations, and upstream cases
├── data_collection/          # Rail fare, Amap road, and station-access data collection
├── preprocessing/            # Upstream case construction and data audits
├── visualization/
│   ├── main_figures/         # Archived main-experiment figures
│   ├── case_figures/         # Case-study plotting code and figure assets
│   └── model_diagrams/       # Model diagram sources
├── tables/
│   ├── main/                 # Main-experiment tables
│   └── supplementary/        # Supporting tables for supplementary analyses
├── reference_figures/        # The final manuscript's 17 PDF figures
├── editorial/                # Historical text and figure-label revision support
├── metadata/                 # Provenance, file manifests, layout mapping, and checks
├── requirements-computation.txt
├── requirements-optional.txt
└── README.md
```

Within `experiments/main/`, `inputs/` contains calibration input templates, `runs/` contains grouped experiment results, and `states/` contains deduplicated solver states. `historical_baseline/` holds historical audit material and is not an entry point for the final model. Some script filenames retain their original names to preserve links to archived records.

## Archive version selection

| Component | Directory | Latest result-file modification time (Asia/Shanghai) | Contents |
| --- | --- | --- | --- |
| Main experiments | `experiments/main/` | 2026-10-15 20:29:48 | Core model, 966 experiment groups, and 840 deduplicated solver states |
| Policy grid | `experiments/policy_grid/` | 2026-10-15 22:21:59 | Original 60-point fare-cap/trip-retention grid and supplementary checks |
| Latest supplements | `experiments/supplementary/` | 2026-10-16 16:27:42 | Refined policy grid, indicator decomposition, cross-state evaluation, and elasticity experiments |

These are filesystem timestamps, not exact process completion times. During initial archive preparation, all 76 main-experiment source hashes and seven input hashes recorded in the supplementary provenance manifest matched the selected original files. Later manuscript edits do not imply that the model was rerun.

Directory reorganization changed path references and documentation only; source data, numerical results, and core model algorithms were preserved. See [selection_evidence.json](metadata/selection_evidence.json), [file_manifest.csv](metadata/file_manifest.csv), and [layout_migration.json](metadata/layout_migration.json) for provenance and directory mappings. Old paths in historical reports identify their original locations.

## Main code and results

- `experiments/main/model.py` and `calibration.py`: demand response, objectives, constraints, and scenario calibration.
- `experiments/main/run_round5.py`: main-experiment orchestration, deduplication over complete decision domains, and caching.
- `experiments/main/exact_single_od.py` and `copt_backend.py`: single-OD finite-menu enumeration, COPT master problems, and LP screening.
- `experiments/main/period_kernel.py`, `fast_evaluator.py`, and `pareto_kernel.py`: computational acceleration.
- `experiments/main/verify.py` and `local_review_audit.py`: independent scalar verification and local-neighborhood audits.
- `experiments/policy_grid/run_round6.py`: policy-grid computation; results are summarized in `cap_floor_frontier.csv`.
- `experiments/supplementary/exp1.py` through `exp4.py`: the latest supplementary experiments. `checks_and_exp5.py` contains the archived factual and cost-allocation checks.

For the main results, start with `experiments/main/round5_analysis.json`, `certification_scope.csv`, `commercial_profile.csv`, and `cap_floor_tradeoff.csv`. Supplementary results are documented in `experiments/supplementary/RESULTS_V4.md`, with supporting files in `exp1/grid.csv`, `exp2/analysis.json`, `exp3/cross_eval.csv`, and `exp4/elasticity_ext.csv` under that directory.

Optimality claims are limited to the archived certificate ledger. A time-limited solve is not proof of optimality or infeasibility. Searches for JX and seat-specific pricing do not establish global optimality. Successive policy grids overlap, so their counts must not be added as if all problems were unique.

## Data and fare sources

`data/corridors/` contains the Hangzhou–Nanjing (HN), Wuhan–Changsha (WC), and Jiangxi multi-OD (JX) corridors. Archived rail queries cover travel dates from **2026-08-03 through 2026-08-09**, with **2026-08-05** as the reference date. Travel dates and collection timestamps are distinct; consult the configurations and the raw JSON `collected_at_utc` field where available.

Each corridor's `raw_data/` directory contains:

- `*_trains_YYYYMMDD.csv` and `*_prices_YYYYMMDD.csv`: timetables and published fares.
- `*_rail_raw_YYYYMMDD.json`: archived responses and error records.
- `*_amap_od.csv`, `*_amap_access.csv`, and `*_amap_raw.json`: Amap road and station-access snapshots.
- `*_road_passenger.csv`, `*_access_fares.csv`, and `*_road_cost_rules.json`: derived monetary attributes and their calculation rules.

`data_collection/collect_rail_12306.py` calls the bundled client's `query_tickets_validated` and `query_ticket_price_validated` functions to save timetables, fares, and raw JSON. The client is included in `data_collection/vendor/mcp-server-12306/`; its archived fare-query endpoint is `leftTicketPrice/queryAllPublicPrice`. Its original license is retained.

`experiments/main/build_inputs.py` constructs products by train tier, stopping coverage, and departure period. It uses medians of available published fares and explicitly specified inherited values or ratio-based imputations for missing seat classes. Final scenarios are further calibrated in `calibration.py`; not every input is a direct observation.

`data_collection/collect_road_amap.py` obtains distances, route-planning times, tolls, and access attributes, then applies cost rules for private cars, coaches, MaaS, business vans, and station access. **These derived costs are not observed market transaction fares supplied by Amap.** Coefficients are documented in each corridor's cost rules and the calibration code. `data/corridors/SOURCE_LEDGER_CN.md` distinguishes observed, derived, calibrated, and scenario inputs.

## Amap API key

**The author's Amap key is not included. Users must supply their own Amap Web Service key.** For example:

```powershell
$env:AMAP_API_KEY = "YOUR_OWN_AMAP_WEB_SERVICE_KEY"
```

Alternatively, copy `data_collection/.env.example` to `.env` in the same directory and enter your own key. Do not commit the completed file. An Amap key is not required for offline computation using the archived inputs.

Booking windows, dynamic fares, and API changes affect fresh collection. Use the archived snapshots when checking the paper's results. To collect a new dataset, copy a corridor configuration to a new output directory, set its `query_date` to an available travel date, and use the same date for the rail collector's `--date` argument. Then collect Amap attributes. From the repository root, for example:

```powershell
python -m pip install -r .\data_collection\requirements.txt
python .\data_collection\collect_rail_12306.py --config .\new_data\corridor_config.json --output-dir .\new_data --date YYYY-MM-DD
python .\data_collection\collect_road_amap.py --config .\new_data\corridor_config.json --output-dir .\new_data
```

## Software environment and entry points

The recorded environment was Windows 11 (64-bit), Python **3.13.2**, NumPy **2.5.0**, SciPy **1.18.0**, Matplotlib **3.11.0**, PyMuPDF **1.28.0**, and COPT/coptpy **8.0.6**, with HiGHS **1.12.0** inside SciPy. Versions, thread settings, and tolerances are recorded in `experiments/policy_grid/environment.json`. Solving requires the user's own valid COPT license.

Core dependencies are listed in `requirements-computation.txt`, optional plotting and mapping dependencies in `requirements-optional.txt`, and collection dependencies in `data_collection/requirements.txt`. The commands below document existing entry points; **they were not run during archive preparation**. They may reuse or update cached results, so use a complete working copy.

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

`step0.py` performs computational checks and any required solves; it is separate from the static archive checks. Historical manuscript-generation, compilation, and layout-checking scripts may depend on manuscripts or backups that are not included. They are not a one-command build of the final paper. See [PORTABILITY.md](metadata/PORTABILITY.md) for plotting and path details. No fresh environment installation or end-to-end reproduction was performed during archive preparation.

## Verification and provenance

`reference_figures/` preserves the final manuscript's 17 PDF figures. Sixteen have exact hash matches among the archived experiment figures; no upstream PDF with an identical hash was found for Figure 1. See `metadata/final_figure_sources.json`.

`metadata/file_manifest.csv` records original sources and current paths. `layout_migration.json` documents directory changes and file modifications, and `packaging_checks.json` records static checks. `SHA256SUMS.txt` covers the current archive files, excluding itself. Historical logs and scientific reports retain their original provenance context; use this README and the metadata for current paths.

The public repository is linked above. No DOI or new author license has been created; third-party code retains its original license.
