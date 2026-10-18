# V4 factual checks



Evidence paths below are relative to D:/Paper-M/TRA unless absolute. The supplied V4 .tex is unchanged.



## 1. Demand sizing (V4 line 597)

The statement is approximately correct but hides the construction. `TRA-R2/experiments_v3_round5/calibration.py:9–33` first allocates target seat flows by inverse OD road distance, normalizes by maximum subpath occupancy, and scales each tier by 0.78/0.72/0.70 relative to G and by the 0.88 reference load. Potential demand is target rail flow divided by 0.85 and the distance-band target rail share, allocated 0.20/0.60/0.20 to H/M/L. Class participation targets are 0.90/0.85/0.80, class rail shares are shifted by +0.04/0/−0.045, and iterative proportional fitting balances class/product/seat targets. This is calibrated demand, not observed ticket demand.

Suggested wording: “Potential demand is constructed from tier-scaled reference seat flows, allocated across ODs using normalized inverse road-distance weights, and divided by the target aggregate rail share and a 0.85 participation scaling factor; class-specific flows and intercepts are then balanced to reproduce the 0.88 peak load.”



## 2. Business-van fare (V4 line 602)

Model interpretation is a passenger's monetary cost: there is no van-occupancy divisor (`model.py:93–104`; only private-auto cost is divided by occupancy in `calibration.py:57`). The HN value is 695.5 CNY, not an observed per-seat quote. The source rules are `TRA-V7/TRA-V7_REUSABLE_R1_KINCUMBENT_20260812/cases/formal/hangzhou_nanjing/raw_data/hangzhou_nanjing_road_cost_rules.json:18–23`: max(50, 2.2 × distance_km + 0.4 × duration_min). The associated road_passenger.csv row gives 279.388 km, 202.117 min and 695.50 CNY. No cited tariff source or explicit seat/vehicle unit is recorded in those rules. Consequently the model's per-person use can be confirmed, but the real-world quote unit cannot.

Reference van shares of realized trips: HN 0.5400%, WC 0.5400%, JX 0.5845%. Van has 3% within shared-road modes and 1.8% within all road trips by construction (`calibration.py:63–73`).

Suggested wording: “Business-van monetary costs are stylized model assumptions, calculated at 2.2 CNY/km plus 0.4 CNY/min with a 50-CNY minimum and applied per traveler; they are not verified per-seat tariffs.” The author should confirm the intended tariff unit before interpreting it empirically.



## 3. Headroom (V4 line 650)

Endpoint difference, not a regression slope: [gain(load 0.85) − gain(load 0.92)] / 7 / observed_departures / 1000. Computed values: {'HN': np.float64(0.8862989494778194), 'WC': np.float64(1.0252294937868751), 'JX': np.float64(0.3151467495038965)}. The ceiling is 0.95, variable-cost share 0.70, and total reference cost is held at the load-0.88 anchor. Evidence: `write_round3.py:124–128`; `constant_cost_grid.json`.

Suggested wording: “Across the 0.85–0.92 reference-load endpoints, the average increase in commercial P3 profit gain per percentage point of spare capacity is 0.886/1.025/0.315 thousand CNY/day per observed departure.”



## 4. Fare freeze versus P2 (V4 line 662)

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



## 5. Distinct grid designs (V4 lines 669–670)

V3: HN 11/30; WC 10/30. Refined V4: HN 21/35; WC 20/35. Identity hashes y/u derived from N, integer N and full fare arrays; no rounding of numerical outcomes is used as a design identifier. Evidence: `exp1/analysis.json` and `TRA-R2/experiments_v3_round6/grid/*.json`.

Suggested wording: “The 30 sampled cap–floor points correspond to 11 distinct HN designs and 10 distinct WC designs.”



## 6. Floor definitions in 72 moderate states (V4 line 723)

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



## 7. 92% cost ratio (V4 line 610)

The ratio is hard-coded as `totalcost=.92*refrev` in `calibration.py:91`; older input construction also rescales costs at `build_inputs.py:145`. The code/config contains no cited source for 92%. It is an assumption, with 70% variable and 30% retained commitments at the central setting.

Suggested wording: “We assume total reference operating cost equal to 92% of reference rail revenue and split it into 70% variable departure costs and 30% retained product commitments.”



## 8. JX welfare-P3 profit change (V4 line 643)

163.349901 thousand CNY/day relative to same-state P0. This is positive, based on the fresh search rerun and independent scalar check in `step0_runs/JX_welfare.json`. Suggested wording: “The welfare benchmark also raises operator profit in all three corridors.”



## 9. Hard-coded table/figure numbers

0 occurrences in the current TRA-R3/tables/*.tex. The governance note already uses Table~\ref{tab:baseline_policy_values}. Complete inventory: `checks_hardcoded_refs.csv`.



## 10. Certified/certify/witness wording

30 individual occurrences are inventoried with the matched word, column, complete line text, file and line number in `checks_wording.csv`. Scope: every current R3 table and the V3 round5 figure generators, active round6 Fig. 13 generator, round7 Fig. 17 generator, and current R3 redrawing scripts; historical archived/replaced engines are excluded. New table copies and figure generators use the requested terminology.
