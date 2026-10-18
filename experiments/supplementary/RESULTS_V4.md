# RESULTS V4 — 16 October 2026



All requested experiments and the optional cost-split extraction are complete. Outputs are confined to TRA-R3/exp_v4. The supplied V4 manuscript, all original tables, and the V3 model/calibration/solver/verification sources remain unchanged. Money below is thousand CNY/day for one direction unless stated. Full precision is retained in CSV/JSON. The most consequential changes are WC sub-unit-floor dominance and the positive WC commercial welfare result at elasticity −1.50.

The V3 source folder was not a Git repository. A scoped Git repository was created in exp_v4; commits, source/input SHA256 hashes, configuration hashes, statuses, runtimes and design identifiers accompany the supplement. This does not invent a historical V3 commit. `common.py` derives y and period activity u from N for hashing; full N and phi are saved. Solver tolerances and limits are inherited unchanged from V3.



## Step 0 — regression

PASS. 32 numerical checks; 12 optimal and 4 search design reruns; 0 infeasible and 0 open.

| Corridor | Commercial profit gain | Commercial ΔW | L retention | Welfare-P3 ΔW |
| --- | --- | --- | --- | --- |
| HN | 1585.2 | -398.9 | 0.98106307 | 562.2 |
| WC | 1788.8 | -709.7 | 0.98824325 | 769.6 |
| JX | 1598.4 | -941.2 | 0.99323558 | 833.7 |

Verdict: all required reference quantities reproduce within the specified tolerances, including WC welfare profit 852.5, welfare 769.6 and retention 0.999753881.

The first local runner omitted the JX cap-1.10 E16 incumbent and failed two search checks. New experiments remained stopped. That runner was corrected to reuse the unchanged V3 collector’s complete state-specific seeds; the corrected regression passed before EXP-1–4 began. An intermediate collector lookup for an exact-only round6 state was also corrected. Both diagnostic logs are retained in step0_initial_seed_audit; no model defaults or numerical targets were changed. Every final Step 0 row has a pass/fail entry in step0_regression.csv and step0.log.



## EXP-1 — refined cap–floor grid

PASS. 78 optimal / 0 infeasible / 0 open / 0 search (70 commercial + 8 welfare).

| Corridor | Cap | Floor | Profit gain | ΔW | Retention |
| --- | --- | --- | --- | --- | --- |
| HN | 1.20 | 0.9950 | 924.7 | 278.1 | 0.99500905 |
| HN | 1.20 | 0.9990 | 682.7 | 502.4 | 0.99900170 |
| HN | 1.20 | 0.9995 | 626.7 | 490.1 | 0.99953320 |
| HN | 1.20 | 1.0000 | 569.9 | 388.9 | 1.00008851 |
| HN | 1.05 | 0.9950 | 822.6 | 279.6 | 0.99500051 |
| HN | 1.05 | 0.9990 | 640.3 | 483.8 | 0.99905553 |
| HN | 1.05 | 0.9995 | 624.1 | 513.5 | 0.99953033 |
| HN | 1.05 | 1.0000 | 565.7 | 521.0 | 1.00004120 |
| WC | 1.20 | 0.9950 | 1286.1 | 106.0 | 0.99500146 |
| WC | 1.20 | 0.9990 | 979.6 | 683.9 | 0.99912635 |
| WC | 1.20 | 0.9995 | 922.9 | 769.3 | 0.99958959 |
| WC | 1.20 | 1.0000 | 757.0 | 730.4 | 1.00000642 |
| WC | 1.05 | 0.9950 | 1129.9 | 167.5 | 0.99534262 |
| WC | 1.05 | 0.9990 | 895.3 | 631.8 | 0.99909778 |
| WC | 1.05 | 0.9995 | 891.7 | 724.1 | 0.99957320 |
| WC | 1.05 | 1.0000 | 756.2 | 734.0 | 1.00001536 |

Verdict: sub-unit floors dominate the strict floor alone in both corridors; WC cap 1.20/floor 0.9995 also dominates the cap-1.05/strict-floor combination. The latter remains sampled nondominated in HN.

| Corridor | Distinct V3 / 30 | Distinct refined / 35 | Floors admitting central W optimum at cap 1.20 |
| --- | --- | --- | --- |
| HN | 11 | 21 | 0.9800, 0.9850, 0.9900, 0.9950, 0.9990, 0.9995, 1.0000 |
| WC | 10 | 20 | 0.9800, 0.9850, 0.9900, 0.9950, 0.9990, 0.9995 |

Numerical binding is defined exactly as requested, retention − floor < 1e-6 after integer optimization: the only binding sampled point is HN cap 1.05/floor 0.995. No WC point is binding at this tolerance. This does not mean all other floors are irrelevant: integer choices leave slack after a floor forces a different design. The first floor affecting each cap and the sampled nondominated set are tabulated below.

