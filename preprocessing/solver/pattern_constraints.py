"""Exact feasibility checks and one-shot MILP start repair for pattern designs."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

try:
    import coptpy as cp
except ImportError:  # portable fallback for environments without COPT
    cp = None


PRODUCTS = ("G", "D", "K")
REGIMES = ("incumbent_only", "incumbent_plus_candidate")


class PatternConstraintSystem:
    """Represent all linear constraints without per-candidate MILP calls.

    Search candidates are batch-filtered against the exact linear system.  A
    small MILP is used only once when a requested regime's natural starting
    point is infeasible.
    """

    def __init__(self, case: dict[str, Any]):
        self.case = case
        self.patterns = list(case["service_patterns"])
        self.pattern_ids = [pattern["id"] for pattern in self.patterns]
        self.periods = list(case["sets"]["periods"])
        self.ods = list(case["sets"]["ods"])
        self.line_segments = list(case["network"]["segments"])
        self.n_patterns = len(self.patterns)
        self.n_periods = len(self.periods)
        self.n_lines = len(self.line_segments)
        self.n_ods = len(self.ods)
        self._product_index = {product: i for i, product in enumerate(PRODUCTS)}

        self.pattern_product_idx = np.array(
            [self._product_index[pattern["product"]] for pattern in self.patterns],
            dtype=np.int32,
        )
        self.pattern_status = np.array(
            [str(pattern.get("status", "incumbent_observed")) for pattern in self.patterns],
            dtype=object,
        )
        self.incumbent_mask = self.pattern_status == "incumbent_observed"
        self.candidate_mask = self.pattern_status == "candidate_synthetic"
        unknown_status = sorted(set(self.pattern_status) - {
            "incumbent_observed", "candidate_synthetic"
        })
        if unknown_status:
            raise ValueError(f"Unknown service-pattern status values: {unknown_status}")
        self.freq_max = np.array(
            [[int(pattern["frequency_max"][period]) for period in self.periods]
             for pattern in self.patterns],
            dtype=np.int32,
        )
        self.cycle_time = np.array(
            [float(pattern["cycle_time_h"]) for pattern in self.patterns],
            dtype=np.float64,
        )
        self.line_incidence = np.array(
            [[1.0 if line in pattern["route_segments"] else 0.0
              for line in self.line_segments]
             for pattern in self.patterns],
            dtype=np.float64,
        )
        self.od_incidence = np.array(
            [[1.0 if od in pattern["served_ods"] else 0.0 for od in self.ods]
             for pattern in self.patterns],
            dtype=np.float64,
        )
        self.line_capacity = np.array(
            [float(case["constraints"]["line_capacity_per_hour"])
             * float(case["sets"]["periods"][period]["duration_h"])
             for period in self.periods],
            dtype=np.float64,
        )
        self.fleet_available = np.array(
            [float(case["products"][product]["fleet_size"]) * 24.0
             for product in PRODUCTS],
            dtype=np.float64,
        )
        self.daily_floor = np.array(
            [int(case["pattern_constraints"]["minimum_daily_departures_by_product"][product])
             for product in PRODUCTS],
            dtype=np.int32,
        )
        self.incumbent_pattern_floor = int(
            case["pattern_constraints"].get(
                "minimum_daily_departures_by_incumbent_pattern", 1
            )
        )
        candidate_default = int(
            case["pattern_constraints"].get(
                "minimum_daily_departures_by_candidate_when_active", 1
            )
        )
        self.candidate_active_floor = np.array(
            [
                int(pattern.get(
                    "minimum_daily_departures_if_active", candidate_default
                ))
                for pattern in self.patterns
            ],
            dtype=np.int32,
        )
        self.min_od_service = int(case["constraints"]["min_od_departures_per_period"])
        self.fare_lo = float(case["constraints"]["fare_bounds"][0])
        self.fare_hi = float(case["constraints"]["fare_bounds"][1])
        self.linear_repair_backend = "copt" if cp is not None else "scipy_milp"

    def _validate_regime(self, regime: str) -> None:
        if regime not in REGIMES:
            raise ValueError(f"Unknown service-pattern regime: {regime}")

    def natural_start(self, regime: str) -> np.ndarray:
        self._validate_regime(regime)
        N = np.zeros((self.n_patterns, self.n_periods), dtype=np.int32)
        for ri, pattern in enumerate(self.patterns):
            if self.incumbent_mask[ri]:
                N[ri] = [int(pattern["observed_frequency"][p]) for p in self.periods]
        np.minimum(N, self.freq_max, out=N)
        if self.linear_feasible_batch(N[None], regime)[0]:
            return N
        return self.repair_start(N, regime)

    def linear_feasible_batch(self, N_batch: np.ndarray, regime: str) -> np.ndarray:
        self._validate_regime(regime)
        N = np.asarray(N_batch, dtype=np.float64)
        if N.ndim != 3 or N.shape[1:] != (self.n_patterns, self.n_periods):
            raise ValueError("N_batch has incompatible shape")
        feasible = np.all((N >= 0) & (N <= self.freq_max[None]), axis=(1, 2))

        if regime == "incumbent_only" and np.any(self.candidate_mask):
            feasible &= np.all(N[:, self.candidate_mask, :] == 0, axis=(1, 2))

        if np.any(self.incumbent_mask):
            incumbent_daily = N[:, self.incumbent_mask, :].sum(axis=2)
            feasible &= np.all(
                incumbent_daily >= self.incumbent_pattern_floor, axis=1
            )
        if np.any(self.candidate_mask):
            candidate_daily = N[:, self.candidate_mask, :].sum(axis=2)
            candidate_floors = self.candidate_active_floor[self.candidate_mask]
            feasible &= np.all(
                (candidate_daily == 0)
                | (candidate_daily >= candidate_floors[None, :]),
                axis=1,
            )

        # Existing G and D products remain in service, but may reduce frequency.
        for pi, floor in enumerate(self.daily_floor):
            if floor <= 0:
                continue
            mask = self.pattern_product_idx == pi
            feasible &= N[:, mask, :].sum(axis=(1, 2)) >= floor

        line_use = np.einsum("brt,re->bte", N, self.line_incidence, optimize=True)
        feasible &= np.all(line_use <= self.line_capacity[None, :, None] + 1e-9, axis=(1, 2))

        for pi in range(len(PRODUCTS)):
            mask = self.pattern_product_idx == pi
            hours = np.sum(N[:, mask, :] * self.cycle_time[None, mask, None], axis=(1, 2))
            feasible &= hours <= self.fleet_available[pi] + 1e-9

        od_service = np.einsum("brt,ro->bto", N, self.od_incidence, optimize=True)
        feasible &= np.all(od_service >= self.min_od_service - 1e-9, axis=(1, 2))
        return feasible

    def linear_violations(self, N: np.ndarray, regime: str) -> dict[str, float]:
        self._validate_regime(regime)
        Nf = np.asarray(N, dtype=np.float64)
        violations: dict[str, float] = {}
        bound_gap = np.maximum(-Nf, 0.0)
        bound_gap = np.maximum(bound_gap, np.maximum(Nf - self.freq_max, 0.0))
        if np.max(bound_gap) > 0:
            violations["frequency_bounds"] = float(np.max(bound_gap / np.maximum(1, self.freq_max)))

        if regime == "incumbent_only" and np.any(Nf[self.candidate_mask] > 0):
            violations["candidate_forbidden"] = float(
                np.sum(Nf[self.candidate_mask])
            )
        if np.any(self.incumbent_mask):
            missing = np.maximum(
                float(self.incumbent_pattern_floor)
                - Nf[self.incumbent_mask].sum(axis=1),
                0.0,
            )
            if np.max(missing, initial=0.0) > 0:
                violations["incumbent_pattern_daily_floor"] = float(np.max(missing))
        if np.any(self.candidate_mask):
            candidate_daily = Nf[self.candidate_mask].sum(axis=1)
            candidate_floor = self.candidate_active_floor[self.candidate_mask]
            partial = np.where(
                candidate_daily > 0,
                np.maximum(candidate_floor - candidate_daily, 0.0),
                0.0,
            )
            if np.max(partial, initial=0.0) > 0:
                violations["candidate_activation_floor"] = float(np.max(partial))

        product_floor_gap = 0.0
        for pi, floor in enumerate(self.daily_floor):
            if floor > 0:
                supplied = float(Nf[self.pattern_product_idx == pi].sum())
                product_floor_gap = max(product_floor_gap, max(0.0, floor - supplied) / floor)
        if product_floor_gap > 0:
            violations["existing_product_daily_floor"] = product_floor_gap

        line_use = np.einsum("rt,re->te", Nf, self.line_incidence, optimize=True)
        line_ratio = line_use / self.line_capacity[:, None]
        if float(np.max(line_ratio)) > 1.0 + 1e-9:
            violations["line_path_capacity"] = float(np.max(line_ratio) - 1.0)

        fleet_ratio = 0.0
        for pi in range(len(PRODUCTS)):
            mask = self.pattern_product_idx == pi
            hours = float(np.sum(Nf[mask] * self.cycle_time[mask, None]))
            fleet_ratio = max(fleet_ratio, hours / self.fleet_available[pi])
        if fleet_ratio > 1.0 + 1e-9:
            violations["fleet_hours"] = fleet_ratio - 1.0

        od_service = np.einsum("rt,ro->to", Nf, self.od_incidence, optimize=True)
        service_gap = float(np.max(np.maximum(self.min_od_service - od_service, 0.0)))
        if service_gap > 0:
            violations["minimum_od_service"] = service_gap / max(1, self.min_od_service)
        return violations

    def constraint_report(
        self, N: np.ndarray, phi: np.ndarray, regime: str
    ) -> dict[str, Any]:
        """Return final-design use, limits, slacks, and utilization ratios."""
        self._validate_regime(regime)
        Nf = np.asarray(N, dtype=np.float64)
        phif = np.asarray(phi, dtype=np.float64)

        frequency = []
        for ri, pattern_id in enumerate(self.pattern_ids):
            for ti, period in enumerate(self.periods):
                used = float(Nf[ri, ti])
                upper = float(self.freq_max[ri, ti])
                frequency.append({
                    "pattern_id": pattern_id,
                    "period": period,
                    "departures": int(round(used)),
                    "upper_bound": int(round(upper)),
                    "upper_slack": float(upper - used),
                    "utilization": float(used / upper) if upper > 0 else 0.0,
                })

        product_daily = []
        for pi, product in enumerate(PRODUCTS):
            mask = self.pattern_product_idx == pi
            used = float(Nf[mask].sum())
            floor = float(self.daily_floor[pi])
            product_daily.append({
                "product": product,
                "departures": int(round(used)),
                "minimum": int(round(floor)),
                "slack": float(used - floor),
                "binding": bool(floor > 0 and abs(used - floor) <= 1e-9),
            })

        line_use = np.einsum("rt,re->te", Nf, self.line_incidence, optimize=True)
        line_capacity = []
        for ti, period in enumerate(self.periods):
            for ei, segment in enumerate(self.line_segments):
                used = float(line_use[ti, ei])
                capacity = float(self.line_capacity[ti])
                line_capacity.append({
                    "period": period,
                    "line_segment": segment,
                    "used_paths": used,
                    "capacity": capacity,
                    "slack": float(capacity - used),
                    "utilization": float(used / capacity) if capacity > 0 else 0.0,
                    "binding": bool(abs(capacity - used) <= 1e-9),
                })

        fleet_hours = []
        for pi, product in enumerate(PRODUCTS):
            mask = self.pattern_product_idx == pi
            used = float(np.sum(Nf[mask] * self.cycle_time[mask, None]))
            available = float(self.fleet_available[pi])
            fleet_hours.append({
                "product": product,
                "used_hours": used,
                "available_hours": available,
                "slack_hours": float(available - used),
                "utilization": float(used / available) if available > 0 else 0.0,
                "binding": bool(abs(available - used) <= 1e-9),
            })

        od_service_matrix = np.einsum(
            "rt,ro->to", Nf, self.od_incidence, optimize=True
        )
        od_service = []
        for ti, period in enumerate(self.periods):
            for oi, od in enumerate(self.ods):
                used = float(od_service_matrix[ti, oi])
                minimum = float(self.min_od_service)
                od_service.append({
                    "period": period,
                    "od": od,
                    "departures": int(round(used)),
                    "minimum": int(round(minimum)),
                    "slack": float(used - minimum),
                    "binding": bool(abs(used - minimum) <= 1e-9),
                })

        fare_bounds = []
        for pi, product in enumerate(PRODUCTS):
            for ti, period in enumerate(self.periods):
                value = float(phif[pi, ti])
                fare_bounds.append({
                    "product": product,
                    "period": period,
                    "multiplier": value,
                    "lower_bound": self.fare_lo,
                    "upper_bound": self.fare_hi,
                    "lower_slack": float(value - self.fare_lo),
                    "upper_slack": float(self.fare_hi - value),
                    "binding": bool(
                        abs(value - self.fare_lo) <= 1e-9
                        or abs(value - self.fare_hi) <= 1e-9
                    ),
                })

        pattern_daily = []
        for ri, pattern_id in enumerate(self.pattern_ids):
            used = float(Nf[ri].sum())
            status = str(self.pattern_status[ri])
            minimum = (
                float(self.incumbent_pattern_floor)
                if status == "incumbent_observed" else 0.0
            )
            pattern_daily.append({
                "pattern_id": pattern_id,
                "product": self.patterns[ri]["product"],
                "status": status,
                "departures": int(round(used)),
                "minimum": int(round(minimum)),
                "active": bool(used > 0),
                "binding": bool(minimum > 0 and abs(used - minimum) <= 1e-9),
            })

        k_mask = self.pattern_product_idx == self._product_index["K"]
        k_pattern_daily = {
            self.pattern_ids[ri]: int(round(float(Nf[ri].sum())))
            for ri in np.flatnonzero(k_mask)
        }
        return {
            "regime": regime,
            "linear_feasible": bool(
                self.linear_feasible_batch(Nf[None], regime)[0]
            ),
            "linear_violations": self.linear_violations(Nf, regime),
            "frequency_bounds": frequency,
            "product_daily_service": product_daily,
            "pattern_daily_service": pattern_daily,
            "line_capacity": line_capacity,
            "fleet_hours": fleet_hours,
            "minimum_od_service": od_service,
            "fare_bounds": fare_bounds,
            "k_pattern_daily_departures": k_pattern_daily,
        }

    def _repair_start_copt(self, target: np.ndarray, regime: str) -> np.ndarray:
        """Find the closest feasible integer start with COPT."""
        if cp is None:
            raise RuntimeError("COPTpy is unavailable")
        self._validate_regime(regime)
        target = np.asarray(target, dtype=np.float64)
        env = cp.Envr()
        model = env.createModel("pattern_start_repair")
        model.setParam(cp.COPT.Param.Logging, 0)
        model.setParam(cp.COPT.Param.Threads, 1)
        model.setParam(cp.COPT.Param.TimeLimit, 10.0)
        model.setParam(cp.COPT.Param.RelGap, 0.0)

        n_vars: list[list[Any]] = []
        dp_vars: list[list[Any]] = []
        dm_vars: list[list[Any]] = []
        for ri in range(self.n_patterns):
            n_row = []
            dp_row = []
            dm_row = []
            for ti in range(self.n_periods):
                upper = int(self.freq_max[ri, ti])
                if regime == "incumbent_only" and self.candidate_mask[ri]:
                    upper = 0
                n_row.append(model.addVar(
                    lb=0.0, ub=float(upper), vtype=cp.COPT.INTEGER,
                    name=f"N_{ri}_{ti}",
                ))
                dp_row.append(model.addVar(lb=0.0, name=f"dp_{ri}_{ti}"))
                dm_row.append(model.addVar(lb=0.0, name=f"dm_{ri}_{ti}"))
            n_vars.append(n_row)
            dp_vars.append(dp_row)
            dm_vars.append(dm_row)

        objective_terms = []
        for ri in range(self.n_patterns):
            for ti in range(self.n_periods):
                model.addConstr(
                    n_vars[ri][ti] - dp_vars[ri][ti] + dm_vars[ri][ti]
                    == float(target[ri, ti])
                )
                weight = 1.0 / max(1.0, float(self.freq_max[ri, ti]))
                objective_terms.append(weight * (dp_vars[ri][ti] + dm_vars[ri][ti]))
        model.setObjective(cp.quicksum(objective_terms), cp.COPT.MINIMIZE)

        for ri in np.flatnonzero(self.incumbent_mask):
            model.addConstr(
                cp.quicksum(n_vars[int(ri)][ti] for ti in range(self.n_periods))
                >= float(self.incumbent_pattern_floor)
            )
        for pi, floor in enumerate(self.daily_floor):
            if floor <= 0:
                continue
            model.addConstr(cp.quicksum(
                n_vars[ri][ti]
                for ri in range(self.n_patterns)
                if self.pattern_product_idx[ri] == pi
                for ti in range(self.n_periods)
            ) >= float(floor))
        if regime == "incumbent_plus_candidate":
            for ri in np.flatnonzero(self.candidate_mask):
                if float(target[int(ri)].sum()) > 0:
                    model.addConstr(
                        cp.quicksum(
                            n_vars[int(ri)][ti] for ti in range(self.n_periods)
                        ) >= float(self.candidate_active_floor[int(ri)])
                    )
        for ti in range(self.n_periods):
            for ei in range(self.n_lines):
                model.addConstr(cp.quicksum(
                    float(self.line_incidence[ri, ei]) * n_vars[ri][ti]
                    for ri in range(self.n_patterns)
                    if self.line_incidence[ri, ei] > 0
                ) <= float(self.line_capacity[ti]))
        for pi in range(len(PRODUCTS)):
            model.addConstr(cp.quicksum(
                float(self.cycle_time[ri]) * n_vars[ri][ti]
                for ri in range(self.n_patterns)
                if self.pattern_product_idx[ri] == pi
                for ti in range(self.n_periods)
            ) <= float(self.fleet_available[pi]))
        for ti in range(self.n_periods):
            for oi in range(self.n_ods):
                model.addConstr(cp.quicksum(
                    float(self.od_incidence[ri, oi]) * n_vars[ri][ti]
                    for ri in range(self.n_patterns)
                    if self.od_incidence[ri, oi] > 0
                ) >= float(self.min_od_service))

        model.solve()
        if model.status != cp.COPT.OPTIMAL:
            raise RuntimeError(f"COPT start repair status is {model.status}")
        repaired = np.array([
            [int(round(float(n_vars[ri][ti].x))) for ti in range(self.n_periods)]
            for ri in range(self.n_patterns)
        ], dtype=np.int32)
        if not self.linear_feasible_batch(repaired[None], regime)[0]:
            raise RuntimeError("COPT returned a non-feasible start")
        return repaired

    def repair_start(self, target: np.ndarray, regime: str) -> np.ndarray:
        """Find the closest linearly feasible integer start via COPT or SciPy."""
        if cp is not None:
            try:
                self.linear_repair_backend = "copt"
                return self._repair_start_copt(target, regime)
            except Exception:
                # Preserve portability and robustness: the exact same MILP is
                # solved by SciPy if a local COPT license or API call fails.
                self.linear_repair_backend = "scipy_milp_fallback"
        self._validate_regime(regime)
        target = np.asarray(target, dtype=np.float64)
        n = self.n_patterns * self.n_periods
        total_vars = 3 * n
        i_n, i_dp, i_dm = 0, n, 2 * n
        c = np.zeros(total_vars)
        weights = 1.0 / np.maximum(1.0, self.freq_max.ravel())
        c[i_dp:i_dp+n] = weights
        c[i_dm:i_dm+n] = weights
        integrality = np.zeros(total_vars, dtype=int)
        integrality[:n] = 1
        lower = np.zeros(total_vars)
        upper = np.full(total_vars, np.inf)
        upper[:n] = self.freq_max.ravel()

        candidate_mask_flat = np.repeat(self.candidate_mask, self.n_periods)
        if regime == "incumbent_only":
            upper[:n][candidate_mask_flat] = 0.0

        rows: list[np.ndarray] = []
        lows: list[float] = []
        highs: list[float] = []

        def add(coeff: dict[int, float], lb: float = -np.inf, ub: float = np.inf) -> None:
            row = np.zeros(total_vars)
            for index, value in coeff.items():
                row[index] = value
            rows.append(row); lows.append(lb); highs.append(ub)

        for flat in range(n):
            add({flat: 1.0, i_dp + flat: -1.0, i_dm + flat: 1.0},
                lb=float(target.ravel()[flat]), ub=float(target.ravel()[flat]))

        def flat(ri: int, ti: int) -> int:
            return ri * self.n_periods + ti

        # Incumbent-pattern and product-level daily floors.
        for ri in np.flatnonzero(self.incumbent_mask):
            add(
                {flat(int(ri), ti): 1.0 for ti in range(self.n_periods)},
                lb=float(self.incumbent_pattern_floor),
            )
        for pi, floor in enumerate(self.daily_floor):
            if floor > 0:
                add({flat(ri, ti): 1.0
                     for ri in range(self.n_patterns) if self.pattern_product_idx[ri] == pi
                     for ti in range(self.n_periods)}, lb=float(floor))

        # A candidate is optional.  When the repair target activates it, retain
        # the configured minimum; otherwise the zero branch remains available.
        if regime == "incumbent_plus_candidate":
            for ri in np.flatnonzero(self.candidate_mask):
                if float(target[int(ri)].sum()) > 0:
                    add(
                        {flat(int(ri), ti): 1.0 for ti in range(self.n_periods)},
                        lb=float(self.candidate_active_floor[int(ri)]),
                    )

        for ti in range(self.n_periods):
            for ei in range(self.n_lines):
                add({flat(ri, ti): self.line_incidence[ri, ei]
                     for ri in range(self.n_patterns) if self.line_incidence[ri, ei] > 0},
                    ub=float(self.line_capacity[ti]))
        for pi in range(len(PRODUCTS)):
            add({flat(ri, ti): self.cycle_time[ri]
                 for ri in range(self.n_patterns) if self.pattern_product_idx[ri] == pi
                 for ti in range(self.n_periods)}, ub=float(self.fleet_available[pi]))
        for ti in range(self.n_periods):
            for oi in range(self.n_ods):
                add({flat(ri, ti): self.od_incidence[ri, oi]
                     for ri in range(self.n_patterns) if self.od_incidence[ri, oi] > 0},
                    lb=float(self.min_od_service))

        result = milp(
            c=c,
            integrality=integrality,
            bounds=Bounds(lower, upper),
            constraints=LinearConstraint(np.vstack(rows), np.array(lows), np.array(highs)),
            options={"time_limit": 10.0, "mip_rel_gap": 0.0, "presolve": True},
        )
        if result.x is None:
            raise RuntimeError(f"Cannot construct feasible start for {regime}: {result.message}")
        repaired = np.rint(result.x[:n]).astype(np.int32).reshape(self.n_patterns, self.n_periods)
        if not self.linear_feasible_batch(repaired[None], regime)[0]:
            raise RuntimeError(f"MILP returned a non-feasible start for {regime}")
        return repaired

    def assess(
        self,
        N: np.ndarray,
        phi: np.ndarray,
        metrics: dict[str, Any],
        *,
        regime: str,
        loss_tolerance: float,
        retention_floor: float,
        reference_vulnerable_trips: float,
        state_reference_metrics: dict[str, Any],
        objective: str,
    ) -> dict[str, Any]:
        violations = self.linear_violations(N, regime)
        mlf = float(metrics["max_load_factor"])
        if mlf > 1.0 + 1e-9:
            violations["seat_segment_capacity"] = mlf - 1.0
        fare_gap = 0.0
        for pi in range(len(PRODUCTS)):
            fare_gap = max(
                fare_gap,
                float(np.max(np.maximum(self.fare_lo - phi[pi], 0.0))),
                float(np.max(np.maximum(phi[pi] - self.fare_hi, 0.0))),
            )
        if fare_gap > 0:
            violations["fare_bounds"] = fare_gap

        profit = float(metrics["profit"])
        if profit < -loss_tolerance:
            scale = max(1.0, abs(float(state_reference_metrics["revenue"])))
            violations["financial_floor"] = (-loss_tolerance - profit) / scale
        vuln = float(metrics["vulnerable_trips"])
        retention = vuln / reference_vulnerable_trips if reference_vulnerable_trips > 0 else 1.0
        if retention < retention_floor:
            violations["vulnerable_retention"] = retention_floor - retention

        if objective == "profit":
            objective_value = profit
        elif objective == "welfare":
            objective_value = float(metrics["welfare_level"]) - float(state_reference_metrics["welfare_level"])
        else:
            raise ValueError(f"Unknown objective: {objective}")
        penalty = float(sum(value * value for value in violations.values()))
        return {
            "feasible": not violations,
            "violations": violations,
            "penalty": penalty,
            "objective_value": objective_value,
            "retention_rate": retention,
            "profit": profit,
            "revenue": float(metrics["revenue"]),
            "operating_cost": float(metrics["operating_cost"]),
            "consumer_benefit": float(metrics["consumer_benefit"]),
            "welfare_level": float(metrics["welfare_level"]),
            "total_trips": float(metrics["total_trips"]),
            "rail_pax": float(metrics["rail_pax"]),
            "vulnerable_trips": vuln,
            "max_load_factor": mlf,
        }
