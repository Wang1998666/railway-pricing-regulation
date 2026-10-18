# EXP-1 refined grid

{'optimal': 78}

All money: thousand CNY/day, one direction. The welfare benchmark is central cap 1.20.

## HN
Distinct designs: 21/35 refined points; 11/30 V3 points.
First sampled binding floors (null means no sampled floor is binding): {'1.0': None, '1.05': 0.995, '1.1': None, '1.15': None, '1.2': None}.
Floors admitting the central welfare optimum at cap 1.20: [0.98, 0.985, 0.99, 0.995, 0.999, 0.9995, 1.0].
Sub-unit commercial designs weakly dominating cap 1.20/floor 1.00: 8; dominating cap 1.05/floor 1.00: 0.

| Cap | Floor | Profit gain | ΔW | L retention |
|---|---|---|---|---|
| 1.20 | 0.9950 | 924.7 | 278.1 | 0.99500905 |
| 1.20 | 0.9990 | 682.7 | 502.4 | 0.99900170 |
| 1.20 | 0.9995 | 626.7 | 490.1 | 0.99953320 |
| 1.20 | 1.0000 | 569.9 | 388.9 | 1.00008851 |
| 1.05 | 0.9950 | 822.6 | 279.6 | 0.99500051 |
| 1.05 | 0.9990 | 640.3 | 483.8 | 0.99905553 |
| 1.05 | 0.9995 | 624.1 | 513.5 | 0.99953033 |
| 1.05 | 1.0000 | 565.7 | 521.0 | 1.00004120 |

## WC
Distinct designs: 20/35 refined points; 10/30 V3 points.
First sampled binding floors (null means no sampled floor is binding): {'1.0': None, '1.05': None, '1.1': None, '1.15': None, '1.2': None}.
Floors admitting the central welfare optimum at cap 1.20: [0.98, 0.985, 0.99, 0.995, 0.999, 0.9995].
Sub-unit commercial designs weakly dominating cap 1.20/floor 1.00: 1; dominating cap 1.05/floor 1.00: 1.

| Cap | Floor | Profit gain | ΔW | L retention |
|---|---|---|---|---|
| 1.20 | 0.9950 | 1286.1 | 106.0 | 0.99500146 |
| 1.20 | 0.9990 | 979.6 | 683.9 | 0.99912635 |
| 1.20 | 0.9995 | 922.9 | 769.3 | 0.99958959 |
| 1.20 | 1.0000 | 757.0 | 730.4 | 1.00000642 |
| 1.05 | 0.9950 | 1129.9 | 167.5 | 0.99534262 |
| 1.05 | 0.9990 | 895.3 | 631.8 | 0.99909778 |
| 1.05 | 0.9995 | 891.7 | 724.1 | 0.99957320 |
| 1.05 | 1.0000 | 756.2 | 734.0 | 1.00001536 |

Binding uses the requested post-integer-solution tolerance of 1e-6; a stricter floor can change the optimal discrete design while the constraint remains numerically slack. Full sampled frontier and welfare shares are in analysis.json and grid.csv.


## Interpretation and draft prose

The refined grid crosses five caps with seven participation floors from 0.98 to 1.00, producing 70 proven-optimal commercial designs and eight proven-optimal welfare benchmarks. These commercial points represent 21 distinct HN designs and 20 distinct WC designs, compared with 11 and 10 in the original grid. At cap 1.20, floors of 0.995 and 0.999 yield profit/welfare gains of 924.7/278.1 and 682.7/502.4 thousand CNY/day in HN, and 1,286.1/106.0 and 979.6/683.9 in WC. With cap 1.05, the corresponding gains are 822.6/279.6 and 640.3/483.8 in HN, and 1,129.9/167.5 and 895.3/631.8 in WC. Under the numerical binding tolerance of $10^{-6}$, only HN at cap 1.05 and floor 0.995 is binding among these sampled optima; elsewhere integer adjustments leave positive slack even when tightening the floor changes the chosen design.

A sub-unit floor can improve both objectives relative to strict retention. In HN, cap 1.20 with floor 0.999 yields 682.7 thousand CNY/day of profit gain and 502.4 of welfare gain, exceeding 569.9 and 388.9 under the strict floor alone, although it does not dominate the cap-1.05/strict-floor combination. In WC, cap 1.20 with floor 0.9995 yields gains of 922.9 and 769.3, exceeding both strict-floor designs under caps 1.20 and 1.05. Its welfare is only 0.3 thousand CNY/day below the central welfare optimum. The WC welfare optimum itself is feasible at floor 0.9995, since its retention ratio is 0.999754. Thus the cap-1.05/strict-floor combination remains sampled nondominated in HN but is dominated on the refined WC grid.