| Corridor | Cap | First design change from floor 0.98 | First numerically binding floor |
| --- | --- | --- | --- |
| HN | 1.00 | 1.0 | none |
| HN | 1.05 | 0.995 | 0.995 |
| HN | 1.10 | 0.99 | none |
| HN | 1.15 | 0.985 | none |
| HN | 1.20 | 0.985 | none |
| WC | 1.00 | 1.0 | none |
| WC | 1.05 | 0.999 | none |
| WC | 1.10 | 0.995 | none |
| WC | 1.15 | 0.99 | none |
| WC | 1.20 | 0.99 | none |

| Corridor | Cap | Floor | Profit gain | ΔW | W optimum share (%) |
| --- | --- | --- | --- | --- | --- |
| HN | 1.05 | 0.9995 | 624.1 | 513.5 | 91.3 |
| HN | 1.05 | 1.0000 | 565.7 | 521.0 | 92.7 |
| HN | 1.10 | 0.9950 | 885.5 | 295.0 | 52.5 |
| HN | 1.10 | 1.0000 | 565.7 | 521.0 | 92.7 |
| HN | 1.15 | 0.9800 | 1493.1 | -280.4 | -49.9 |
| HN | 1.15 | 0.9850 | 1417.3 | -127.5 | -22.7 |
| HN | 1.15 | 0.9950 | 924.7 | 278.1 | 49.5 |
| HN | 1.15 | 0.9990 | 682.7 | 502.4 | 89.4 |
| HN | 1.15 | 1.0000 | 565.7 | 521.0 | 92.7 |
| HN | 1.20 | 0.9800 | 1585.2 | -398.9 | -71.0 |
| HN | 1.20 | 0.9850 | 1445.8 | -144.1 | -25.6 |
| HN | 1.20 | 0.9900 | 1199.5 | 90.2 | 16.0 |
| HN | 1.20 | 0.9950 | 924.7 | 278.1 | 49.5 |
| HN | 1.20 | 0.9990 | 682.7 | 502.4 | 89.4 |
| WC | 1.05 | 0.9800 | 1129.9 | 167.5 | 21.8 |
| WC | 1.05 | 0.9850 | 1129.9 | 167.5 | 21.8 |
| WC | 1.05 | 0.9900 | 1129.9 | 167.5 | 21.8 |
| WC | 1.05 | 0.9950 | 1129.9 | 167.5 | 21.8 |
| WC | 1.10 | 0.9800 | 1510.8 | -345.2 | -44.9 |
| WC | 1.10 | 0.9850 | 1510.8 | -345.2 | -44.9 |
| WC | 1.10 | 0.9900 | 1510.8 | -345.2 | -44.9 |
| WC | 1.10 | 0.9950 | 1199.7 | 165.8 | 21.5 |
| WC | 1.15 | 0.9800 | 1732.9 | -607.1 | -78.9 |
| WC | 1.15 | 0.9850 | 1732.9 | -607.1 | -78.9 |
| WC | 1.15 | 0.9950 | 1286.1 | 106.0 | 13.8 |
| WC | 1.20 | 0.9800 | 1788.8 | -709.7 | -92.2 |
| WC | 1.20 | 0.9850 | 1788.8 | -709.7 | -92.2 |
| WC | 1.20 | 0.9900 | 1667.9 | -419.3 | -54.5 |
| WC | 1.20 | 0.9950 | 1286.1 | 106.0 | 13.8 |
| WC | 1.20 | 0.9990 | 979.6 | 683.9 | 88.9 |
| WC | 1.20 | 0.9995 | 922.9 | 769.3 | 100.0 |

The WC 100.0% welfare share is rounded: the design is 0.3435 thousand CNY/day below the welfare optimum. Dominance compares full-precision values with a 1e-8 thousand-CNY tolerance. The frontier is sampled, not the full feasible frontier.

Draft LaTeX (`latex_insertions/exp1_v4.tex`):

```latex

The refined grid crosses five caps with seven participation floors from 0.98 to 1.00, producing 70 proven-optimal commercial designs and eight proven-optimal welfare benchmarks. These commercial points represent 21 distinct HN designs and 20 distinct WC designs, compared with 11 and 10 in the original grid. At cap 1.20, floors of 0.995 and 0.999 yield profit/welfare gains of 924.7/278.1 and 682.7/502.4 thousand CNY/day in HN, and 1,286.1/106.0 and 979.6/683.9 in WC. With cap 1.05, the corresponding gains are 822.6/279.6 and 640.3/483.8 in HN, and 1,129.9/167.5 and 895.3/631.8 in WC. Under the numerical binding tolerance of $10^{-6}$, only HN at cap 1.05 and floor 0.995 is binding among these sampled optima; elsewhere integer adjustments leave positive slack even when tightening the floor changes the chosen design.

A sub-unit floor can improve both objectives relative to strict retention. In HN, cap 1.20 with floor 0.999 yields 682.7 thousand CNY/day of profit gain and 502.4 of welfare gain, exceeding 569.9 and 388.9 under the strict floor alone, although it does not dominate the cap-1.05/strict-floor combination. In WC, cap 1.20 with floor 0.9995 yields gains of 922.9 and 769.3, exceeding both strict-floor designs under caps 1.20 and 1.05. Its welfare is only 0.3 thousand CNY/day below the central welfare optimum. The WC welfare optimum itself is feasible at floor 0.9995, since its retention ratio is 0.999754. Thus the cap-1.05/strict-floor combination remains sampled nondominated in HN but is dominated on the refined WC grid.

```

