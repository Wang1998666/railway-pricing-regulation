# EXP-2 cost-ratio diagnostics



{
  "n": 1842,
  "lower_left": 341,
  "common_VOT_CNY_hour": [
    97.5714285714
  ],
  "argmax_cells": {
    "H": 1.0,
    "M": 0.0,
    "L": 0.0
  },
  "argmax_worst": {
    "H": 1.0,
    "M": 0.0,
    "L": 0.0
  },
  "lower_left_L_exit_share": 1.0,
  "lower_left_H_argmax_share": 1.0,
  "lower_left_fixed_not_falling": 0.04985337243401759,
  "quadrants": {
    "dG": {
      "-1,-1": 341,
      "-1,+1": 460,
      "+1,-1": 600,
      "+1,+1": 225,
      "on_axis": 216
    },
    "delta_L_common_ratio": {
      "-1,-1": 660,
      "-1,+1": 395,
      "+1,-1": 308,
      "+1,+1": 242,
      "on_axis": 237
    },
    "delta_L_monetary_CNY": {
      "-1,-1": 728,
      "-1,+1": 420,
      "+1,-1": 284,
      "+1,+1": 268,
      "on_axis": 142
    },
    "delta_Gfix": {
      "-1,-1": 327,
      "-1,+1": 476,
      "+1,-1": 614,
      "+1,+1": 209,
      "on_axis": 216
    }
  },
  "scalar_max_error": 6.705522537231445e-08
}



Aggregation matches Fig. 15: Gmax is the maximum over OD-period cells of the maximum class generalized cost divided by the realized-trip-weighted class mean in that cell. L common-VOT burden is the maximum OD-period L ratio; monetary burden is the L-trip-weighted daily mean across OD-periods. Changes use each design's same-state P0.

The common in-vehicle VOT is population-weighted at the central unperturbed reference state and held fixed across every library configuration. Access, wait, schedule, reliability and transfer valuations use the corresponding population-weighted central reference coefficients; this gives every class the same attribute valuations while retaining their evaluated choices. Ties split attribution equally. Canonical library designs pool parent/candidate K; feasibility is the original library's union over tested configurations, not a new policy-feasibility claim.

Verdict: Both low-income participation loss and high-VOT-class burdens are present; the fixed-weight comparison quantifies when changing participation weights is necessary for the reported cost-ratio fall.


## Interpretation and draft prose

Forward evaluation of the same 1,842 unique feasible designs shows that class H attains the maximum generalized-cost ratio in every OD--period cell and at every design's worst-case cell. All 341 lower-left designs reduce low-income trips. Holding the class participation weights fixed at their same-state P0 values prevents the cost ratio from falling in 17 of these designs (5.0%), demonstrating a composition effect in that subset. In the remaining 324, the cost ratio still falls at fixed weights, so low-income exit alone does not explain the decline. These are accounting comparisons within the evaluated library, rather than causal estimates.

Using a common reference in-vehicle VOT of 97.6 CNY/h for all classes, together with common population-weighted reference valuations for other time attributes, the L-specific generalized-cost ratio falls while L participation falls in 660 designs. The corresponding counts are 728 for L's mean monetary cost per realized trip and 327 for the fixed-weight version of the original ratio. The diagnostics therefore support both high-VOT-class dominance of the original index and a participation-composition effect in a smaller subset; monitoring L participation remains necessary alongside realized-traveler burden measures.
