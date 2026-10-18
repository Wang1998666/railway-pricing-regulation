"""Write English review responses and reproducibility/delivery records."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;P=HERE.parent
A=json.loads((HERE/'round6_analysis.json').read_text(encoding='utf-8'))
Q=json.loads((HERE/'pdf_qa.json').read_text(encoding='utf-8'))
V=json.loads((HERE/'visual_inspection.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert Q['pdf_sha256']==sha(P/'TRA-20261014-V3.pdf')==V['pdf_sha256'] and V['passed']
assert A['grid_certificates']==60 and A['independent_max_error']<1e-5
assert all(abs(r['welfare']-next(o for o in g['previous'] if o['policy']==r['policy'] and o['objective']=='welfare')['welfare'])<1e-5 for g in A['variants'] for r in g['records'])
rows=[]
for ci in ['HN','WC']:
    for key,label in [('freeze','Cap 1.00, floor 0.95'),('cap105','Cap 1.05, floor 0.95'),('floor100','Cap 1.20, floor 1.00'),('joint105_100','Cap 1.05, floor 1.00')]:
        r=A['summary'][ci][key];rows.append(f"| {ci} | {label} | {r['profit_gain']/1000:,.1f} | {r['welfare']/1000:,.1f} | {r['departures']} |")
response=f'''# Response to the Section 4 review: round 6

15 October 2026. Revised manuscript: TRA-20261014-V3.tex; compiled PDF: {Q['pages']} pages.

## A1. Test caps, floors, their combinations, and the fare-freeze alternative

Implemented the reference HN/WC P3 grid with caps 1.00, 1.05, 1.10, 1.15 and 1.20 and floors 0.95, 0.96, 0.97, 0.98, 0.99 and 1.00. All **60 commercial optima** have COPT finite-menu certificates on the original 0.025 menu. Observed K remains fixed and 50% G/D frequency authority remains the baseline. Each design was independently reconstructed and checked; the largest accounting difference is {A['independent_max_error']:.3g} CNY/day. Nested-domain profit inequalities also pass.

Figure 17 displays the sampled nondominated profit–welfare envelope, collapses coincident outcomes and marks the separately certified reference welfare optima. Insets make the small WC strict-floor tradeoff readable. The figure and text explicitly distinguish this sampled envelope from the full attainable frontier.

Selected outcomes, all certified; monetary entries are gains from same-state P0 in CNY thousand/day:

| Corridor | Regulation | Profit | Welfare | Departures/day |
|---|---|---:|---:|---:|
{chr(10).join(rows)}

A fare freeze reproduces much of the strict-floor welfare benefit, but is not equivalent to the floor. In HN the floor selects 137 departures rather than 138 and retains more profit with less welfare; in WC it improves both relative to the cap-1.00-only outcome. Combining cap 1.05 with floor 1.00 increases welfare above the floor alone by 132.1/3.6 thousand CNY/day in HN/WC, at profit sacrifices of 4.2/0.8. The combinations dominate the cap-1.00-only outcome, but not the same strict-floor-only outcome in both objectives. The abstract, Introduction, Section 4.6, conclusion and policy-implication table now describe corridor-specific tradeoffs. The blanket assertion that the instruments are complementary has been removed.

Evidence: `grid/*.json`, `cap_floor_frontier.csv`, `round6_analysis.json`, Figure 17 and Section 4.6.

## A2. Align the title and framing with the strength of the evidence

Adopted review option **(b)**. The title is now **“Regulated Railway Product, Fare, and Frequency Design under Income and Road-Cost Shocks.”** The abstract and Introduction lead with pricing authority, service consolidation, fare restraint and participation guarantees. Income polarization remains a modeled scenario dimension, rather than the headline empirical finding. Section 4.4 is titled “Income composition and road-cost scenarios.”

The differentiated-seat-pricing extension retains its explicit search-based status; its increments are described as exploratory and are not used to claim a certified effect of polarization. No seat-pricing certificate has been invented or inferred from the common-pricing certificates. The theoretical model and literature review in Sections 2–3 are unchanged.

## A3. Recheck the two Table 9B served-period rows

Re-solved both P3 and P4 welfare designs for the half-schedule-slope/served and 60-minute-cap/served variants, using their own recalibrated models and strong multi-start seeds including the final reference JX designs and paired schedule variants. Independent scalar verification and joint-neighborhood polishing were applied. Frequencies remain exactly unchanged and fare differences are at most numerical roundoff (1.12 × 10⁻¹⁶). The welfare objectives remain unchanged.

The matched P4-minus-P3 ledgers are therefore still:

| Variant | Added K/day | Profit change (k) | Traveler surplus change (k) | Welfare change (k) |
|---|---:|---:|---:|---:|
| Half schedule slope / Served | 1 | −74.6 | 86.1 | 11.5 |
| 60-minute cap / Served | 1 | −46.1 | 48.6 | 2.5 |

These rows compare each variant with its own P3 design; they do not subtract the central JX welfare level. A change in the central reference optimum therefore need not change a matched variant increment. This explanation is now in Section 4.5 and the Table 9 note. The recheck confirms unchanged feasible search outcomes, not global JX optimality.

Evidence: `variants/JX_schedule_half_served.json` and `variants/JX_displacement60_served.json` include old and rechecked physical decisions, objectives and scalar checks.

## A4. Interpret the smaller JX headroom gain

Added a sentence in Section 4.3 connecting JX's 0.315-thousand-CNY normalized headroom gain with its 86.8% departure-weighted fare-cap incidence. The interpretation separates cap-driven commercial gains from calibrated consolidation savings and is stated as consistency with the observed model response, rather than an independently identified causal decomposition.

## A5. State exactly where open problems enter the reported evidence

The 63 unresolved common-pricing problems are **all P4: 47 profit and 16 welfare problems**. The manuscript now explicitly states that some K-entry, stress, withdrawal, floor/budget and design-library/sensitivity summaries use feasible witnesses from this set. `reported_open_scope.csv` maps **all 63 distinct problems** to their publication-input jobs and status; identical physical domains can appear in more than one job. It contains {A['open_job_occurrences']} job-policy-objective occurrences, including {A['open_feasible_occurrences']} feasible-witness occurrences. No unresolved result is labeled optimal.

Central HN/WC P1–P4 outcomes, the HN/WC elasticity–cap profiles, strict P3 floor comparisons and all 60 new cap–floor optima are certified. The separate grid count is not added to the broad-domain ledger as if every new grid domain were distinct from every earlier domain.

For the broader 75-state screen, the six states lacking P3/P4 witnesses are now distinguished explicitly. P3 is certified infeasible in all six. P4 is certified infeasible in the three WC states; the other three are HN states at polarization scale 1.50 and road intensities 0, 0.25 and 0.50 where the master reached its time limit without a feasible witness. Their feasibility remains open. Missing witnesses are not treated as infeasibility certificates.

Evidence: `reported_open_scope.csv`, `round6_analysis.json`, the original `main/certification_scope.csv`, Sections 4.4 and 4.7.

## A6. Explain the HN strict-floor outcome

Section 4.6 now explains the selected certified operating response: HN restores eight of eighteen commercially consolidated departures, retains 137 departures against 138 under a fare freeze, and uses a near-reference but nonuniform fare pattern. The participation target is met, while 9.1% of the commercial traveler-surplus loss remains. This accounts for the 90.9% recovery being below the WC/JX figures; the strict floor is not a requirement to reproduce every reference fare and departure.

## B. Abstract, method length and figures

Removed the defensive per-trip-budget sentence from the abstract and replaced the unsupported complementarity conclusion with the grid finding. Condensed the solution-evidence paragraph in Section 4.2 to four sentences. Filtering, reduced-cost screening, pooled-K equivalence, tolerances, limits and cached-certificate provenance are documented in the data/code statement and reproducibility package. Figure 14 is retained, as its remaining low-count faintness was accepted. Existing Figures 3–16, including Figure 4(a) and the original TikZ workflow, are unchanged.

## Additional requested revision: computing environment and solver roles

Section 4.2 explicitly reports 64-bit Windows 11 Pro, AMD Ryzen 7 4800H (8 physical cores/16 logical processors), 16 GB RAM with 15.37 GiB reported physical memory, Python 3.13.2, NumPy 2.5.0 and SciPy 1.18.0. **COPT 8.0.6 through coptpy 8.0.6** solves the enumerated HN/WC binary integer masters. **HiGHS 1.12.0 through SciPy** solves continuous LP relaxations for screening. JX and seat-specific pricing use custom coordinated multi-start search and independent local audits; COPT does not globally solve those nonlinear problems.

The main batch uses eight worker processes; this focused round-six batch uses four. COPT and numerical-library threading are limited to one thread per worker. The data/code statement and environment record specify zero relative MIP gap, COPT absolute gap 10⁻⁹ on thousand-CNY-scaled objectives, feasibility/dual tolerances 10⁻⁹, master limits of 120/180 seconds with up to 600 seconds for priority recertification, and a 30-second LP limit. Certification additionally requires feasibility under the original evaluator and bound agreement within 0.01 CNY/day. Compatible previously cached proofs retain their originating solver provenance, including earlier SciPy/HiGHS MILP certificates; a time limit is never treated as a certificate.

## Delivery verification

The final {Q['pages']}-page PDF compiles successfully. All pages were rendered and visually reviewed; detailed checks cover the solver/environment paragraph, revised Table 9 note, cap–floor prose, Figure 17 and conclusion/data-code statement. There are no unresolved references, new case-study numbered equations or longtables. The only two overfull warnings are the pre-existing protected model/layout warnings. Figure 3 and the TikZ workflow match their preserved hashes; Figure 4(a) and all existing figure files are unchanged. All checks refer to the delivered PDF hash recorded in `pdf_qa.json` and `visual_inspection.json`.
'''
(P/'REVIEW_RESPONSE_V3_round6_20261015_EN.md').write_text(response,encoding='utf-8')
readme='''# Round-six reproducibility package

This package adds focused review experiments to the validated round-five engine. It does not overwrite its solver, records or certificate ledger. The final manuscript remains `../TRA-20261014-V3.tex` and its PDF. The preceding final manuscript/PDF/tables are backed up in `../archive/before_round6_20261015/`.

## Computation

- `run_round6.py`: 60 HN/WC reference P3 profit optima, five caps × six floors × two corridors; four-process batch, one numerical/solver thread per process. Also rechecks the two JX served-period P3/P4 welfare pairs. Incomplete grid files are recomputed on restart.
- Engines are imported from `../main/`: `model.py`, `exact_single_od.py`, `copt_backend.py`, period kernels, local audits and independent scalar evaluator. The main round-five run used eight processes.
- All grid points have COPT finite-menu optimality certificates. Each model keeps observed K fixed, 50% G/D authority, the 0.025 menu and all original fleet, occupancy, finance and participation constraints. Exhaustive per-period fare/frequency columns are coupled by a binary daily master. Column filtering and LP reduced-cost screening preserve attainable optima.
- `analyze_round6.py` reconstructs all 60 records in their exact cap/floor domains, snapshots metadata, checks accounting independently, tests nested-domain profit ordering and creates the grid CSV/plot. `cap_floor_frontier.csv` is the complete sampled policy grid; the nondominated envelope is not the full attainable design frontier.
- `variants/*.json`: both old and rechecked physical decisions and values. The variant's own recalibrated P3 is its comparator; the central JX welfare number is not its denominator.
- `reported_open_scope.csv` maps every one of the original 63 open problems to all corresponding main publication-input jobs. All are P4; feasible records remain witnesses, and absent witnesses remain open. The new P3 grid does not resolve these P4 problems.

## Actual environment and solver roles

See `environment.json` for exact versions/settings. Windows 11 Pro 64 bit; Ryzen 7 4800H, 8 physical cores and 16 logical processors; reported physical RAM 16,505,966,592 bytes (~15.37 GiB), nominal 16 GB. Python 3.13.2, NumPy 2.5.0, SciPy 1.18.0, coptpy/COPT 8.0.6. SciPy's bundled HiGHS runtime reports version 1.12.0.

COPT solves the exact enumerated binary masters for HN/WC common pricing. SciPy/HiGHS `linprog` supplies continuous LP relaxations and valid reduced-cost bounds. JX and differentiated seat fares use the custom multi-start joint fare–frequency search, with independent scalar and joint-neighborhood checks; there is no COPT global nonlinear certificate for them. Earlier compatible cached HN/WC certificates retain their original SciPy/HiGHS MILP provenance; the round-six grid itself was solved with COPT.

COPT: Threads=1, RelGap=0, AbsGap=1e-9, FeasTol=1e-9, DualTol=1e-9. Master objectives are scaled by 1,000 CNY. Standard relaxed-bound/hard-master time limits are 120/180 seconds, priority fallback up to 600 seconds. HiGHS LP screen: 30 seconds, one thread, primal/dual tolerances 1e-9. Independently reconstructed feasibility and certificate gap <0.01 CNY/day are required in addition to optimal master status. Time limits are never treated as proof of optimality or infeasibility. OPENBLAS_NUM_THREADS, MKL_NUM_THREADS and OMP_NUM_THREADS are all 1.

## Reproduce in PowerShell

```powershell
& 'C:\\Python313\\python.exe' -u 'D:\\Paper-M\\TRA\\TRA-R2\\policy_grid\\run_round6.py' --workers 4
& 'C:\\Python313\\python.exe' 'D:\\Paper-M\\TRA\\TRA-R2\\policy_grid\\analyze_round6.py'
& 'C:\\Python313\\python.exe' 'D:\\Paper-M\\TRA\\TRA-R2\\policy_grid\\write_round6.py'
Set-Location 'D:\\Paper-M\\TRA\\TRA-R2'
latexmk -pdf -interaction=nonstopmode -halt-on-error TRA-20261014-V3.tex
& 'C:\\Python313\\python.exe' 'D:\\Paper-M\\TRA\\TRA-R2\\policy_grid\\qa_round6.py'
```

`write_round6.py` starts from the final round-five manuscript snapshot, so running it is deterministic. Do not run an older round-five manuscript writer after the round-six writer. `qa_round6.py` renders every page and verifies preservation/reference/layout constraints. Visually inspect the latest previews and record their PDF hash in `visual_inspection.json` before running `finalize_round6.py`.

## Audit files

- `run_manifest.json`: execution batch counts and engine/controller fingerprints.
- `round6_analysis.json`: independent errors, selected outcomes, sampled nondominated points, open-domain classifications and JX rechecks.
- `pdf_qa.json`, `visual_inspection.json`, `delivery_checks.json`: delivered-PDF and preservation verification.
- `artifact_manifest.json`: final source/results/manuscript/figure fingerprints.

The package adds a separate 60-point fully certified grid; do not sum it with the original 2,583 certificates as if none of the domains overlapped. Existing broad-domain open P4 problems and JX/seat-pricing global-optimality limitations remain explicitly disclosed.
'''
(HERE/'README.md').write_text(readme,encoding='utf-8')
checks=dict(passed=True,grid_certificates=60,independent_max_error=A['independent_max_error'],variant_objectives_unchanged=True,open_scope_complete=Q['open_scope_complete'],sections_2_3_unchanged=True,pdf_pages=Q['pages'],pdf_sha256=Q['pdf_sha256'],visual_passed=True,protected_sha256=Q['protected_sha256'])
(HERE/'delivery_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
files=[p for p in HERE.rglob('*') if p.is_file() and 'preview' not in p.parts and '__pycache__' not in p.parts and p.name!='artifact_manifest.json']
files += [P/'TRA-20261014-V3.tex',P/'TRA-20261014-V3.pdf',P/'REVIEW_RESPONSE_V3_round6_20261015_EN.md',P/'Fig/round6_frontier.pdf',P/'Fig/round6_frontier.png',P/'tables/v3_events.tex',P/'tables/v3_findings.tex']
(HERE/'artifact_manifest.json').write_text(json.dumps({str(p.relative_to(P)):sha(p) for p in sorted(files)},indent=2),encoding='utf-8')
print('Round-six delivery checks passed; English response and README written.')