Other V4 changes: line 669 should describe the refined 70-point grid and 41 distinct designs; line 678 must restrict the nondominance claim to HN; line 680 can now cite an actual commercial sub-unit-floor design. Add the WC result to the abstract (65), main findings (775), and regulatory implication 3 (785). Figure 13 caption (688) must distinguish the new refined grid from the five V3 cap-only reference points. The original strict-floor numbers remain valid. Surprising: almost all floor-constrained discrete optima are numerically slack.



## EXP-2 — cost-ratio diagnostics

PASS. 1,842 forward evaluations; no optimization. Optimal / infeasible / open / search solve counts: 0 / 0 / 0 / 0.

| Diagnostic | Result |
| --- | --- |
| Argmax class, all OD-period cells | H 100.0%; M 0.0%; L 0.0% |
| Argmax class, design worst-case cell | H 100.0%; M 0.0%; L 0.0% |
| Lower-left designs with L trip loss | 341/341 = 100.0% |
| Lower-left designs with H argmax | 341/341 = 100.0% |
| Fixed-weight cost ratio does not fall | 17/341 = 5.0% |
| Common reference in-vehicle VOT | 97.6 CNY/hour |

| Metric | Cost↓, L↓ | Cost↓, L↑ | Cost↑, L↓ | Cost↑, L↑ | On axis |
| --- | --- | --- | --- | --- | --- |
| Original worst-case G | 341 | 460 | 600 | 225 | 216 |
| L ratio at common VOT | 660 | 395 | 308 | 242 | 237 |
| L monetary cost/trip | 728 | 420 | 284 | 268 | 142 |
| Fixed-weight G | 327 | 476 | 614 | 209 | 216 |

Verdict: both mechanisms are supported in a qualified sense—H dominates the index throughout, while participation-composition change is necessary for the cost-ratio decline in 17/341 lower-left designs; L exit co-occurs in all 341 but does not explain every decline.

Aggregation and definitions: Fig. 15 uses max over (w,h) of max over classes of g_n/gbar_wh. L common-VOT burden uses max over (w,h) of g_L/gbar at common valuations; L monetary burden is the trip-weighted daily L mean. Fixed weights are same-state P0 participation weights within each OD-period. Common valuations are population-weighted at the central reference calibration and held fixed across configurations, including monetary-sensitivity robustness cases. Choice probabilities are evaluated under the original model. All burden changes are relative to each library design’s same-state P0. Near-zero classification uses 1e-7 for ratio changes and L-retention changes; monetary changes use 1e-7 CNY. Ties split equally, although no class ties occur. Canonical K pooling and feasibility follow the original library, which is a union over tested configurations. Source: model.py:174–187,214; analyze_review.py:34–63; figures_round5.py:173–177. Independent scalar maximum error is 6.71e-08 CNY/flow units.

Draft LaTeX (`latex_insertions/exp2_v4.tex`):

```latex

Forward evaluation of the same 1,842 unique feasible designs shows that class H attains the maximum generalized-cost ratio in every OD--period cell and at every design's worst-case cell. All 341 lower-left designs reduce low-income trips. Holding the class participation weights fixed at their same-state P0 values prevents the cost ratio from falling in 17 of these designs (5.0%), demonstrating a composition effect in that subset. In the remaining 324, the cost ratio still falls at fixed weights, so low-income exit alone does not explain the decline. These are accounting comparisons within the evaluated library, rather than causal estimates.

Using a common reference in-vehicle VOT of 97.6 CNY/h for all classes, together with common population-weighted reference valuations for other time attributes, the L-specific generalized-cost ratio falls while L participation falls in 660 designs. The corresponding counts are 728 for L's mean monetary cost per realized trip and 327 for the fixed-weight version of the original ratio. The diagnostics therefore support both high-VOT-class dominance of the original index and a participation-composition effect in a smaller subset; monitoring L participation remains necessary alongside realized-traveler burden measures.

```

Other V4 changes: replace the mechanism paragraph at line 696 and EXP-2 comments at 697–702. The 341/1,842 frequency in line 694 remains valid. The abstract (65) and conclusion (775,789) should identify G as an H-attained relative-cost index, without suggesting that L exit generally causes it to improve. Surprising: the argmax is H in every evaluated cell. No optional Fig. 15 panel was added.



