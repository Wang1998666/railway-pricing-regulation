# EXP-4 wider elasticity range

{'optimal': 16, 'search': 8}

All money: thousand CNY/day. Reference flows and peak load pass for all six recalibrations.

Commercial ΔW negative at every new anchor/cap: False.

| Corridor | Anchor | Cap | Objective | Profit gain | ΔW | Mean multiplier | Cap cell share | Retention | Status |
|---|---|---|---|---|---|---|---|---|---|
| HN | -1.50 | 1.10 | profit | 741.6 | -69.3 | 1.0582 | 0.250 | 0.986301 | optimal |
| HN | -1.50 | 1.20 | profit | 804.2 | -243.7 | 1.0788 | 0.125 | 0.980888 | optimal |
| HN | -1.50 | 1.20 | welfare | 591.2 | 555.7 | 0.9996 | 0.000 | 0.999731 | optimal |
| HN | -1.50 | 1.30 | profit | 838.1 | -402.6 | 1.0939 | 0.125 | 0.976255 | optimal |
| HN | -1.20 | 1.10 | profit | 946.2 | -157.0 | 1.0849 | 0.500 | 0.984189 | optimal |
| HN | -1.20 | 1.20 | profit | 1069.8 | -336.3 | 1.1084 | 0.250 | 0.979294 | optimal |
| HN | -1.20 | 1.20 | welfare | 588.2 | 571.0 | 0.9976 | 0.000 | 1.000203 | optimal |
| HN | -1.20 | 1.30 | profit | 1103.2 | -447.3 | 1.1198 | 0.000 | 0.976597 | optimal |
| JX | -1.50 | 1.10 | profit | 761.1 | -181.2 | 1.0696 | 0.458 | 0.995375 | search |
| JX | -1.50 | 1.20 | profit | 944.7 | -253.1 | 1.1117 | 0.375 | 0.994111 | search |
| JX | -1.50 | 1.20 | welfare | 255.0 | 524.7 | 0.9804 | 0.038 | 1.000910 | search |
| JX | -1.50 | 1.30 | profit | 1012.5 | -277.0 | 1.1451 | 0.292 | 0.993589 | search |
| JX | -1.20 | 1.10 | profit | 782.7 | -112.7 | 1.0732 | 0.500 | 0.996182 | search |
| JX | -1.20 | 1.20 | profit | 911.9 | -133.6 | 1.0982 | 0.375 | 0.995762 | search |
| JX | -1.20 | 1.20 | welfare | 123.7 | 483.8 | 0.9711 | 0.038 | 1.001060 | search |
| JX | -1.20 | 1.30 | profit | 983.6 | -174.7 | 1.1184 | 0.333 | 0.995331 | search |
| WC | -1.50 | 1.10 | profit | 920.2 | 720.0 | 1.0063 | 0.333 | 0.999086 | optimal |
| WC | -1.50 | 1.20 | profit | 930.8 | 740.8 | 1.0106 | 0.286 | 0.999119 | optimal |
| WC | -1.50 | 1.20 | welfare | 877.6 | 816.1 | 1.0015 | 0.143 | 0.999850 | optimal |
| WC | -1.50 | 1.30 | profit | 938.4 | 735.7 | 1.0127 | 0.143 | 0.999017 | optimal |
| WC | -1.20 | 1.10 | profit | 1047.1 | -560.3 | 1.0820 | 0.667 | 0.988862 | optimal |
| WC | -1.20 | 1.20 | profit | 1126.2 | -515.6 | 1.0851 | 0.333 | 0.988689 | optimal |
| WC | -1.20 | 1.20 | welfare | 939.0 | 785.4 | 1.0040 | 0.000 | 0.999411 | optimal |
| WC | -1.20 | 1.30 | profit | 1154.5 | -668.4 | 1.0962 | 0.167 | 0.987944 | optimal |


## Interpretation and draft prose

Extending the own-product elasticity anchors to $-1.20$ and $-1.50$ preserves reference flows and the 0.88 peak load and yields the targeted weighted elasticities within 0.01. At $-1.20$, commercial welfare remains below P0 under all three caps in all corridors. At $-1.50$, it remains negative in HN and in the JX search designs, but becomes positive in WC: 720.0, 740.8 and 735.7 thousand CNY/day under caps 1.10, 1.20 and 1.30. The corresponding WC mean G/D multipliers are 1.006, 1.011 and 1.013. Across the complete eight-anchor grid, 45 of 48 proven-optimal HN/WC commercial designs and all 24 JX search designs have negative welfare changes. Thus the negative commercial-welfare result is robust over the original grid and through $-1.20$, but does not extend to every corridor at $-1.50$.

Mean commercial multipliers are below their caps in all 18 added commercial cases; this is also true in parts of the original grid, so it does not define a new common threshold. Some product--period caps still bind, but their incidence falls substantially. Commercial welfare remains nonmonotone across the full sampled anchor range. Welfare-optimal P3 at cap 1.20 yields gains of 571.0/555.7 in HN, 785.4/816.1 in WC and 483.8/524.7 in JX at anchors $-1.20$/$-1.50$, respectively; the JX values remain search results.
