"""Vectorized nested-logit engine with service-pattern frequency decisions.

Replaces the pure-Python evaluate_design / segment_probabilities / build_alternatives
chain with pre-computed tensors and batch NumPy operations.

G/D retain the calibrated corridor-product representation.  K frequencies are
indexed by observed service pattern, so a train pattern supplies only the ODs
that it actually served in the source data.  Demand alternatives remain
product/seat alternatives; their effective frequency is the sum of eligible
patterns serving the segment OD.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import logsumexp as _sp_logsumexp

PRODUCTS = ("G", "D", "K")
MODES = ("rail", "road", "auto")


def load_case(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


class PatternNLTEngine:
    """Batch-evaluate nested logit demand for arbitrary designs.

    Parameters
    ----------
    case : dict
        Full aligned_case.json content.
    income_state : str
        Income scenario name.
    electrification_state : str
        Electrification scenario name.
    """

    def __init__(self, case: dict[str, Any], income_state: str, electrification_state: str):
        self.case = case
        self.income_state = income_state
        self.electrification_state = electrification_state

        self.periods = list(case["sets"]["periods"])
        self.classes = list(case["sets"]["classes"])
        self.n_periods = len(self.periods)
        self.n_products = 3
        self.n_classes = len(self.classes)
        self._vulnerable_class_idx = self.classes.index(
            case["sets"]["vulnerable_class"]
        )

        # Service-pattern decision dimensions.
        self.patterns = list(case["service_patterns"])
        self.pattern_ids = [pattern["id"] for pattern in self.patterns]
        self.n_patterns = len(self.patterns)
        product_to_idx = {"G": 0, "D": 1, "K": 2}
        self._pattern_product_idx = np.array(
            [product_to_idx[pattern["product"]] for pattern in self.patterns],
            dtype=np.int32,
        )
        self._pattern_route_length = np.array(
            [float(pattern["route_length_km"]) for pattern in self.patterns],
            dtype=np.float64,
        )
        self._pattern_activation_cost = np.array(
            [float(pattern.get("activation_cost", 0.0)) for pattern in self.patterns],
            dtype=np.float64,
        )

        # Build segment index arrays
        segments = case["demand_segments"]
        self.n_segments = len(segments)
        self._seg_od = [s["od"] for s in segments]
        self._seg_class = [s["class"] for s in segments]
        self._seg_period = [s["period"] for s in segments]
        self._qbar = np.array([s["qbar"] for s in segments], dtype=np.float64)

        # Map segment -> period index, class index
        period_idx = {p: i for i, p in enumerate(self.periods)}
        class_idx = {c: i for i, c in enumerate(self.classes)}
        self._seg_period_idx = np.array([period_idx[s["period"]] for s in segments], dtype=np.int32)
        self._seg_class_idx = np.array([class_idx[s["class"]] for s in segments], dtype=np.int32)

        # Duration per period (hours)
        self._duration_h = np.array(
            [case["sets"]["periods"][p]["duration_h"] for p in self.periods], dtype=np.float64
        )

        # Schedule parameters
        self._vartheta = float(case["schedule"]["vartheta_min"])
        self._terminal_wait = float(case["schedule"]["terminal_wait_min"])

        # Mu (nest scale parameters)
        mu = case["utility"]["mu"]
        self._mu_rail = float(mu["rail"])
        self._mu_road = float(mu["road"])
        self._mu_auto = float(mu["auto"])
        self._mu_mode = float(mu["mode_level"])
        self._mu_top = float(mu["top"])

        # Beta coefficients per class (adjusted for income shock)
        self._beta = self._build_beta_matrix(case, income_state)  # [n_classes, 9]
        # Order: beta_c, beta_iv, beta_ac, beta_wt, beta_sc, beta_rel, beta_tr, gamma_com, gamma_flex

        # Alpha travel and ASC mode per class
        self._alpha_travel = np.array(
            [case["utility"]["alpha_travel"][c] for c in self.classes], dtype=np.float64
        )
        self._asc_mode_rail = np.array(
            [case["utility"]["asc_mode"][c]["rail"] for c in self.classes], dtype=np.float64
        )
        self._asc_mode_road = np.array(
            [case["utility"]["asc_mode"][c]["road"] for c in self.classes], dtype=np.float64
        )
        self._asc_mode_auto = np.array(
            [case["utility"]["asc_mode"][c]["auto"] for c in self.classes], dtype=np.float64
        )

        # Build alternative structure
        self._build_alternatives(case, electrification_state)

        # Pre-compute fixed utility components for road/auto (design-independent)
        self._road_auto_fixed_utils = self._compute_road_auto_fixed_utils()

        # Pre-compute rail fixed utility components
        self._rail_fixed_utils = self._compute_rail_fixed_utils()

        # Reference vulnerable trips (for retention constraint)
        self._reference_vulnerable_trips: float | None = None

    def _build_beta_matrix(self, case: dict, income_state: str) -> np.ndarray:
        """Build income-adjusted beta matrix [n_classes, 9]."""
        beta_keys = ["beta_c", "beta_iv", "beta_ac", "beta_wt", "beta_sc",
                     "beta_rel", "beta_tr", "gamma_com", "gamma_flex"]
        matrix = np.zeros((self.n_classes, 9), dtype=np.float64)
        for ci, cls in enumerate(self.classes):
            base = dict(case["utility"]["by_class"][cls])
            shock = case["scenarios"]["income"][income_state][cls]
            delta_y = math.log1p(shock)
            rho = case["utility"]["rho"][cls]
            base["beta_c"] = base["beta_c"] * math.exp(-rho * delta_y)
            for ki, key in enumerate(beta_keys):
                matrix[ci, ki] = base[key]
        return matrix

    def _build_alternatives(self, case: dict, electrification_state: str) -> None:
        """Build the fixed alternative structure for all segments."""
        attrs = case["attributes"]
        products_spec = case["products"]
        electric = case["scenarios"]["electrification"][electrification_state]

        # For each segment, enumerate rail alternatives (product, seat) with fixed attrs
        # Rail alt: [iv_time, ac_time, wait_time, reliability, comfort, flexibility, asc, base_fare]
        # Design-dependent: cost = base_fare * phi, schedule_delay = vartheta*duration/N

        self._rail_alts: list[list[dict]] = []  # per segment
        self._road_alts: list[list[dict]] = []  # per segment (fixed)

        for seg_i, seg in enumerate(case["demand_segments"]):
            od = seg["od"]
            endpoints = case["network"].get("od_endpoints", {}).get(od)
            if endpoints is None:
                endpoints = od.split("-", 1)
            if len(endpoints) != 2:
                raise ValueError(
                    f"OD {od!r} needs two endpoints in network.od_endpoints"
                )
            origin, destination = endpoints
            access = attrs["access_by_city"]
            access_cost = access[origin]["fare"] + access[destination]["fare"]
            access_min = access[origin]["time_min"] + access[destination]["time_min"]

            rail_list = []
            for product in PRODUCTS:
                product_fares = attrs["rail_fare"].get(od, {}).get(product, {})
                runtime = attrs["rail_runtime_min"].get(od, {}).get(product)
                if runtime is None or not product_fares:
                    continue
                for seat, ref_fare in product_fares.items():
                    if seat not in products_spec[product]["seat_capacity"]:
                        continue
                    asc = (case["utility"]["asc_product"][product]
                           + case["utility"]["asc_seat"][product][seat])
                    rail_list.append({
                        "product": product,
                        "seat": seat,
                        "base_fare": float(ref_fare),
                        "access_cost": float(access_cost),
                        "iv_time": float(runtime),
                        "ac_time": float(access_min),
                        "wait_time": self._terminal_wait,
                        "reliability": products_spec[product]["reliability_fraction"] * runtime,
                        "transfers": 0.0,
                        "comfort": products_spec[product]["seat_comfort"][seat],
                        "flexibility": products_spec[product]["flexibility"],
                        "asc": float(asc),
                        "seat_capacity": products_spec[product]["seat_capacity"][seat],
                    })
            self._rail_alts.append(rail_list)

            # Road alternatives (fixed for given electrification)
            road = attrs["road_by_od"][od]
            distance = road["distance_km"]
            pass_through = electric["pass_through"]
            auto_saving = (case["electrification_savings"]["private_auto_per_km"]
                           * distance * electric["auto_intensity"])
            road_list = []
            # private_auto (mode=auto)
            road_list.append({
                "mode": "auto",
                "product": "private_auto",
                "cost": max(1.0, road["private_auto_cost"] - auto_saving),
                "iv_time": road["auto_duration_min"],
                "ac_time": 0.0,
                "wait_time": 0.0,
                "schedule_delay": 0.0,
                "reliability": 0.05 * road["auto_duration_min"],
                "transfers": 0.0,
                "comfort": 3.0,
                "flexibility": 5.0,
                "asc": case["utility"]["asc_alternative"]["private_auto"],
            })
            # coach, maas, business_van (mode=road)
            road_specs = {
                "coach": {"base_cost": road["coach_fare"], "saving_key": "coach_per_km",
                          "time": road["coach_duration_min"], "access": 18.0, "wait": 30.0,
                          "comfort": 2.0, "flexibility": 1.0, "reliability": 0.08},
                "maas": {"base_cost": road["maas_fare"], "saving_key": "maas_per_km",
                         "time": road["auto_duration_min"] * 1.10, "access": 10.0, "wait": 15.0,
                         "comfort": 3.0, "flexibility": 3.0, "reliability": 0.06},
                "business_van": {"base_cost": road["business_van_fare"],
                                 "saving_key": "business_van_per_km",
                                 "time": road["auto_duration_min"] * 1.02, "access": 5.0,
                                 "wait": 5.0, "comfort": 4.0, "flexibility": 4.0,
                                 "reliability": 0.04},
            }
            affected = set(electric["road_services"])
            for name, spec in road_specs.items():
                saving = 0.0
                if name in affected:
                    saving = case["electrification_savings"][spec["saving_key"]] * distance * pass_through
                road_list.append({
                    "mode": "road",
                    "product": name,
                    "cost": max(1.0, spec["base_cost"] - saving),
                    "iv_time": spec["time"],
                    "ac_time": spec["access"],
                    "wait_time": spec["wait"],
                    "schedule_delay": 0.0,
                    "reliability": spec["reliability"] * spec["time"],
                    "transfers": 0.0,
                    "comfort": spec["comfort"],
                    "flexibility": spec["flexibility"],
                    "asc": case["utility"]["asc_alternative"][name],
                })
            self._road_alts.append(road_list)

        # Max rail alternatives across segments (for padding)
        self._max_rail = max(len(r) for r in self._rail_alts)
        self._max_road = max(len(r) for r in self._road_alts)  # always 4

        # Build rail index arrays: for each segment's rail alt, which product (0,1,2)
        self._rail_product_idx = np.full((self.n_segments, self._max_rail), -1, dtype=np.int32)
        self._rail_base_fare = np.zeros((self.n_segments, self._max_rail), dtype=np.float64)
        self._rail_access_cost = np.zeros((self.n_segments, self._max_rail), dtype=np.float64)
        self._rail_seat_cap = np.zeros((self.n_segments, self._max_rail), dtype=np.float64)
        self._rail_mask = np.zeros((self.n_segments, self._max_rail), dtype=bool)

        product_to_idx = {"G": 0, "D": 1, "K": 2}
        for si, rail_list in enumerate(self._rail_alts):
            for ai, alt in enumerate(rail_list):
                self._rail_product_idx[si, ai] = product_to_idx[alt["product"]]
                self._rail_base_fare[si, ai] = alt["base_fare"]
                self._rail_access_cost[si, ai] = alt["access_cost"]
                self._rail_seat_cap[si, ai] = alt["seat_capacity"]
                self._rail_mask[si, ai] = True

        # supply[segment, rail alternative, pattern] = 1 when the pattern has
        # the same product and actually serves that OD.
        self._rail_pattern_supply = np.zeros(
            (self.n_segments, self._max_rail, self.n_patterns), dtype=np.float64
        )
        for si, seg in enumerate(case["demand_segments"]):
            od = seg["od"]
            for ai in range(self._max_rail):
                pi = int(self._rail_product_idx[si, ai])
                if pi < 0:
                    continue
                for ri, pattern in enumerate(self.patterns):
                    if self._pattern_product_idx[ri] == pi and od in pattern["served_ods"]:
                        self._rail_pattern_supply[si, ai, ri] = 1.0

        # Build line-segment incidence for load factor computation
        # Each OD may traverse multiple line segments
        od_segments = case["network"]["od_segments"]
        all_line_segs: list[str] = []
        for segs in od_segments.values():
            for ls in segs:
                if ls not in all_line_segs:
                    all_line_segs.append(ls)
        self._n_line_segs = len(all_line_segs)
        ls_idx = {ls: i for i, ls in enumerate(all_line_segs)}
        self._line_segments = all_line_segs
        self._pattern_line_incidence = np.zeros(
            (self.n_patterns, self._n_line_segs), dtype=np.float64
        )
        for ri, pattern in enumerate(self.patterns):
            for line_segment in pattern["route_segments"]:
                if line_segment in ls_idx:
                    self._pattern_line_incidence[ri, ls_idx[line_segment]] = 1.0
        # [n_segments, n_line_segs] incidence: 1 if segment's OD traverses that line seg
        self._od_line_incidence = np.zeros((self.n_segments, self._n_line_segs), dtype=np.float64)
        for si, seg in enumerate(case["demand_segments"]):
            od = seg["od"]
            for ls in od_segments.get(od, []):
                self._od_line_incidence[si, ls_idx[ls]] = 1.0

        # Pre-compute load factor groups: (product, period, seat_type, line_segment)
        # Each group accumulates flow from multiple (segment, alt) positions
        self._load_groups: list[dict] = []
        for pi in range(3):
            for ti in range(self.n_periods):
                alt_mask = (self._rail_product_idx == pi) & self._rail_mask
                period_mask = (self._seg_period_idx == ti)
                combined = alt_mask & period_mask[:, None]
                if not combined.any():
                    continue
                seg_idxs, alt_idxs = np.where(combined)
                seat_caps = self._rail_seat_cap[seg_idxs, alt_idxs]
                inc = self._od_line_incidence[seg_idxs]  # [n_pos, n_ls]
                # Determine seat type per position (same product+seat → same cap)
                unique_caps, inv_map = np.unique(seat_caps, return_inverse=True)
                n_unique = len(unique_caps)
                # Build group assignment: group = seat_type * n_ls + line_seg
                n_ls = self._n_line_segs
                ls_indices = np.arange(n_ls)
                # group_ids[pos, ls] = inv_map[pos] * n_ls + ls
                group_ids = inv_map[:, None] * n_ls + ls_indices[None, :]  # [n_pos, n_ls]
                n_groups = n_unique * n_ls
                # Incidence-weighted assignment: only where inc > 0
                active = inc > 0  # [n_pos, n_ls]
                self._load_groups.append({
                    'pi': pi, 'ti': ti,
                    'seg_idxs': seg_idxs,
                    'alt_idxs': alt_idxs,
                    'seat_caps': unique_caps,  # [n_unique]
                    'group_ids': group_ids,  # [n_pos, n_ls]
                    'active': active,  # [n_pos, n_ls]
                    'n_groups': n_groups,
                    'n_ls': n_ls,
                    'n_unique_seats': n_unique,
                })

    def _compute_road_auto_fixed_utils(self) -> np.ndarray:
        """Pre-compute design-independent road/auto utilities.
        Returns array [n_segments, n_classes, max_road] of fixed utility values
        (excluding beta_c * cost which is also fixed for road).
        Actually compute FULL fixed utility since road cost never changes.
        """
        # For road/auto, ALL attributes are fixed. Utility = asc - beta_c*cost - ...
        utils = np.full((self.n_segments, self.n_classes, self._max_road), -np.inf)
        for si, road_list in enumerate(self._road_alts):
            ci = self._seg_class_idx[si]
            for ai, alt in enumerate(road_list):
                # Full utility (all terms are constant)
                for k in range(self.n_classes):
                    b = self._beta[k]
                    u = (alt["asc"]
                         - b[0] * alt["cost"]
                         - b[1] * alt["iv_time"]
                         - b[2] * alt["ac_time"]
                         - b[3] * alt["wait_time"]
                         - b[4] * alt["schedule_delay"]
                         - b[5] * alt["reliability"]
                         - b[6] * alt["transfers"]
                         + b[7] * alt["comfort"]
                         + b[8] * alt["flexibility"])
                    utils[si, k, ai] = u
        return utils

    def _compute_rail_fixed_utils(self) -> np.ndarray:
        """Pre-compute the fixed part of rail utilities (everything except fare and sched_delay).
        Returns [n_segments, n_classes, max_rail].
        fixed_part = asc - beta_iv*iv - beta_ac*ac - beta_wt*wait - beta_rel*rel - beta_tr*tr
                     + gamma_com*comfort + gamma_flex*flex
        Design-dependent: - beta_c * (base_fare*phi + access_cost) - beta_sc * sched_delay
        """
        fixed = np.full((self.n_segments, self.n_classes, self._max_rail), -np.inf)
        for si, rail_list in enumerate(self._rail_alts):
            for ai, alt in enumerate(rail_list):
                for k in range(self.n_classes):
                    b = self._beta[k]
                    val = (alt["asc"]
                           - b[1] * alt["iv_time"]
                           - b[2] * alt["ac_time"]
                           - b[3] * alt["wait_time"]
                           - b[5] * alt["reliability"]
                           - b[6] * alt["transfers"]
                           + b[7] * alt["comfort"]
                           + b[8] * alt["flexibility"])
                    fixed[si, k, ai] = val
        return fixed

    def evaluate_single(self, N: np.ndarray, phi: np.ndarray) -> dict[str, Any]:
        """Evaluate one design. N[patterns, periods], phi[3, periods].
        Returns metrics dict compatible with case_model.evaluate_design output.
        """
        result = self.evaluate_batch(N[None], phi[None])
        return {k: v[0] if isinstance(v, np.ndarray) else v for k, v in result.items()}

    def evaluate_batch(
        self, N_batch: np.ndarray, phi_batch: np.ndarray, *,
        return_details: bool = False,
    ) -> dict[str, Any]:
        """Batch evaluate multiple designs.

        Parameters
        ----------
        N_batch : ndarray [batch, n_patterns, n_periods] int
        phi_batch : ndarray [batch, 3, n_periods] float

        Returns
        -------
        dict of arrays, each [batch]:
            revenue, operating_cost, profit, consumer_benefit, welfare_level,
            total_trips, participation_rate, rail_pax, road_pax, auto_pax,
            max_load_factor, vulnerable_trips, feasible indicators, etc.
        """
        batch = N_batch.shape[0]
        N_b = N_batch.astype(np.float64)  # [batch, 3, n_periods]
        phi_b = phi_batch.astype(np.float64)

        # For each segment, get the relevant phi and N values
        # seg_period_idx[si] -> period index for that segment
        # rail_product_idx[si, ai] -> product index for that rail alt
        # phi_seg[batch, si, ai] = phi_b[batch, product_idx[si,ai], period_idx[si]]
        # N_seg[batch, si, ai] = N_b[batch, product_idx[si,ai], period_idx[si]]

        # Expand for broadcasting
        p_idx = self._rail_product_idx  # [n_seg, max_rail]
        t_idx = self._seg_period_idx  # [n_seg]

        # Product-period fares retain the original shape.
        t_idx_expanded = np.broadcast_to(t_idx[:, None], p_idx.shape)  # [n_seg, max_rail]
        phi_seg = phi_b[:, p_idx, t_idx_expanded]  # [batch, n_seg, max_rail]

        # Effective frequency of a product/seat alternative equals the sum of
        # service-pattern departures that cover its OD.
        n_by_segment_pattern = np.transpose(
            N_b[:, :, t_idx], (0, 2, 1)
        )  # [batch, n_seg, n_patterns]
        N_seg = np.einsum(
            "bsp,sap->bsa", n_by_segment_pattern, self._rail_pattern_supply,
            optimize=True,
        )

        # Schedule delay = vartheta * duration_h / N
        duration_seg = self._duration_h[t_idx]  # [n_seg]
        # Avoid division by zero: where N<=0, alt is inactive
        with np.errstate(divide='ignore', invalid='ignore'):
            sched_delay = self._vartheta * duration_seg[None, :, None] / N_seg  # [batch, n_seg, max_rail]

        # Rail cost = base_fare * phi + access_cost
        rail_cost = (self._rail_base_fare[None] * phi_seg
                     + self._rail_access_cost[None])  # [batch, n_seg, max_rail]

        # Rail utility = fixed_part - beta_c * cost - beta_sc * sched_delay
        # beta_c per segment's class: self._beta[class_idx, 0]
        beta_c_seg = self._beta[self._seg_class_idx, 0]  # [n_seg]
        beta_sc_seg = self._beta[self._seg_class_idx, 4]  # [n_seg]

        # rail_fixed_utils: [n_seg, n_classes, max_rail] -> pick the segment's class
        # For each segment si, we want rail_fixed_utils[si, class_idx[si], :]
        rail_fixed_seg = self._rail_fixed_utils[
            np.arange(self.n_segments), self._seg_class_idx, :
        ]  # [n_seg, max_rail]

        rail_utils = (rail_fixed_seg[None, :, :]
                      - beta_c_seg[None, :, None] * rail_cost
                      - beta_sc_seg[None, :, None] * sched_delay)  # [batch, n_seg, max_rail]

        # Mask inactive alternatives: N<=0 or no rail alt
        active_mask = (N_seg > 0) & self._rail_mask[None]  # [batch, n_seg, max_rail]
        rail_utils = np.where(active_mask, rail_utils, -np.inf)

        # Road/auto utilities (fixed, only need the segment's class)
        road_utils_seg = self._road_auto_fixed_utils[
            np.arange(self.n_segments), self._seg_class_idx, :
        ]  # [n_seg, max_road]
        road_utils = np.broadcast_to(
            road_utils_seg[None, :, :], (batch, self.n_segments, self._max_road)
        ).copy()

        # Identify which road alts are "auto" vs "road" mode
        # First alt is always auto (private_auto), rest are road
        auto_mask = np.zeros(self._max_road, dtype=bool)
        auto_mask[0] = True
        road_mode_mask = np.zeros(self._max_road, dtype=bool)
        road_mode_mask[1:] = True

        # --- Nested Logit Computation ---
        # Level 1: within-nest logsumexp
        # Rail nest
        rail_lse = _sp_logsumexp(
            rail_utils / self._mu_rail, axis=2
        ) * self._mu_rail  # [batch, n_seg]
        # Handle segments with no active rail alts
        rail_has_active = active_mask.any(axis=2)  # [batch, n_seg]
        rail_lse = np.where(rail_has_active, rail_lse, -np.inf)

        # Road nest (fixed)
        road_vals = road_utils[:, :, road_mode_mask]  # [batch, n_seg, 3]
        road_lse = _sp_logsumexp(
            road_vals / self._mu_road, axis=2
        ) * self._mu_road  # [batch, n_seg]

        # Auto nest (fixed, single alt)
        auto_vals = road_utils[:, :, auto_mask]  # [batch, n_seg, 1]
        auto_lse = _sp_logsumexp(
            auto_vals / self._mu_auto, axis=2
        ) * self._mu_auto  # [batch, n_seg]

        # Level 2: mode level
        # asc_mode per segment's class
        asc_rail = self._asc_mode_rail[self._seg_class_idx]  # [n_seg]
        asc_road = self._asc_mode_road[self._seg_class_idx]
        asc_auto = self._asc_mode_auto[self._seg_class_idx]

        mode_vals = np.stack([
            asc_rail[None, :] + rail_lse,
            asc_road[None, :] + road_lse,
            asc_auto[None, :] + auto_lse,
        ], axis=2)  # [batch, n_seg, 3]

        # Mask rail mode if no active rail
        mode_vals[:, :, 0] = np.where(rail_has_active, mode_vals[:, :, 0], -np.inf)

        mode_lse = _sp_logsumexp(
            mode_vals / self._mu_mode, axis=2
        ) * self._mu_mode  # [batch, n_seg]

        # Level 3: top level (travel vs no-travel)
        alpha_travel = self._alpha_travel[self._seg_class_idx]  # [n_seg]
        travel_val = alpha_travel[None, :] + mode_lse  # [batch, n_seg]
        no_travel_val = np.zeros_like(travel_val)

        top_vals = np.stack([travel_val, no_travel_val], axis=2)  # [batch, n_seg, 2]
        top_lse = _sp_logsumexp(top_vals / self._mu_top, axis=2) * self._mu_top

        # Participation probability
        participation = np.exp(
            (travel_val - top_lse) / self._mu_top
        )  # [batch, n_seg]

        # Mode probabilities (softmax with scale mu_mode)
        mode_probs = np.exp(mode_vals / self._mu_mode - (mode_lse / self._mu_mode)[:, :, None])  # [batch, n_seg, 3]
        rail_mode_prob = mode_probs[:, :, 0]  # [batch, n_seg]

        # --- Revenue and flow computation ---
        # Rail conditional probabilities within rail nest
        rail_cond = np.exp(rail_utils / self._mu_rail - (rail_lse / self._mu_rail)[:, :, None])
        rail_cond = np.where(active_mask, rail_cond, 0.0)  # [batch, n_seg, max_rail]

        # Flow per rail alternative = qbar * participation * rail_mode_prob * rail_cond
        qbar = self._qbar[None, :, None]  # [1, n_seg, 1]
        part = participation[:, :, None]  # [batch, n_seg, 1]
        rmp = rail_mode_prob[:, :, None]  # [batch, n_seg, 1]
        rail_flow = qbar * part * rmp * rail_cond  # [batch, n_seg, max_rail]

        # Revenue = sum(flow * rail_fare) where rail_fare = base_fare * phi
        rail_fare_actual = self._rail_base_fare[None] * phi_seg  # [batch, n_seg, max_rail]
        revenue = np.sum(rail_flow * rail_fare_actual, axis=(1, 2))  # [batch]

        # Total trips
        total_trips = np.sum(self._qbar[None, :] * participation, axis=1)  # [batch]
        total_potential = float(np.sum(self._qbar))

        # Rail pax
        rail_pax = np.sum(rail_flow, axis=(1, 2))  # [batch]

        # Road and auto pax
        road_cond = np.exp(road_vals / self._mu_road
                           - (road_lse / self._mu_road)[:, :, None])
        road_flow = qbar * part * mode_probs[:, :, 1:2] * road_cond
        road_pax = np.sum(road_flow, axis=(1, 2))

        auto_cond = np.exp(auto_vals / self._mu_auto
                           - (auto_lse / self._mu_auto)[:, :, None])
        auto_flow = qbar * part * mode_probs[:, :, 2:3] * auto_cond
        auto_pax = np.sum(auto_flow, axis=(1, 2))

        # Consumer benefit = sum(qbar / beta_c * logsum)
        beta_c_per_seg = self._beta[self._seg_class_idx, 0]  # [n_seg]
        consumer_benefit = np.sum(
            self._qbar[None, :] / beta_c_per_seg[None, :] * top_lse, axis=1
        )  # [batch]

        # The vulnerable class is declared by input and may be in any position.
        vuln_idx = self._vulnerable_class_idx
        vuln_mask = (self._seg_class_idx == vuln_idx)
        vulnerable_trips = np.sum(
            self._qbar[None, vuln_mask] * participation[:, vuln_mask], axis=1
        )  # [batch]

        # Max load factor: per (product, seat_type, period, line_segment)
        max_load = np.zeros(batch, dtype=np.float64)
        for grp in self._load_groups:
            pi, ti = grp['pi'], grp['ti']
            # Extract flow at matching positions: [batch, n_pos]
            flows = rail_flow[:, grp['seg_idxs'], grp['alt_idxs']]
            # Expand by line segments: [batch, n_pos, n_ls]
            flows_exp = flows[:, :, None] * grp['active'][None, :, :]
            # Flatten positions × line_segs for bincount
            flat_flows = flows_exp.reshape(batch, -1)  # [batch, n_pos*n_ls]
            flat_ids = grp['group_ids'].ravel()  # [n_pos*n_ls]
            # Sum flows per group using bincount
            n_grp = grp['n_groups']
            load_sums = np.array([
                np.bincount(flat_ids, weights=flat_flows[b], minlength=n_grp)
                for b in range(batch)
            ])  # [batch, n_groups]
            # Capacity varies by line segment because patterns can cover
            # different ODs.  Sum departures of this product that traverse
            # each segment, then apply the relevant seat capacity.
            pattern_mask = self._pattern_product_idx == pi
            departures_by_line = (
                N_b[:, pattern_mask, ti]
                @ self._pattern_line_incidence[pattern_mask]
            )  # [batch, n_ls]
            n_ls = grp['n_ls']
            group_seat_caps = np.repeat(grp['seat_caps'], n_ls)  # [n_groups]
            group_departures = np.tile(
                departures_by_line, (1, grp['n_unique_seats'])
            )
            caps = group_departures * group_seat_caps[None, :]
            with np.errstate(divide='ignore', invalid='ignore'):
                ratios = np.where(
                    caps > 0,
                    load_sums / caps,
                    np.where(load_sums > 1e-8, np.inf, 0.0)
                )
            max_ratio = ratios.max(axis=1)  # [batch]
            max_load = np.maximum(max_load, max_ratio)

        # Operating cost
        costs = self.case["costs"]
        op_cost = np.zeros(batch, dtype=np.float64)
        for pi, product in enumerate(PRODUCTS):
            product_patterns = self._pattern_product_idx == pi
            total_dep = N_b[:, product_patterns, :].sum(axis=(1, 2))
            active_prod = total_dep > 0
            fixed = costs["fixed_per_product_day"][product]
            op_cost += np.where(active_prod, fixed, 0.0)
        for ri, pattern in enumerate(self.patterns):
            product = pattern["product"]
            dep = N_b[:, ri, :].sum(axis=1)
            variable = (
                costs["per_run"][product]
                + costs["per_train_km"][product] * self._pattern_route_length[ri]
            )
            op_cost += dep * variable
            op_cost += np.where(
                dep > 0, self._pattern_activation_cost[ri], 0.0
            )

        profit = revenue - op_cost
        welfare = consumer_benefit + profit

        result = {
            "revenue": revenue,
            "operating_cost": op_cost,
            "profit": profit,
            "consumer_benefit": consumer_benefit,
            "welfare_level": welfare,
            "total_potential": np.full(batch, total_potential),
            "total_trips": total_trips,
            "participation_rate": total_trips / total_potential,
            "rail_pax": rail_pax,
            "road_pax": road_pax,
            "auto_pax": auto_pax,
            "rail_share_among_trips": rail_pax / np.maximum(total_trips, 1e-12),
            "vulnerable_trips": vulnerable_trips,
            "max_load_factor": max_load,
        }
        if return_details:
            result["_details"] = {
                "participation": participation,
                "mode_probabilities": mode_probs,
                "rail_flow": rail_flow,
                "road_flow": road_flow,
                "auto_flow": auto_flow,
                "rail_fare": rail_fare_actual,
                "rail_generalized_cost": rail_cost,
                "effective_frequency": N_seg,
                "schedule_delay": sched_delay,
                "top_logsum": top_lse,
            }
        return result

    @staticmethod
    def _new_flow_bucket() -> dict[str, float]:
        return {
            "potential": 0.0,
            "trips": 0.0,
            "rail_pax": 0.0,
            "road_pax": 0.0,
            "auto_pax": 0.0,
            "rail_revenue": 0.0,
        }

    @staticmethod
    def _finish_flow_bucket(bucket: dict[str, float]) -> dict[str, float]:
        potential = max(float(bucket["potential"]), 1e-12)
        trips = max(float(bucket["trips"]), 1e-12)
        result = {key: float(value) for key, value in bucket.items()}
        result["participation_rate"] = float(bucket["trips"] / potential)
        result["rail_share_among_trips"] = float(bucket["rail_pax"] / trips)
        return result

    def evaluate_detailed(self, N: np.ndarray, phi: np.ndarray) -> dict[str, Any]:
        """Evaluate one final design and return publication-oriented breakdowns.

        This method is intentionally separate from the hot search path.  It
        exposes class, OD, period, product, and seat flows only for a final
        incumbent, while ``evaluate_batch`` remains compact for candidate
        screening.
        """
        evaluated = self.evaluate_batch(
            N[None], phi[None], return_details=True
        )
        raw = {
            key: value[0] for key, value in evaluated["_details"].items()
        }
        metrics = {
            key: float(value[0]) for key, value in evaluated.items()
            if key != "_details"
        }

        by_class = {name: self._new_flow_bucket() for name in self.classes}
        by_od = {
            name: self._new_flow_bucket()
            for name in dict.fromkeys(self._seg_od)
        }
        by_period = {
            name: self._new_flow_bucket() for name in self.periods
        }
        rail_by_product = {
            product: {"pax": 0.0, "revenue": 0.0} for product in PRODUCTS
        }
        rail_by_product_period: dict[str, dict[str, float]] = {}
        rail_by_od_product: dict[str, dict[str, float]] = {}
        rail_by_seat: dict[str, dict[str, float]] = {}

        for si in range(self.n_segments):
            qbar = float(self._qbar[si])
            trips = qbar * float(raw["participation"][si])
            rail_pax = float(np.sum(raw["rail_flow"][si]))
            road_pax = float(np.sum(raw["road_flow"][si]))
            auto_pax = float(np.sum(raw["auto_flow"][si]))
            rail_revenue = float(np.sum(
                raw["rail_flow"][si] * raw["rail_fare"][si]
            ))
            for bucket in (
                by_class[self._seg_class[si]],
                by_od[self._seg_od[si]],
                by_period[self._seg_period[si]],
            ):
                bucket["potential"] += qbar
                bucket["trips"] += trips
                bucket["rail_pax"] += rail_pax
                bucket["road_pax"] += road_pax
                bucket["auto_pax"] += auto_pax
                bucket["rail_revenue"] += rail_revenue

            for ai, alt in enumerate(self._rail_alts[si]):
                flow = float(raw["rail_flow"][si, ai])
                if flow <= 0:
                    continue
                revenue_i = flow * float(raw["rail_fare"][si, ai])
                product = str(alt["product"])
                seat = str(alt["seat"])
                period = self._seg_period[si]
                od = self._seg_od[si]
                rail_by_product[product]["pax"] += flow
                rail_by_product[product]["revenue"] += revenue_i
                for container, key in (
                    (rail_by_product_period, f"{product}|{period}"),
                    (rail_by_od_product, f"{od}|{product}"),
                    (rail_by_seat, f"{product}|{seat}"),
                ):
                    bucket = container.setdefault(
                        key, {"pax": 0.0, "revenue": 0.0}
                    )
                    bucket["pax"] += flow
                    bucket["revenue"] += revenue_i

        for cls, bucket in by_class.items():
            ci = self.classes.index(cls)
            bucket["value_of_time_per_hour"] = float(
                60.0 * self._beta[ci, 1] / self._beta[ci, 0]
            )

        def finish_rail(container: dict[str, dict[str, float]]) -> dict[str, Any]:
            finished: dict[str, Any] = {}
            for key, bucket in container.items():
                pax = float(bucket["pax"])
                finished[key] = {
                    "pax": pax,
                    "revenue": float(bucket["revenue"]),
                    "average_fare": float(bucket["revenue"] / max(pax, 1e-12)),
                }
            return finished

        effective_frequency: dict[str, dict[str, int]] = {}
        for si, od in enumerate(self._seg_od):
            period = self._seg_period[si]
            for ai, alt in enumerate(self._rail_alts[si]):
                key = f"{od}|{alt['product']}"
                period_values = effective_frequency.setdefault(key, {})
                period_values[period] = int(round(
                    float(raw["effective_frequency"][si, ai])
                ))

        return {
            "metrics": metrics,
            "by_class": {
                key: {
                    **self._finish_flow_bucket(bucket),
                    "value_of_time_per_hour": float(
                        bucket["value_of_time_per_hour"]
                    ),
                }
                for key, bucket in by_class.items()
            },
            "by_od": {
                key: self._finish_flow_bucket(bucket)
                for key, bucket in by_od.items()
            },
            "by_period": {
                key: self._finish_flow_bucket(bucket)
                for key, bucket in by_period.items()
            },
            "rail_by_product": finish_rail(rail_by_product),
            "rail_by_product_period": finish_rail(rail_by_product_period),
            "rail_by_od_product": finish_rail(rail_by_od_product),
            "rail_by_seat": finish_rail(rail_by_seat),
            "effective_frequency_by_od_product_period": effective_frequency,
        }