## EXP-3 — seat-pricing cross-evaluation

PASS. Six retained seat-pricing designs are search results; zero new search solves were required. Six cross-evaluated candidate designs violate capacity; this is not a proof of problem infeasibility.

| Corridor | Target state | Cross max load | Cross feasible | Seat increment | H premium share (%) |
| --- | --- | --- | --- | --- | --- |
| HN | uniform | 0.960509 | False | 395.8 | 36.6 |
| HN | polarized | 1.061503 | False | 169.6 | 38.3 |
| WC | uniform | 0.960350 | False | 576.2 | 28.7 |
| WC | polarized | 1.158120 | False | 156.5 | 30.5 |
| JX | uniform | 0.953559 | False | 264.7 | 26.2 |
| JX | polarized | 1.057463 | False | 80.3 | 26.9 |

| Corridor | Common profit: uniform→polarized | Seat profit: uniform→polarized |
| --- | --- | --- |
| HN | 71.5 | -154.7 |
| WC | 95.2 | -324.5 |
| JX | 92.1 | -92.3 |

| Corridor | State | Mean seat 0 multiplier | Mean seat 1 multiplier | Mean seat 2 multiplier |
| --- | --- | --- | --- | --- |
| HN | uniform | 1.0351 | 1.0830 | 1.1132 |
| HN | polarized | 1.0386 | 1.0750 | 1.0915 |
| WC | uniform | 1.0027 | 1.0479 | 1.0752 |
| WC | polarized | 1.0134 | 1.0348 | 1.0521 |
| JX | uniform | 1.0851 | 1.1291 | 1.1815 |
| JX | polarized | 1.0944 | 1.1310 | 1.1614 |

Seat indices follow the archived G/D seat arrays: 0 is the highest fare tier; 2 exists for G only. Means are weighted by departures of products offering that seat. H premium share is premium H rail trips divided by all H rail trips, using the source product premium flags. Cross-evaluations pass finance, floor, fleet and structure, and fail only the 0.95 seat-load ceiling. Saved final designs pass the existing scalar and domain checks; all seat profits exceed corresponding common-pricing incumbents. The optional exact seat-pricing solve was not attempted: raw candidate counts are saved, but the existing exact engine’s two-fare enumeration does not support seat-specific dominance filtering, so no unsupported tractability claim is made.

Verdict: the reported reversal survives the specified cross-check without numerical changes; capacity-driven seat rebalancing is visible, but global seat-pricing optima remain unproven.

Draft LaTeX (`latex_insertions/exp3_v4.tex`):

```latex

Cross-evaluating each uniform-income seat-specific design under polarized income, and each polarized-income design under uniform income, produces six infeasible candidates: every candidate exceeds the 0.95 seat-load ceiling, although finance, participation and fleet constraints are satisfied. No feasible cross-evaluated design improves the reported incumbent, so no additional search is triggered and the reported seat-pricing increments remain 395.8/169.6, 576.2/156.5 and 264.7/80.3 thousand CNY/day under uniform/polarized income in HN, WC and JX. Every retained seat-specific incumbent also exceeds its corresponding common-pricing incumbent.

The saved designs show that income composition changes which seat capacities are scarce. Moving the uniform-income seat-specific design to the polarized state raises maximum seat loads to 1.062, 1.158 and 1.057 in HN, WC and JX. In the retained polarized designs, the departure-weighted lowest G/D seat-class multipliers are lower, while the premium-seat share of H rail travelers is higher. These patterns are consistent with capacity-driven rebalancing of seat prices, but the cross-evaluations do not establish global seat-pricing optima. The reversal remains a comparison of best designs found by search, rather than a proven effect of income dispersion.

```

Other V4 changes: replace speculative last sentences at line 730 and EXP-3 comments at 731–736 with the qualified explanation. Figure 11 is not regenerated because its numbers are unchanged. Surprising: every cross-state design, including polarized→uniform, violates seat capacity.



## EXP-4 — wider elasticity range

PASS. 16 optimal / 0 infeasible / 0 open / 8 search (18 commercial and 6 welfare cases).

