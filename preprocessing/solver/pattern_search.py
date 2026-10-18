"""Fast deterministic search over service-pattern frequencies and product fares."""

from __future__ import annotations

import itertools
import time
from typing import Any

import numpy as np

from pattern_constraints import PRODUCTS, PatternConstraintSystem
from pattern_nlt import PatternNLTEngine


POLICY_SET_REGIME = {
    "fixed_reference": "incumbent_only",
    "fare_only_incumbent": "incumbent_only",
    "frequency_only_incumbent": "incumbent_only",
    "joint_incumbent": "incumbent_only",
    "joint_plus_candidate": "incumbent_plus_candidate",
}
POLICY_SETS = tuple(POLICY_SET_REGIME)
SOLVER_VERSION = "pattern_constrained_2026_08_12_copt_hybrid_v9"
MAX_EXACT_BLOCK_COMBINATIONS = 20_000


def fare_grid(step: float, lo: float, hi: float) -> np.ndarray:
    count = int(round((hi - lo) / step)) + 1
    return np.array([round(lo + i * step, 6) for i in range(count)], dtype=np.float64)


class PatternStructuredSearch:
    """Multi-start coordinate search with exact batch feasibility filtering."""

    def __init__(
        self,
        case: dict[str, Any],
        income_state: str,
        electrification_state: str,
        *,
        objective: str,
        regime: str | None = None,
        policy_set: str | None = None,
        loss_tolerance: float = 500000.0,
        retention_floor: float = 0.95,
        fare_step: float = 0.05,
        report_details: bool = True,
    ):
        if policy_set is not None:
            if policy_set not in POLICY_SET_REGIME:
                raise ValueError(
                    f"Unknown policy_set {policy_set!r}; expected one of {POLICY_SETS}"
                )
            expected_regime = POLICY_SET_REGIME[policy_set]
            if regime is not None and regime != expected_regime:
                raise ValueError(
                    f"policy_set={policy_set!r} requires regime={expected_regime!r}"
                )
            regime = expected_regime
        if regime is None:
            raise ValueError("Either regime or policy_set must be supplied")

        self.case = case
        self.objective = objective
        self.regime = regime
        self.policy_set = policy_set or f"legacy_{regime}"
        self.loss_tolerance = float(loss_tolerance)
        self.retention_floor = float(retention_floor)
        self.report_details = bool(report_details)
        self.constraints = PatternConstraintSystem(case)
        self.engine = PatternNLTEngine(case, income_state, electrification_state)
        self.patterns = self.constraints.patterns
        self.pattern_ids = self.constraints.pattern_ids
        self.periods = self.constraints.periods
        self.n_patterns = self.constraints.n_patterns
        self.n_periods = self.constraints.n_periods
        self.grid = fare_grid(
            fare_step, self.constraints.fare_lo, self.constraints.fare_hi
        )
        self.fare_step = float(fare_step)
        self._evaluations = 0

        ref = case["pattern_reference_design"]
        N_ref = self._design_N(ref)
        phi_ref = self._design_phi(ref)
        self._fixed_N = N_ref.copy()
        self._fixed_phi = phi_ref.copy()
        self._frequency_free = np.ones(
            (self.n_patterns, self.n_periods), dtype=bool
        )
        self._fare_free = np.ones((3, self.n_periods), dtype=bool)
        if self.regime == "incumbent_only":
            self._frequency_free[self.constraints.candidate_mask, :] = False
        if policy_set == "joint_plus_candidate" and not np.any(
            self.constraints.candidate_mask
        ):
            raise ValueError(
                "joint_plus_candidate is available only when the case declares "
                "at least one candidate_synthetic pattern"
            )
        if policy_set in {"fixed_reference", "fare_only_incumbent"}:
            self._frequency_free[:, :] = False
        if policy_set in {"fixed_reference", "frequency_only_incumbent"}:
            self._fare_free[:, :] = False
        self._state_reference = self.engine.evaluate_single(N_ref, phi_ref)
        income_states = tuple(case["scenarios"]["income"])
        electric_states = tuple(case["scenarios"]["electrification"])
        reference_spec = case.get("reference_scenario", {})
        reference_income = str(reference_spec.get("income_state", income_states[0]))
        reference_electric = str(
            reference_spec.get("electrification_state", electric_states[0])
        )
        if reference_income not in income_states:
            raise ValueError(f"Unknown reference income state: {reference_income!r}")
        if reference_electric not in electric_states:
            raise ValueError(
                f"Unknown reference electrification state: {reference_electric!r}"
            )
        reference_engine = PatternNLTEngine(
            case, reference_income, reference_electric
        )
        self._reference_vulnerable = float(
            reference_engine.evaluate_single(N_ref, phi_ref)["vulnerable_trips"]
        )

    def _design_N(self, design: dict[str, Any]) -> np.ndarray:
        return np.array(
            [[int(design["N"][pattern][period]) for period in self.periods]
             for pattern in self.pattern_ids], dtype=np.int32
        )

    def _design_phi(self, design: dict[str, Any]) -> np.ndarray:
        return np.array(
            [[float(design["phi"][product][period]) for period in self.periods]
             for product in PRODUCTS], dtype=np.float64
        )

    def _assess(self, N: np.ndarray, phi: np.ndarray, metrics: dict[str, Any]) -> dict[str, Any]:
        return self.constraints.assess(
            N, phi, metrics,
            regime=self.regime,
            loss_tolerance=self.loss_tolerance,
            retention_floor=self.retention_floor,
            reference_vulnerable_trips=self._reference_vulnerable,
            state_reference_metrics=self._state_reference,
            objective=self.objective,
        )

    @staticmethod
    def _score(assessed: dict[str, Any]) -> float:
        if assessed["feasible"]:
            return float(assessed["objective_value"])
        return -1e18 - float(assessed["penalty"])

    def _start_candidates(self) -> list[np.ndarray]:
        if not np.any(self._frequency_free):
            if not self.constraints.linear_feasible_batch(
                self._fixed_N[None], self.regime
            )[0]:
                raise RuntimeError(
                    f"Fixed reference frequencies are infeasible for {self.policy_set}"
                )
            return [self._fixed_N.copy()]

        candidates = [self.constraints.natural_start(self.regime)]

        # A low-frequency start exposes solutions that reduce use of existing
        # assets while respecting their daily service floors.
        low_target = np.zeros((self.n_patterns, self.n_periods), dtype=np.int32)
        candidates.append(self.constraints.repair_start(low_target, self.regime))

        # P4 needs active-candidate starts because a fixed activation cost can
        # create a barrier around the zero-frequency reference design.
        if self.regime == "incumbent_plus_candidate" and np.any(
            self.constraints.candidate_mask
        ):
            active_target = self.constraints.natural_start(self.regime)
            for ri in np.flatnonzero(self.constraints.candidate_mask):
                active_target[int(ri), 0] = max(
                    int(self.constraints.candidate_active_floor[int(ri)]), 1
                )
            candidates.append(self.constraints.repair_start(active_target, self.regime))

            high_target = self.constraints.natural_start(self.regime)
            high_target[self.constraints.candidate_mask] = self.constraints.freq_max[
                self.constraints.candidate_mask
            ]
            candidates.append(self.constraints.repair_start(high_target, self.regime))

        unique: list[np.ndarray] = []
        seen: set[bytes] = set()
        for candidate in candidates:
            key = candidate.tobytes()
            if key not in seen:
                seen.add(key); unique.append(candidate)
        return unique

    def solve(self, max_rounds: int = 4, verbose: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        self._evaluations = 0
        global_best: tuple[np.ndarray, np.ndarray, dict[str, Any], float] | None = None
        best_candidate_zero: tuple[
            np.ndarray, np.ndarray, dict[str, Any], float
        ] | None = None
        start_summaries = []
        k_mask = self.constraints.pattern_product_idx == PRODUCTS.index("K")
        candidate_mask = self.constraints.candidate_mask

        for start_index, N0 in enumerate(self._start_candidates(), start=1):
            phi0 = self._fixed_phi.copy()
            local = self._solve_from(N0, phi0, max_rounds, verbose)
            N, phi, assessed, score, rounds = local
            start_summaries.append({
                "start": start_index,
                "feasible": bool(assessed["feasible"]),
                "objective_value": float(assessed["objective_value"]),
                "k_daily_departures": int(N[k_mask].sum()),
                "candidate_daily_departures": int(N[candidate_mask].sum()),
                "rounds": rounds,
            })
            if global_best is None or score > global_best[3] + 1e-8:
                global_best = (N.copy(), phi.copy(), assessed, score)
            if (
                self.regime == "incumbent_plus_candidate"
                and int(N[candidate_mask].sum()) == 0
                and (
                    best_candidate_zero is None
                    or score > best_candidate_zero[3] + 1e-8
                )
            ):
                best_candidate_zero = (N.copy(), phi.copy(), assessed, score)

        assert global_best is not None
        N, phi, assessed, score = global_best
        pre_polish_score = score
        N, phi, assessed, score, block_polish = self._block_polish(
            N, phi, assessed, score,
            max_passes=8,
            verbose=verbose,
        )
        if (
            self.regime == "incumbent_plus_candidate"
            and int(N[candidate_mask].sum()) == 0
            and (
                best_candidate_zero is None
                or score > best_candidate_zero[3] + 1e-8
            )
        ):
            best_candidate_zero = (N.copy(), phi.copy(), assessed, score)
        # Independent final re-evaluation; no stale batch metric can enter output.
        detailed_metrics = None
        if self.report_details:
            detailed_metrics = self.engine.evaluate_detailed(N, phi)
            final_metrics = detailed_metrics["metrics"]
        else:
            final_metrics = self.engine.evaluate_single(N, phi)
        final_assessed = self._assess(N, phi, final_metrics)
        candidate_zero_design = None
        if best_candidate_zero is not None:
            zN, zphi, _, _ = best_candidate_zero
            zmetrics = self.engine.evaluate_single(zN, zphi)
            zassessed = self._assess(zN, zphi, zmetrics)
            candidate_zero_design = {
                "best_design": self._to_design(zN, zphi),
                "best_metrics": zassessed,
                "objective_value": float(zassessed["objective_value"]),
                "feasible": bool(zassessed["feasible"]),
            }
        elapsed = time.perf_counter() - started
        result = {
            "solver": "pattern_vectorized_multistart_structured_search",
            "solver_version": SOLVER_VERSION,
            "linear_repair_backend": self.constraints.linear_repair_backend,
            "regime": self.regime,
            "policy_set": self.policy_set,
            "objective": self.objective,
            "best_design": self._to_design(N, phi),
            "best_metrics": final_assessed,
            "objective_value": float(final_assessed["objective_value"]),
            "feasible": bool(final_assessed["feasible"]),
            "evaluations": int(self._evaluations),
            "elapsed_seconds": elapsed,
            "starts": start_summaries,
            "block_polish": {
                **block_polish,
                "objective_before": float(pre_polish_score),
                "objective_after": float(score),
                "objective_improvement": float(score - pre_polish_score),
            },
            "best_candidate_zero_design": candidate_zero_design,
            "k_service_decisions": self._k_service_decisions(N),
            "candidate_service_decisions": self._candidate_service_decisions(N),
            "k_od_frequency": self._k_od_frequency(N),
        }
        if self.report_details:
            constraint_report = self.constraints.constraint_report(
                N, phi, self.regime
            )
            constraint_report["nonlinear_constraints"] = {
                "seat_capacity": {
                    "max_load_factor": float(final_assessed["max_load_factor"]),
                    "slack": float(1.0 - final_assessed["max_load_factor"]),
                    "binding": bool(
                        abs(1.0 - final_assessed["max_load_factor"]) <= 1e-6
                    ),
                },
                "financial_floor": {
                    "profit": float(final_assessed["profit"]),
                    "minimum_profit": float(-self.loss_tolerance),
                    "slack": float(final_assessed["profit"] + self.loss_tolerance),
                    "binding": bool(
                        abs(final_assessed["profit"] + self.loss_tolerance) <= 1e-6
                    ),
                },
                "vulnerable_retention": {
                    "retention_rate": float(final_assessed["retention_rate"]),
                    "minimum": float(self.retention_floor),
                    "slack": float(
                        final_assessed["retention_rate"] - self.retention_floor
                    ),
                    "binding": bool(abs(
                        final_assessed["retention_rate"] - self.retention_floor
                    ) <= 1e-6),
                },
            }
            result["detailed_metrics"] = detailed_metrics
            result["constraint_report"] = constraint_report
            result["decision_masks"] = {
                "frequency_free": self._frequency_free.astype(int).tolist(),
                "fare_free": self._fare_free.astype(int).tolist(),
            }
        return result

    def certify_design(
        self,
        design: dict[str, Any],
        *,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Re-evaluate an externally discovered incumbent under this policy.

        This supports the nested-policy audit: a design found in a restricted
        policy remains a valid incumbent for any policy that frees additional
        fare, frequency, or candidate-pattern decisions.
        """
        started = time.perf_counter()
        N = self._design_N(design)
        phi = self._design_phi(design)
        if np.any(N[~self._frequency_free] != self._fixed_N[~self._frequency_free]):
            raise ValueError("Design violates fixed frequency decisions for target policy")
        if np.any(np.abs(
            phi[~self._fare_free] - self._fixed_phi[~self._fare_free]
        ) > 1e-9):
            raise ValueError("Design violates fixed fare decisions for target policy")

        initial_metrics = self.engine.evaluate_single(N, phi)
        self._evaluations += 1
        initial_assessed = self._assess(N, phi, initial_metrics)
        initial_score = self._score(initial_assessed)
        N, phi, _, polished_score, block_polish = self._block_polish(
            N, phi, initial_assessed, initial_score,
            max_passes=8, verbose=False,
        )
        detailed_metrics = self.engine.evaluate_detailed(N, phi)
        final_assessed = self._assess(N, phi, detailed_metrics["metrics"])
        constraint_report = self.constraints.constraint_report(N, phi, self.regime)
        constraint_report["nonlinear_constraints"] = {
            "seat_capacity": {
                "max_load_factor": float(final_assessed["max_load_factor"]),
                "slack": float(1.0 - final_assessed["max_load_factor"]),
                "binding": bool(abs(1.0 - final_assessed["max_load_factor"]) <= 1e-6),
            },
            "financial_floor": {
                "profit": float(final_assessed["profit"]),
                "minimum_profit": float(-self.loss_tolerance),
                "slack": float(final_assessed["profit"] + self.loss_tolerance),
                "binding": bool(abs(
                    final_assessed["profit"] + self.loss_tolerance
                ) <= 1e-6),
            },
            "vulnerable_retention": {
                "retention_rate": float(final_assessed["retention_rate"]),
                "minimum": float(self.retention_floor),
                "slack": float(
                    final_assessed["retention_rate"] - self.retention_floor
                ),
                "binding": bool(abs(
                    final_assessed["retention_rate"] - self.retention_floor
                ) <= 1e-6),
            },
        }
        return {
            "solver": "pattern_vectorized_nested_incumbent_certification",
            "solver_version": SOLVER_VERSION,
            "linear_repair_backend": self.constraints.linear_repair_backend,
            "regime": self.regime,
            "policy_set": self.policy_set,
            "objective": self.objective,
            "best_design": self._to_design(N, phi),
            "best_metrics": final_assessed,
            "objective_value": float(final_assessed["objective_value"]),
            "feasible": bool(final_assessed["feasible"]),
            "evaluations": int(self._evaluations),
            "elapsed_seconds": time.perf_counter() - started,
            "starts": [],
            "block_polish": {
                **block_polish,
                "method": "target_policy_exact_block_polish_after_external_certification",
                "objective_before": float(initial_score),
                "objective_after": float(polished_score),
                "objective_improvement": float(polished_score - initial_score),
            },
            "best_candidate_zero_design": None,
            "k_service_decisions": self._k_service_decisions(N),
            "candidate_service_decisions": self._candidate_service_decisions(N),
            "k_od_frequency": self._k_od_frequency(N),
            "detailed_metrics": detailed_metrics,
            "constraint_report": constraint_report,
            "decision_masks": {
                "frequency_free": self._frequency_free.astype(int).tolist(),
                "fare_free": self._fare_free.astype(int).tolist(),
            },
            "nested_feasible_set_audit": {
                "action": "certified_external_incumbent",
                "provenance": provenance or {},
            },
        }

    @staticmethod
    def _chunks(iterator: Any, size: int) -> Any:
        """Yield bounded lists without materialising a whole Cartesian product."""
        while True:
            chunk = list(itertools.islice(iterator, size))
            if not chunk:
                return
            yield chunk

    def _frequency_neighborhood(
        self, N: np.ndarray, ri: int, ti: int, radius: int = 1
    ) -> list[int]:
        current = int(N[ri, ti])
        upper = int(self.constraints.freq_max[ri, ti])
        return sorted({
            max(0, min(upper, current + delta))
            for delta in range(-radius, radius + 1)
        })

    def _fare_neighborhood(
        self, phi: np.ndarray, pi: int, ti: int
    ) -> list[float]:
        current = float(phi[pi, ti])
        nearest = int(np.argmin(np.abs(self.grid - current)))
        indices = {
            max(0, min(len(self.grid) - 1, nearest + delta))
            for delta in (-1, 0, 1)
        }
        return [float(self.grid[index]) for index in sorted(indices)]

    def _optimize_exact_block(
        self,
        N: np.ndarray,
        phi: np.ndarray,
        n_coords: list[tuple[int, int]],
        phi_coords: list[tuple[int, int]],
        score: float,
        *,
        chunk_size: int = 512,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float] | None:
        """Exhaust a radius-one mixed frequency/fare neighborhood in chunks."""
        value_lists: list[list[int] | list[float]] = [
            self._frequency_neighborhood(N, ri, ti) for ri, ti in n_coords
        ]
        value_lists.extend(
            self._fare_neighborhood(phi, pi, ti) for pi, ti in phi_coords
        )
        if not value_lists:
            return None

        best = None
        best_score = score
        combinations = itertools.product(*value_lists)
        for combo_chunk in self._chunks(combinations, chunk_size):
            count = len(combo_chunk)
            N_batch = np.broadcast_to(N[None], (count, *N.shape)).copy()
            phi_batch = np.broadcast_to(phi[None], (count, *phi.shape)).copy()
            for bi, values in enumerate(combo_chunk):
                cursor = 0
                for ri, ti in n_coords:
                    N_batch[bi, ri, ti] = int(values[cursor])
                    cursor += 1
                for pi, ti in phi_coords:
                    phi_batch[bi, pi, ti] = float(values[cursor])
                    cursor += 1
            candidate = self._choose_best(N_batch, phi_batch, best_score)
            if candidate is not None:
                best = candidate
                best_score = candidate[3]
        return best

    def _exact_block_combinations(
        self,
        N: np.ndarray,
        phi: np.ndarray,
        n_coords: list[tuple[int, int]],
        phi_coords: list[tuple[int, int]],
    ) -> int:
        """Return the Cartesian size without materialising the neighborhood."""
        size = 1
        for ri, ti in n_coords:
            size *= len(self._frequency_neighborhood(N, ri, ti))
        for pi, ti in phi_coords:
            size *= len(self._fare_neighborhood(phi, pi, ti))
        return size

    def _bounded_product_period_blocks(
        self,
        N: np.ndarray,
        phi: np.ndarray,
        n_coords: list[tuple[int, int]],
        phi_coords: list[tuple[int, int]],
    ) -> list[tuple[list[tuple[int, int]], list[tuple[int, int]]]]:
        """Partition a product-period block into bounded exact subblocks."""
        blocks: list[tuple[list[tuple[int, int]], list[tuple[int, int]]]] = []
        current: list[tuple[int, int]] = []
        for coord in n_coords:
            candidate = [*current, coord]
            if current and self._exact_block_combinations(
                N, phi, candidate, phi_coords
            ) > MAX_EXACT_BLOCK_COMBINATIONS:
                blocks.append((current, phi_coords))
                current = [coord]
            else:
                current = candidate
        if current or phi_coords:
            blocks.append((current, phi_coords))
        return blocks

    def _block_polish(
        self,
        N: np.ndarray,
        phi: np.ndarray,
        assessed: dict[str, Any],
        score: float,
        *,
        max_passes: int,
        verbose: bool,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float, dict[str, Any]]:
        """Polish the best multi-start solution over publication-relevant blocks."""
        accepted_moves = 0
        pass_summaries: list[dict[str, Any]] = []

        for pass_index in range(max_passes):
            pass_before = score
            period_moves = 0
            pattern_moves = 0
            full_period_blocks = 0
            product_period_blocks = 0

            # A period block captures simultaneous substitution among services
            # and fares faced by travellers in the same time-of-day market.
            # On a corridor with many optional K patterns, the full Cartesian
            # block can contain tens of millions of points.  In that case use
            # bounded exact product-by-period subblocks; cross-block and
            # cross-product substitutions are still covered by repeated scans
            # and the strategic pair pass in ``_solve_from``.
            for ti in range(self.n_periods):
                n_coords = [
                    (ri, ti) for ri in range(self.n_patterns)
                    if self._frequency_free[ri, ti]
                ]
                phi_coords = [
                    (pi, ti) for pi in range(3) if self._fare_free[pi, ti]
                ]
                if self._exact_block_combinations(
                    N, phi, n_coords, phi_coords
                ) <= MAX_EXACT_BLOCK_COMBINATIONS:
                    block_specs = [(n_coords, phi_coords)]
                    full_period_blocks += 1
                else:
                    block_specs = []
                    for pi in range(3):
                        product_n = [
                            coord for coord in n_coords
                            if int(self.constraints.pattern_product_idx[coord[0]]) == pi
                        ]
                        product_phi = [coord for coord in phi_coords if coord[0] == pi]
                        if product_n or product_phi:
                            bounded = self._bounded_product_period_blocks(
                                N, phi, product_n, product_phi
                            )
                            block_specs.extend(bounded)
                            product_period_blocks += len(bounded)
                for block_n, block_phi in block_specs:
                    result = self._optimize_exact_block(
                        N, phi, block_n, block_phi, score
                    )
                    if result is not None:
                        N, phi, assessed, score = result
                        period_moves += 1
                        accepted_moves += 1

            # A pattern block captures fleet/frequency reallocation over the
            # day together with the product's period-specific price response.
            for ri in range(self.n_patterns):
                n_coords = [
                    (ri, ti) for ti in range(self.n_periods)
                    if self._frequency_free[ri, ti]
                ]
                pi = int(self.constraints.pattern_product_idx[ri])
                phi_coords = [
                    (pi, ti) for ti in range(self.n_periods)
                    if self._fare_free[pi, ti]
                ]
                result = self._optimize_exact_block(
                    N, phi, n_coords, phi_coords, score
                )
                if result is not None:
                    N, phi, assessed, score = result
                    pattern_moves += 1
                    accepted_moves += 1

            pass_improvement = float(score - pass_before)
            pass_summaries.append({
                "pass": pass_index + 1,
                "period_moves": period_moves,
                "pattern_moves": pattern_moves,
                "full_period_blocks": full_period_blocks,
                "product_period_blocks": product_period_blocks,
                "objective_improvement": pass_improvement,
            })
            if verbose:
                print(
                    f"  block polish {pass_index + 1}: "
                    f"improvement={pass_improvement:.6f} eval={self._evaluations}",
                    flush=True,
                )
            if pass_improvement <= 1e-8:
                break

        return N, phi, assessed, score, {
            "method": "adaptive_bounded_exact_radius_one_period_product_and_pattern_blocks",
            "max_exact_block_combinations": MAX_EXACT_BLOCK_COMBINATIONS,
            "passes": len(pass_summaries),
            "accepted_moves": accepted_moves,
            "pass_summaries": pass_summaries,
        }

    def _solve_from(
        self, N: np.ndarray, phi: np.ndarray, max_rounds: int, verbose: bool
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float, int]:
        N = N.copy(); phi = phi.copy()
        metrics = self.engine.evaluate_single(N, phi)
        self._evaluations += 1
        assessed = self._assess(N, phi, metrics)
        score = self._score(assessed)
        rounds = 0

        for round_index in range(max_rounds):
            improved = False
            # Frequency coordinates.
            for ri in range(self.n_patterns):
                for ti in range(self.n_periods):
                    if not self._frequency_free[ri, ti]:
                        continue
                    result = self._optimize_frequency(N, phi, ri, ti, score)
                    if result is not None:
                        N, phi, assessed, score = result; improved = True

            # Product-period fare coordinates.  Skip products with no service.
            for pi in range(3):
                product_mask = self.constraints.pattern_product_idx == pi
                if int(N[product_mask].sum()) <= 0:
                    continue
                for ti in range(self.n_periods):
                    if not self._fare_free[pi, ti]:
                        continue
                    result = self._optimize_fare(N, phi, pi, ti, score)
                    if result is not None:
                        N, phi, assessed, score = result; improved = True
            rounds = round_index + 1
            if verbose:
                print(
                    f"  start round {rounds}: obj={assessed['objective_value']:.2f} "
                    f"feasible={assessed['feasible']} eval={self._evaluations}",
                    flush=True,
                )
            if not improved:
                break

        # One strategic pair pass: same pattern across periods or different
        # patterns in the same period.  This allows frequency transfers needed
        # by fleet/path constraints and K reactivation.
        blocks = [
            (ri, ti) for ri in range(self.n_patterns)
            for ti in range(self.n_periods) if self._frequency_free[ri, ti]
        ]
        for left_i, left in enumerate(blocks):
            for right in blocks[left_i + 1:]:
                if left[0] != right[0] and left[1] != right[1]:
                    continue
                result = self._optimize_frequency_pair(N, phi, left, right, score)
                if result is not None:
                    N, phi, assessed, score = result
        return N, phi, assessed, score, rounds

    def _choose_best(
        self,
        N_batch: np.ndarray,
        phi_batch: np.ndarray,
        current_score: float,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float] | None:
        linear = self.constraints.linear_feasible_batch(N_batch, self.regime)
        if not np.any(linear):
            return None
        N_valid = N_batch[linear]
        phi_valid = phi_batch[linear]
        metrics_batch = self.engine.evaluate_batch(N_valid, phi_valid)
        self._evaluations += len(N_valid)

        # Vectorized equivalent of PatternConstraintSystem.assess.  The prior
        # implementation called the scalar assessor for every candidate, which
        # dominated runtime once exact mixed blocks were introduced.
        max_load = np.asarray(metrics_batch["max_load_factor"], dtype=np.float64)
        profit = np.asarray(metrics_batch["profit"], dtype=np.float64)
        retention = (
            np.asarray(metrics_batch["vulnerable_trips"], dtype=np.float64)
            / max(self._reference_vulnerable, 1e-12)
        )
        fare_gap = np.maximum(
            np.max(np.maximum(self.constraints.fare_lo - phi_valid, 0.0), axis=(1, 2)),
            np.max(np.maximum(phi_valid - self.constraints.fare_hi, 0.0), axis=(1, 2)),
        )
        seat_gap = np.maximum(max_load - 1.0, 0.0)
        revenue_scale = max(
            1.0, abs(float(self._state_reference["revenue"]))
        )
        financial_gap = np.maximum(
            (-self.loss_tolerance - profit) / revenue_scale, 0.0
        )
        retention_gap = np.maximum(self.retention_floor - retention, 0.0)
        feasible = (
            (max_load <= 1.0 + 1e-9)
            & (profit >= -self.loss_tolerance)
            & (retention >= self.retention_floor)
            & (fare_gap <= 0.0)
        )
        if self.objective == "profit":
            objective = profit
        else:
            objective = (
                np.asarray(metrics_batch["welfare_level"], dtype=np.float64)
                - float(self._state_reference["welfare_level"])
            )
        penalty = (
            seat_gap * seat_gap
            + financial_gap * financial_gap
            + retention_gap * retention_gap
            + fare_gap * fare_gap
        )
        scores = np.where(feasible, objective, -1e18 - penalty)
        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
        if best_score <= current_score + 1e-8:
            return None
        metrics = {key: value[best_index] for key, value in metrics_batch.items()}
        assessed = self._assess(N_valid[best_index], phi_valid[best_index], metrics)
        return (
            N_valid[best_index].copy(), phi_valid[best_index].copy(),
            assessed, best_score,
        )

    def _optimize_frequency(
        self, N: np.ndarray, phi: np.ndarray, ri: int, ti: int, score: float
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float] | None:
        values = np.arange(0, int(self.constraints.freq_max[ri, ti]) + 1, dtype=np.int32)
        N_batch = np.broadcast_to(N[None], (len(values), *N.shape)).copy()
        N_batch[:, ri, ti] = values
        phi_batch = np.broadcast_to(phi[None], (len(values), *phi.shape)).copy()
        return self._choose_best(N_batch, phi_batch, score)

    def _optimize_fare(
        self, N: np.ndarray, phi: np.ndarray, pi: int, ti: int, score: float
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float] | None:
        N_batch = np.broadcast_to(N[None], (len(self.grid), *N.shape)).copy()
        phi_batch = np.broadcast_to(phi[None], (len(self.grid), *phi.shape)).copy()
        phi_batch[:, pi, ti] = self.grid
        return self._choose_best(N_batch, phi_batch, score)

    def _optimize_frequency_pair(
        self,
        N: np.ndarray,
        phi: np.ndarray,
        left: tuple[int, int],
        right: tuple[int, int],
        score: float,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float] | None:
        lri, lti = left; rri, rti = right
        left_values = sorted({
            max(0, min(int(self.constraints.freq_max[lri, lti]), int(N[lri, lti]) + delta))
            for delta in (-2, -1, 0, 1, 2)
        })
        right_values = sorted({
            max(0, min(int(self.constraints.freq_max[rri, rti]), int(N[rri, rti]) + delta))
            for delta in (-2, -1, 0, 1, 2)
        })
        pairs = [(lv, rv) for lv in left_values for rv in right_values]
        N_batch = np.broadcast_to(N[None], (len(pairs), *N.shape)).copy()
        for i, (lv, rv) in enumerate(pairs):
            N_batch[i, lri, lti] = lv; N_batch[i, rri, rti] = rv
        phi_batch = np.broadcast_to(phi[None], (len(pairs), *phi.shape)).copy()
        return self._choose_best(N_batch, phi_batch, score)

    def _to_design(self, N: np.ndarray, phi: np.ndarray) -> dict[str, Any]:
        return {
            "periods": self.periods,
            "N": {
                pattern_id: {
                    period: int(N[ri, ti]) for ti, period in enumerate(self.periods)
                }
                for ri, pattern_id in enumerate(self.pattern_ids)
            },
            "phi": {
                product: {
                    period: round(float(phi[pi, ti]), 6)
                    for ti, period in enumerate(self.periods)
                }
                for pi, product in enumerate(PRODUCTS)
            },
        }

    def _k_service_decisions(self, N: np.ndarray) -> list[dict[str, Any]]:
        decisions = []
        for ri, pattern in enumerate(self.patterns):
            if pattern["product"] != "K":
                continue
            actual = int(N[ri].sum())
            observed = int(sum(pattern["observed_frequency"].values()))
            status = str(pattern.get("status", "incumbent_observed"))
            if status == "candidate_synthetic":
                action = "activated" if actual > 0 else "inactive"
            elif actual == 0:
                action = "unexpectedly_closed"
            else:
                action = (
                    "reduced" if actual < observed
                    else ("retained" if actual == observed else "expanded")
                )
            decisions.append({
                "pattern_id": pattern["id"],
                "served_ods": pattern["served_ods"],
                "status": status,
                "action": action,
                "optimized_daily_departures": actual,
                "observed_daily_departures": observed,
                "by_period": {
                    period: int(N[ri, ti]) for ti, period in enumerate(self.periods)
                },
            })
        return decisions

    def _candidate_service_decisions(self, N: np.ndarray) -> list[dict[str, Any]]:
        return [
            item for item in self._k_service_decisions(N)
            if item["status"] == "candidate_synthetic"
        ]

    def _k_od_frequency(self, N: np.ndarray) -> dict[str, dict[str, int]]:
        result = {od: {period: 0 for period in self.periods} for od in self.constraints.ods}
        for ri, pattern in enumerate(self.patterns):
            if pattern["product"] != "K":
                continue
            for od in pattern["served_ods"]:
                for ti, period in enumerate(self.periods):
                    result[od][period] += int(N[ri, ti])
        return result


def enforce_candidate_dominance(
    case: dict[str, Any],
    income_state: str,
    electrification_state: str,
    objective: str,
    base_result: dict[str, Any],
    extension_result: dict[str, Any],
    *,
    loss_tolerance: float,
    retention_floor: float,
    fare_step: float = 0.05,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Close the nested P3/P4 comparison over an optional synthetic pattern."""
    promotions: list[dict[str, Any]] = []

    def target_solver(template: dict[str, Any]) -> PatternStructuredSearch:
        policy = template.get("policy_set")
        kwargs: dict[str, Any]
        if policy in POLICY_SET_REGIME:
            kwargs = {"policy_set": policy}
        else:
            kwargs = {"regime": template["regime"]}
        return PatternStructuredSearch(
            case, income_state, electrification_state,
            objective=objective,
            loss_tolerance=loss_tolerance,
            retention_floor=retention_floor,
            fare_step=fare_step,
            report_details=True,
            **kwargs,
        )

    def promote(
        source: dict[str, Any], target: dict[str, Any], direction: str
    ) -> dict[str, Any]:
        solver = target_solver(target)
        provenance = {
            "direction": direction,
            "source_regime": source.get("regime"),
            "source_policy_set": source.get("policy_set"),
            "source_objective_value": float(source["objective_value"]),
            "source_evaluations": int(source.get("evaluations", 0)),
            "source_elapsed_seconds": float(source.get("elapsed_seconds", 0.0)),
        }
        certified = solver.certify_design(
            source["best_design"], provenance=provenance
        )
        if not certified["feasible"]:
            raise RuntimeError(
                f"Nested incumbent promotion unexpectedly infeasible: {direction}"
            )
        for key in (
            "case_id", "case_label", "corridor", "income_state", "electrification_state",
            "retention_floor", "loss_tolerance",
            "search_max_rounds", "case_fingerprint",
        ):
            if key in target:
                certified[key] = target[key]
            elif key in source:
                certified[key] = source[key]
        certified["evaluations"] = int(source.get("evaluations", 0)) + 1
        certified["elapsed_seconds"] += float(source.get("elapsed_seconds", 0.0))
        promotions.append(provenance)
        return certified

    def candidate_departures(result: dict[str, Any]) -> int:
        return sum(
            int(item["optimized_daily_departures"])
            for item in result.get("candidate_service_decisions", [])
        )

    # P4 contains P3.  A P4 solution with its candidate inactive also belongs
    # to P3, so exchange and certify incumbents until neither side improves.
    for _ in range(4):
        changed = False
        base_feasible = bool(base_result.get("feasible", False))
        extension_feasible = bool(extension_result.get("feasible", False))
        base_value = float(base_result.get("objective_value", -np.inf))
        extension_value = float(extension_result.get("objective_value", -np.inf))
        tolerance = 1e-7 * max(1.0, abs(base_value), abs(extension_value))

        if base_feasible and (
            not extension_feasible or extension_value < base_value - tolerance
        ):
            extension_result = promote(
                base_result, extension_result, "joint_incumbent_to_joint_plus_candidate"
            )
            changed = True

        base_feasible = bool(base_result.get("feasible", False))
        base_value = float(base_result.get("objective_value", -np.inf))
        extension_value = float(extension_result.get("objective_value", -np.inf))
        tolerance = 1e-7 * max(1.0, abs(base_value), abs(extension_value))
        extension_candidate = candidate_departures(extension_result)
        if (
            bool(extension_result.get("feasible", False))
            and extension_candidate == 0
            and (not base_feasible or extension_value > base_value + tolerance)
        ):
            base_result = promote(
                extension_result, base_result,
                "joint_plus_candidate_inactive_to_joint_incumbent",
            )
            changed = True
        if not changed:
            break

    base_value = float(base_result.get("objective_value", -np.inf))
    extension_value = float(extension_result.get("objective_value", -np.inf))
    tolerance = 1e-7 * max(1.0, abs(base_value), abs(extension_value))
    extension_candidate = candidate_departures(extension_result)
    audit = {
        "method": "nested_p3_p4_candidate_incumbent_promotion",
        "passed": bool(
            base_result.get("feasible", False)
            and extension_result.get("feasible", False)
            and extension_value + tolerance >= base_value
            and (
                extension_candidate > 0
                or abs(extension_value - base_value) <= tolerance
            )
        ),
        "tolerance": tolerance,
        "joint_incumbent_objective": base_value,
        "joint_plus_candidate_objective": extension_value,
        "candidate_daily_departures": extension_candidate,
        "promotions": promotions,
    }
    base_result["nested_feasible_set_audit"] = audit
    extension_result["nested_feasible_set_audit"] = audit
    return base_result, extension_result


def enforce_policy_chain_dominance(
    case: dict[str, Any],
    income_state: str,
    electrification_state: str,
    objective: str,
    policy_results: dict[str, dict[str, Any]],
    *,
    loss_tolerance: float,
    retention_floor: float,
    fare_step: float = 0.05,
) -> dict[str, dict[str, Any]]:
    """Close incumbents over P0 -> {P1,P2} -> P3 feasible-set edges."""
    promotions: list[dict[str, Any]] = []

    def promote(source: dict[str, Any], target: dict[str, Any], direction: str) -> dict[str, Any]:
        solver = PatternStructuredSearch(
            case, income_state, electrification_state,
            objective=objective, policy_set=str(target["policy_set"]),
            loss_tolerance=loss_tolerance,
            retention_floor=retention_floor,
            fare_step=fare_step,
            report_details=True,
        )
        provenance = {
            "direction": direction,
            "source_policy_set": source.get("policy_set"),
            "source_objective_value": float(source["objective_value"]),
            "source_evaluations": int(source.get("evaluations", 0)),
            "source_elapsed_seconds": float(source.get("elapsed_seconds", 0.0)),
        }
        certified = solver.certify_design(source["best_design"], provenance=provenance)
        if not certified["feasible"]:
            raise RuntimeError(f"Policy-chain incumbent unexpectedly infeasible: {direction}")
        for key in (
            "case_id", "case_label", "corridor", "income_state", "electrification_state",
            "retention_floor", "loss_tolerance", "search_max_rounds", "case_fingerprint",
        ):
            if key in target:
                certified[key] = target[key]
            elif key in source:
                certified[key] = source[key]
        certified["evaluations"] += int(source.get("evaluations", 0))
        certified["elapsed_seconds"] += float(source.get("elapsed_seconds", 0.0))
        promotions.append(provenance)
        return certified

    edges = (
        ("fixed_reference", "fare_only_incumbent"),
        ("fixed_reference", "frequency_only_incumbent"),
        ("fare_only_incumbent", "joint_incumbent"),
        ("frequency_only_incumbent", "joint_incumbent"),
    )
    for source_policy, target_policy in edges:
        if source_policy not in policy_results or target_policy not in policy_results:
            continue
        source = policy_results[source_policy]
        target = policy_results[target_policy]
        source_feasible = bool(source.get("feasible", False))
        target_feasible = bool(target.get("feasible", False))
        source_value = float(source.get("objective_value", -np.inf))
        target_value = float(target.get("objective_value", -np.inf))
        tolerance = 1e-7 * max(1.0, abs(source_value), abs(target_value))
        if source_feasible and (
            not target_feasible or target_value < source_value - tolerance
        ):
            policy_results[target_policy] = promote(
                source, target, f"{source_policy}_to_{target_policy}"
            )

    comparisons = []
    for source_policy, target_policy in edges:
        if source_policy not in policy_results or target_policy not in policy_results:
            continue
        source = policy_results[source_policy]
        target = policy_results[target_policy]
        source_feasible = bool(source.get("feasible", False))
        target_feasible = bool(target.get("feasible", False))
        source_value = float(source.get("objective_value", -np.inf))
        target_value = float(target.get("objective_value", -np.inf))
        tolerance = 1e-7 * max(1.0, abs(source_value), abs(target_value))
        passed = bool(
            not source_feasible
            or (target_feasible and target_value + tolerance >= source_value)
        )
        comparisons.append({
            "source_policy": source_policy,
            "target_policy": target_policy,
            "source_feasible": source_feasible,
            "target_feasible": target_feasible,
            "source_objective_value": source_value,
            "target_objective_value": target_value,
            "tolerance": tolerance,
            "passed": passed,
        })
    audit = {
        "method": "nested_policy_feasible_set_incumbent_promotion",
        "passed": all(item["passed"] for item in comparisons),
        "comparisons": comparisons,
        "promotions": promotions,
    }
    for result in policy_results.values():
        result["policy_chain_audit"] = audit
    return policy_results