| Corridor | Anchor | Cap | Profit gain | ΔW | Mean G/D | At-cap cells (%) | L retention | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HN | -1.20 | 1.10 | 946.2 | -157.0 | 1.0849 | 50.0 | 0.984189 | optimal |
| HN | -1.20 | 1.20 | 1069.8 | -336.3 | 1.1084 | 25.0 | 0.979294 | optimal |
| HN | -1.20 | 1.30 | 1103.2 | -447.3 | 1.1198 | 0.0 | 0.976597 | optimal |
| HN | -1.50 | 1.10 | 741.6 | -69.3 | 1.0582 | 25.0 | 0.986301 | optimal |
| HN | -1.50 | 1.20 | 804.2 | -243.7 | 1.0788 | 12.5 | 0.980888 | optimal |
| HN | -1.50 | 1.30 | 838.1 | -402.6 | 1.0939 | 12.5 | 0.976255 | optimal |
| JX | -1.20 | 1.10 | 782.7 | -112.7 | 1.0732 | 50.0 | 0.996182 | search |
| JX | -1.20 | 1.20 | 911.9 | -133.6 | 1.0982 | 37.5 | 0.995762 | search |
| JX | -1.20 | 1.30 | 983.6 | -174.7 | 1.1184 | 33.3 | 0.995331 | search |
| JX | -1.50 | 1.10 | 761.1 | -181.2 | 1.0696 | 45.8 | 0.995375 | search |
| JX | -1.50 | 1.20 | 944.7 | -253.1 | 1.1117 | 37.5 | 0.994111 | search |
| JX | -1.50 | 1.30 | 1012.5 | -277.0 | 1.1451 | 29.2 | 0.993589 | search |
| WC | -1.20 | 1.10 | 1047.1 | -560.3 | 1.0820 | 66.7 | 0.988862 | optimal |
| WC | -1.20 | 1.20 | 1126.2 | -515.6 | 1.0851 | 33.3 | 0.988689 | optimal |
| WC | -1.20 | 1.30 | 1154.5 | -668.4 | 1.0962 | 16.7 | 0.987944 | optimal |
| WC | -1.50 | 1.10 | 920.2 | 720.0 | 1.0063 | 33.3 | 0.999086 | optimal |
| WC | -1.50 | 1.20 | 930.8 | 740.8 | 1.0106 | 28.6 | 0.999119 | optimal |
| WC | -1.50 | 1.30 | 938.4 | 735.7 | 1.0127 | 14.3 | 0.999017 | optimal |

Verdict: the commercial welfare loss persists through −1.20 and in HN/JX at −1.50, but reverses in WC at −1.50 under every cap.

| Corridor | Anchor | Weighted own elasticity | Pooled G/D H/M/L | All-rail H/M/L | Maximum ref-flow error |
| --- | --- | --- | --- | --- | --- |
| HN | -1.20 | -1.200000 | -0.346/-0.513/-0.865 | -0.355/-0.562/-1.048 | 5.1e-10 |
| HN | -1.50 | -1.500000 | -0.433/-0.641/-1.081 | -0.444/-0.702/-1.310 | 5e-10 |
| WC | -1.20 | -1.200000 | -0.316/-0.424/-0.655 | -0.343/-0.511/-0.896 | 1.9e-10 |
| WC | -1.50 | -1.500000 | -0.395/-0.530/-0.819 | -0.429/-0.639/-1.121 | 1.8e-10 |
| JX | -1.20 | -1.200000 | -0.185/-0.226/-0.308 | -0.210/-0.312/-0.544 | 4.1e-10 |
| JX | -1.50 | -1.500000 | -0.231/-0.283/-0.385 | -0.262/-0.389/-0.681 | 4.1e-10 |

All six load anchors reproduce 0.88 to less than 2e-12. Pooled G/D means total rail-flow response to common G/D fare perturbations with K fixed, matching Fig. 5. All-rail moves K fares as well. Neither pooled elasticity nor inelasticity alone proves cap pricing is optimal: discrete capacity and departure costs also matter. All 18 new mean multipliers are below the cap, while at-cap product-period incidence ranges from 0.0% to 66.7%.

Commercial ΔW remains nonmonotone across the full eight-anchor grid. Even welfare-optimal ΔW is nonmonotone in HN: 562.2 at −0.80, 571.0 at −1.20 and 555.7 at −1.50. WC welfare-optimal ΔW rises to 785.4/816.1 at the new anchors; JX searched values are 483.8/524.7.

Draft LaTeX (`latex_insertions/exp4_v4.tex`):

```latex

Extending the own-product elasticity anchors to $-1.20$ and $-1.50$ preserves reference flows and the 0.88 peak load and yields the targeted weighted elasticities within 0.01. At $-1.20$, commercial welfare remains below P0 under all three caps in all corridors. At $-1.50$, it remains negative in HN and in the JX search designs, but becomes positive in WC: 720.0, 740.8 and 735.7 thousand CNY/day under caps 1.10, 1.20 and 1.30. The corresponding WC mean G/D multipliers are 1.006, 1.011 and 1.013. Across the complete eight-anchor grid, 45 of 48 proven-optimal HN/WC commercial designs and all 24 JX search designs have negative welfare changes. Thus the negative commercial-welfare result is robust over the original grid and through $-1.20$, but does not extend to every corridor at $-1.50$.

Mean commercial multipliers are below their caps in all 18 added commercial cases; this is also true in parts of the original grid, so it does not define a new common threshold. Some product--period caps still bind, but their incidence falls substantially. Commercial welfare remains nonmonotone across the full sampled anchor range. Welfare-optimal P3 at cap 1.20 yields gains of 571.0/555.7 in HN, 785.4/816.1 in WC and 483.8/524.7 in JX at anchors $-1.20$/$-1.50$, respectively; the JX values remain search results.

```

Other V4 changes: line 748 must describe eight anchors, 45/48 negative proven-optimal commercial cases and 24/24 negative JX search cases; delete the “grid ends at −1.00” sentence. Qualify the central-calibration cap-pricing explanation at 641 and the regulator implication at 783. Replace the sign-invariance claim at 760 and Fig. 17 caption at 762. Add the WC exception to the abstract (65), main findings (773), and limitations (792). The original six-anchor numbers are unchanged. Figure 17(a–c) includes the new anchors; panels (d–f) explicitly retain the separate V3 sensitivity ranges. Surprising: WC at −1.50 stays near reference fares and achieves positive welfare even with the 1.30 cap.



## EXP-5 — alternative variable-cost splits

PASS: extraction only, no new optimization. Four existing optimal and two existing search designs independently verified.

| Corridor | Variable share (%) | P0 trains | Welfare P3 trains | Profit gain | ΔW | Status |
| --- | --- | --- | --- | --- | --- | --- |
| HN | 50 | 147 | 138 | 361.5 | 400.0 | optimal |
| HN | 90 | 147 | 137 | 771.0 | 730.2 | optimal |
| WC | 50 | 185 | 177 | 535.2 | 541.2 | optimal |
| WC | 90 | 185 | 174 | 1183.5 | 1029.8 | optimal |
| JX | 50 | 190 | 191 | -110.9 | 843.5 | search |
| JX | 90 | 190 | 186 | 161.5 | 831.9 | search |

Verdict: welfare-optimal withdrawal persists in HN/WC at both splits, but JX at 50% selects 191 trains versus 190 in P0; the over-supply claim is not general across cost splits.

Suggested LaTeX addition after V4 line 643:

```latex

The departure-withdrawal result persists in HN and WC at variable-cost shares of 50% and 90%: welfare P3 selects 138/137 and 177/174 departures, respectively. It is less general in JX, where the searched welfare design selects 191 departures at the 50% split, compared with 190 under P0, and lowers operator profit by 110.9 thousand CNY/day. The interpretation of excess reference supply is therefore conditional on the calibrated cost split.

```

Other V4 changes: qualify “the observed timetable therefore offers more departures than are efficient” at line 643 and the discussion at 781. Evidence is exp5/results.json and the V3 constant_cost_grid.json; no source values were overwritten.



## Checks 1–10





Evidence paths below are relative to D:/Paper-M/TRA unless absolute. The supplied V4 .tex is unchanged.



### 1. Demand sizing (V4 line 597)

The statement is approximately correct but hides the construction. `TRA-R2/experiments_v3_round5/calibration.py:9–33` first allocates target seat flows by inverse OD road distance, normalizes by maximum subpath occupancy, and scales each tier by 0.78/0.72/0.70 relative to G and by the 0.88 reference load. Potential demand is target rail flow divided by 0.85 and the distance-band target rail share, allocated 0.20/0.60/0.20 to H/M/L. Class participation targets are 0.90/0.85/0.80, class rail shares are shifted by +0.04/0/−0.045, and iterative proportional fitting balances class/product/seat targets. This is calibrated demand, not observed ticket demand.

Suggested wording: “Potential demand is constructed from tier-scaled reference seat flows, allocated across ODs using normalized inverse road-distance weights, and divided by the target aggregate rail share and a 0.85 participation scaling factor; class-specific flows and intercepts are then balanced to reproduce the 0.88 peak load.”



### 2. Business-van fare (V4 line 602)

Model interpretation is a passenger's monetary cost: there is no van-occupancy divisor (`model.py:93–104`; only private-auto cost is divided by occupancy in `calibration.py:57`). The HN value is 695.5 CNY, not an observed per-seat quote. The source rules are `TRA-V7/TRA-V7_REUSABLE_R1_KINCUMBENT_20260812/cases/formal/hangzhou_nanjing/raw_data/hangzhou_nanjing_road_cost_rules.json:18–23`: max(50, 2.2 × distance_km + 0.4 × duration_min). The associated road_passenger.csv row gives 279.388 km, 202.117 min and 695.50 CNY. No cited tariff source or explicit seat/vehicle unit is recorded in those rules. Consequently the model's per-person use can be confirmed, but the real-world quote unit cannot.

Reference van shares of realized trips: HN 0.5400%, WC 0.5400%, JX 0.5845%. Van has 3% within shared-road modes and 1.8% within all road trips by construction (`calibration.py:63–73`).

Suggested wording: “Business-van monetary costs are stylized model assumptions, calculated at 2.2 CNY/km plus 0.4 CNY/min with a 50-CNY minimum and applied per traveler; they are not verified per-seat tariffs.” The author should confirm the intended tariff unit before interpreting it empirically.



### 3. Headroom (V4 line 650)

Endpoint difference, not a regression slope: [gain(load 0.85) − gain(load 0.92)] / 7 / observed_departures / 1000. Computed values: {'HN': np.float64(0.8862989494778194), 'WC': np.float64(1.0252294937868751), 'JX': np.float64(0.3151467495038965)}. The ceiling is 0.95, variable-cost share 0.70, and total reference cost is held at the load-0.88 anchor. Evidence: `write_round3.py:124–128`; `constant_cost_grid.json`.

Suggested wording: “Across the 0.85–0.92 reference-load endpoints, the average increase in commercial P3 profit gain per percentage point of spare capacity is 0.886/1.025/0.315 thousand CNY/day per observed departure.”



### 4. Fare freeze versus P2 (V4 line 662)

{
  "HN": {
    "N_identical": true,
    "all_active_fares_one": true,
    "same_y_u": true,
    "design_hash_freeze": "ad2a93b396223e1053b5fb057b52849ab7105a639bbc5b80933a143daccd1a13",
    "design_hash_P2": "ad2a93b396223e1053b5fb057b52849ab7105a639bbc5b80933a143daccd1a13"
  },
  "WC": {
    "N_identical": true,
    "all_active_fares_one": true,
    "same_y_u": true,
    "design_hash_freeze": "9e31d0eba0eea514317ca92ffa00fe1ff503aca849fe078275497b91329e5ba0",
    "design_hash_P2": "9e31d0eba0eea514317ca92ffa00fe1ff503aca849fe078275497b91329e5ba0"
  }
}

Evidence: fresh `step0_runs/*_freeze.json` versus V3 `runs/E2/*_reference_none.json`, profit P2. Suggested wording: “At cap 1.00 and floor 0.95, commercial P3 coincides with commercial P2 in train activation, departures and active fares; no active G/D product-period prices below 1.00.”



### 5. Distinct grid designs (V4 lines 669–670)

V3: HN 11/30; WC 10/30. Refined V4: HN 21/35; WC 20/35. Identity hashes y/u derived from N, integer N and full fare arrays; no rounding of numerical outcomes is used as a design identifier. Evidence: `exp1/analysis.json` and `TRA-R2/experiments_v3_round6/grid/*.json`.

Suggested wording: “The 30 sampled cap–floor points correspond to 11 distinct HN designs and 10 distinct WC designs.”



### 6. Floor definitions in 72 moderate states (V4 line 723)

{
  "same_state": {
    "HN": {
      "states": 24,
      "P0": 22,
      "P4": 24,
      "unresolved_P4": 0
    },
    "WC": {
      "states": 24,
      "P0": 22,
      "P4": 24,
      "unresolved_P4": 0
    },
    "JX": {
      "states": 24,
      "P0": 24,
      "P4": 24,
      "unresolved_P4": 0
    }
  },
  "absolute_reference": {
    "HN": {
      "states": 24,
      "P0": 20,
      "P4": 24,
      "unresolved_P4": 0
    },
    "WC": {
      "states": 24,
      "P0": 22,
      "P4": 24,
      "unresolved_P4": 0
    },
    "JX": {
      "states": 24,
      "P0": 24,
      "P4": 24,
      "unresolved_P4": 0
    }
  }
}

Evidence: `run_experiments.py:26–31,57–58`, `model.py:106–119`, V3 E2 (same-state) and E11 (absolute-reference) outputs. Reference-income states use the identical denominator under both definitions. P4 means at least one independently re-evaluated feasible saved design across objectives; JX is search evidence.



### 7. 92% cost ratio (V4 line 610)

The ratio is hard-coded as `totalcost=.92*refrev` in `calibration.py:91`; older input construction also rescales costs at `build_inputs.py:145`. The code/config contains no cited source for 92%. It is an assumption, with 70% variable and 30% retained commitments at the central setting.

Suggested wording: “We assume total reference operating cost equal to 92% of reference rail revenue and split it into 70% variable departure costs and 30% retained product commitments.”



### 8. JX welfare-P3 profit change (V4 line 643)

163.349901 thousand CNY/day relative to same-state P0. This is positive, based on the fresh search rerun and independent scalar check in `step0_runs/JX_welfare.json`. Suggested wording: “The welfare benchmark also raises operator profit in all three corridors.”



### 9. Hard-coded table/figure numbers

0 occurrences in the current TRA-R3/tables/*.tex. The governance note already uses Table~\ref{tab:baseline_policy_values}. Complete inventory: `checks_hardcoded_refs.csv`.



### 10. Certified/certify/witness wording

30 individual occurrences are inventoried with the matched word, column, complete line text, file and line number in `checks_wording.csv`. Scope: every current R3 table and the V3 round5 figure generators, active round6 Fig. 13 generator, round7 Fig. 17 generator, and current R3 redrawing scripts; historical archived/replaced engines are excluded. New table copies and figure generators use the requested terminology.


Replacement for V4 line 723: “Across the 72 moderate states, P0 is feasible in 68 under same-state floors and 66 under absolute-reference floors, while P4 has feasible saved designs in all 72 under either definition.” Central JX welfare-P3 also raises operator profit, by 163.3 thousand CNY/day; line 643 can say all three corridors, conditional on the central cost split.



## Table and figure changes

Prepared six new table sources in exp_v4/tables with the suffix _v4. Original files remain unchanged. Current R3 tables contain no hard-coded numeric Table/Figure references; the governance note already points to tab:baseline_policy_values. All occurrences of the requested legacy wording in copied notes have been removed, with grammar adjusted to preserve the distinction between proved optima, feasible saved designs and search results.

The new v3_experiments_v4.tex retains A–C and moves D to a continued Table 7 with anchors as rows, explicit Profit gain and ΔW columns at caps 1.10/1.20/1.30, and 48 proven-optimal HN/WC plus 24 searched JX entries. v3_governance_v4.tex retains A–D and adds continued panel E for refined floors. Both continue the same table counters using the already-loaded caption package. Four auxiliary table copies only update terminology; v3_findings remains excluded from the manuscript.

Figure 13 has the original two-corridor panel layout and strict-floor insets, with the refined commercial grid, sampled nondominated envelope, central welfare optima and five V3 cap-only context points per corridor. Figure 17 extends a–c and preserves d–f as explicitly labeled V3 sensitivity ranges. Both have PDF, SVG and PNG outputs. Figure 11 stays unchanged.

The desktop LaTeX compiler and two local pdflatex passes succeeded for table_preview/main.tex; its four-page preview checks the updated Tables 7 and 9. The preview provides a temporary Table 8 anchor for the unchanged reference note, not a replacement manuscript. Rendered tables and figures were visually inspected. No claim is made that the unchanged original V4 manuscript contains the new content.

Integration commands from the TRA-R3 manuscript directory:

```latex

\input{exp_v4/tables/v3_experiments_v4.tex}

\input{exp_v4/tables/v3_governance_v4.tex}

\includegraphics[width=\textwidth]{exp_v4/exp1/fig13_cap_floor_frontier_v4.pdf}

\includegraphics[width=\textwidth]{exp_v4/exp4/fig17_calibration_dependence_v4.pdf}

```

Suggested revised Fig. 17 caption:

```latex

Commercial welfare is corridor-dependent on the expanded elasticity--cap grid. Panels (a)--(c) show proven-optimal HN/WC commercial designs and best JX designs found by search over eight elasticity anchors; WC welfare becomes positive at the -1.50 anchor under all three caps. Panels (d)--(f) retain the separately evaluated V3 sensitivity ranges, whose elasticity component uses the original six-anchor grid. Dashed vertical lines mark the central calibration.

```

Suggested abstract addition:

```latex

In Wuhan--Changsha, a floor of 0.9995 under the 1.20 cap improves both profit and welfare relative to strict full-retention designs and comes within 0.3 thousand CNY/day of the welfare optimum. Commercial welfare losses persist through an own-product elasticity anchor of -1.20, but become gains in this corridor at -1.50.

```

Suggested regulatory implication 3 replacement (line 785):

```latex

Third, a participation floor targets low-income mobility but can be more restrictive than necessary when fixed at exactly full retention. In WC, a floor of 0.9995 under cap 1.20 yields both higher operator profit and higher welfare than either tested strict-floor design. In HN, a sub-unit floor improves on the strict floor alone, while the cap-1.05/strict-floor combination remains sampled nondominated. Regulators should therefore compare nearby floors and joint instruments rather than presume that an exact full-retention rule is best.

```

Availability statement (line 795): distinguish the original V3 archive totals from this supplement’s 78 grid and 24 elasticity run records. These include overlapping configurations and regression repeats; do not add them to the old unique-problem counts without configuration deduplication. A public repository DOI/URL and empirical van-tariff source are not supplied and must not be invented. The 92% ratio should be explicitly labeled an assumption. The audited company-finance and author-address checks in the shorter companion note are outside the detailed brief’s ten code/output checks and remain editorial/source-verification items.

Reproduction: run step0.py first; only after step0_status.json is true run exp1.py, exp2.py, exp3.py and exp4.py. Then run checks_and_exp5.py, prepare_tables.py, figures_v4.py, report_v4.py and verify_delivery.py. Existing experiment runners resume their per-case JSON caches. All new source files and result batches are committed in the scoped exp_v4 repository.
