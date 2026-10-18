"""Core demand, accounting, feasibility, and search logic for the aligned case."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Iterable


PRODUCTS = ("G", "D", "K")
MODES = ("rail", "road", "auto")


def load_case(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def product_type(train_code: str) -> str:
    code = (train_code or "").upper()
    if code.startswith("G"):
        return "G"
    if code.startswith(("D", "C")):
        return "D"
    return "K"


def period_of(time_text: str, periods: dict[str, dict[str, float]]) -> str:
    try:
        hour = int(time_text.split(":")[0])
    except (ValueError, IndexError, AttributeError):
        hour = 12
    for name, spec in periods.items():
        start, end = int(spec["start"]), int(spec["end"])
        if start < end and start <= hour < end:
            return name
        if start > end and (hour >= start or hour < end):
            return name
    return next(iter(periods))


def design_key(design: dict[str, Any]) -> tuple[Any, ...]:
    values: list[Any] = []
    for product in PRODUCTS:
        for period in design["periods"]:
            values.append(int(design["N"][product][period]))
            values.append(round(float(design["phi"][product][period]), 6))
    return tuple(values)


def copy_design(design: dict[str, Any]) -> dict[str, Any]:
    return {
        "periods": list(design["periods"]),
        "N": {s: dict(v) for s, v in design["N"].items()},
        "phi": {s: dict(v) for s, v in design["phi"].items()},
    }


def reference_design(case: dict[str, Any]) -> dict[str, Any]:
    return copy_design(case["reference_design"])


def _logsumexp_scaled(values: Iterable[float], scale: float) -> float:
    vals = list(values)
    if not vals:
        return -math.inf
    maximum = max(vals)
    return maximum + scale * math.log(
        sum(math.exp((value - maximum) / scale) for value in vals)
    )


def _softmax_scaled(values: list[float], scale: float) -> list[float]:
    maximum = max(values)
    weights = [math.exp((value - maximum) / scale) for value in values]
    total = sum(weights)
    return [weight / total for weight in weights]


def _income_beta(
    case: dict[str, Any], traveler_class: str, income_state: str
) -> dict[str, float]:
    base = dict(case["utility"]["by_class"][traveler_class])
    shock = case["scenarios"]["income"][income_state][traveler_class]
    delta_y = math.log1p(shock)
    rho = case["utility"]["rho"][traveler_class]
    base["beta_c"] = base["beta_c"] * math.exp(-rho * delta_y)
    base["vot_yuan_hr"] = 60.0 * base["beta_iv"] / base["beta_c"]
    return base


def _rail_access(case: dict[str, Any], od: str) -> tuple[float, float]:
    origin, destination = od.split("-")
    access = case["attributes"]["access_by_city"]
    cost = access[origin]["fare"] + access[destination]["fare"]
    minutes = access[origin]["time_min"] + access[destination]["time_min"]
    return cost, minutes


def build_alternatives(
    case: dict[str, Any],
    segment: dict[str, Any],
    design: dict[str, Any],
    electrification_state: str,
) -> list[dict[str, Any]]:
    od = segment["od"]
    period = segment["period"]
    duration_h = case["sets"]["periods"][period]["duration_h"]
    attrs = case["attributes"]
    alternatives: list[dict[str, Any]] = []
    access_cost, access_min = _rail_access(case, od)

    for product in PRODUCTS:
        departures = int(design["N"][product][period])
        if departures <= 0:
            continue
        product_fares = attrs["rail_fare"].get(od, {}).get(product, {})
        runtime = attrs["rail_runtime_min"].get(od, {}).get(product)
        if runtime is None or not product_fares:
            continue
        frequency_h = departures / duration_h
        schedule_delay = case["schedule"]["vartheta_min"] / frequency_h
        for seat, reference_fare in product_fares.items():
            if seat not in case["products"][product]["seat_capacity"]:
                continue
            rail_fare = reference_fare * design["phi"][product][period]
            alternatives.append(
                {
                    "id": f"rail_{product}_{seat}",
                    "mode": "rail",
                    "product": product,
                    "seat": seat,
                    "cost": rail_fare + access_cost,
                    "rail_fare": rail_fare,
                    "iv_time": runtime,
                    "ac_time": access_min,
                    "wait_time": case["schedule"]["terminal_wait_min"],
                    "schedule_delay": schedule_delay,
                    "reliability": (
                        case["products"][product]["reliability_fraction"] * runtime
                    ),
                    "transfers": 0.0,
                    "comfort": case["products"][product]["seat_comfort"][seat],
                    "flexibility": case["products"][product]["flexibility"],
                    "asc": (
                        case["utility"]["asc_product"][product]
                        + case["utility"]["asc_seat"][product][seat]
                    ),
                }
            )

    road = attrs["road_by_od"][od]
    electric = case["scenarios"]["electrification"][electrification_state]
    distance = road["distance_km"]
    pass_through = electric["pass_through"]
    auto_saving = (
        case["electrification_savings"]["private_auto_per_km"]
        * distance
        * electric["auto_intensity"]
    )
    alternatives.append(
        {
            "id": "auto_private",
            "mode": "auto",
            "product": "private_auto",
            "seat": "standard",
            "cost": max(1.0, road["private_auto_cost"] - auto_saving),
            "rail_fare": 0.0,
            "iv_time": road["auto_duration_min"],
            "ac_time": 0.0,
            "wait_time": 0.0,
            "schedule_delay": 0.0,
            "reliability": 0.05 * road["auto_duration_min"],
            "transfers": 0.0,
            "comfort": 3.0,
            "flexibility": 5.0,
            "asc": case["utility"]["asc_alternative"]["private_auto"],
        }
    )

    road_specs = {
        "coach": {
            "base_cost": road["coach_fare"],
            "saving_key": "coach_per_km",
            "time": road["coach_duration_min"],
            "access": 18.0,
            "wait": 30.0,
            "comfort": 2.0,
            "flexibility": 1.0,
            "reliability": 0.08,
        },
        "maas": {
            "base_cost": road["maas_fare"],
            "saving_key": "maas_per_km",
            "time": road["auto_duration_min"] * 1.10,
            "access": 10.0,
            "wait": 15.0,
            "comfort": 3.0,
            "flexibility": 3.0,
            "reliability": 0.06,
        },
        "business_van": {
            "base_cost": road["business_van_fare"],
            "saving_key": "business_van_per_km",
            "time": road["auto_duration_min"] * 1.02,
            "access": 5.0,
            "wait": 5.0,
            "comfort": 4.0,
            "flexibility": 4.0,
            "reliability": 0.04,
        },
    }
    affected = set(electric["road_services"])
    for name, spec in road_specs.items():
        saving = 0.0
        if name in affected:
            saving = (
                case["electrification_savings"][spec["saving_key"]]
                * distance
                * pass_through
            )
        alternatives.append(
            {
                "id": f"road_{name}",
                "mode": "road",
                "product": name,
                "seat": "standard",
                "cost": max(1.0, spec["base_cost"] - saving),
                "rail_fare": 0.0,
                "iv_time": spec["time"],
                "ac_time": spec["access"],
                "wait_time": spec["wait"],
                "schedule_delay": 0.0,
                "reliability": spec["reliability"] * spec["time"],
                "transfers": 0.0,
                "comfort": spec["comfort"],
                "flexibility": spec["flexibility"],
                "asc": case["utility"]["asc_alternative"][name],
            }
        )
    return alternatives


def deterministic_utility(alt: dict[str, Any], beta: dict[str, float]) -> float:
    return (
        alt["asc"]
        - beta["beta_c"] * alt["cost"]
        - beta["beta_iv"] * alt["iv_time"]
        - beta["beta_ac"] * alt["ac_time"]
        - beta["beta_wt"] * alt["wait_time"]
        - beta["beta_sc"] * alt["schedule_delay"]
        - beta["beta_rel"] * alt["reliability"]
        - beta["beta_tr"] * alt["transfers"]
        + beta["gamma_com"] * alt["comfort"]
        + beta["gamma_flex"] * alt["flexibility"]
    )


def generalized_cost(alt: dict[str, Any], beta: dict[str, float]) -> float:
    money_scale = beta["beta_c"]
    return (
        alt["cost"]
        + beta["beta_iv"] / money_scale * alt["iv_time"]
        + beta["beta_ac"] / money_scale * alt["ac_time"]
        + beta["beta_wt"] / money_scale * alt["wait_time"]
        + beta["beta_sc"] / money_scale * alt["schedule_delay"]
        + beta["beta_rel"] / money_scale * alt["reliability"]
        + beta["beta_tr"] / money_scale * alt["transfers"]
    )


def segment_probabilities(
    case: dict[str, Any],
    segment: dict[str, Any],
    design: dict[str, Any],
    income_state: str,
    electrification_state: str,
) -> dict[str, Any]:
    traveler_class = segment["class"]
    beta = _income_beta(case, traveler_class, income_state)
    alternatives = build_alternatives(
        case, segment, design, electrification_state
    )
    mu = case["utility"]["mu"]
    by_mode: dict[str, list[int]] = {}
    utilities = [deterministic_utility(alt, beta) for alt in alternatives]
    for index, alt in enumerate(alternatives):
        by_mode.setdefault(alt["mode"], []).append(index)

    nest_iv: dict[str, float] = {}
    conditional: dict[int, float] = {}
    for mode, indices in by_mode.items():
        scale = mu[mode]
        vals = [utilities[index] for index in indices]
        nest_iv[mode] = _logsumexp_scaled(vals, scale)
        probs = _softmax_scaled(vals, scale)
        conditional.update({index: prob for index, prob in zip(indices, probs)})

    mode_names = list(nest_iv)
    mode_values = [
        case["utility"]["asc_mode"][traveler_class][mode] + nest_iv[mode]
        for mode in mode_names
    ]
    travel_iv = _logsumexp_scaled(mode_values, mu["mode_level"])
    mode_probs_list = _softmax_scaled(mode_values, mu["mode_level"])
    mode_probs = dict(zip(mode_names, mode_probs_list))
    travel_value = (
        case["utility"]["alpha_travel"][traveler_class] + travel_iv
    )
    no_travel_value = 0.0
    top_probs = _softmax_scaled(
        [travel_value, no_travel_value], mu["top"]
    )
    participation = top_probs[0]
    logsum = _logsumexp_scaled(
        [travel_value, no_travel_value], mu["top"]
    )
    alt_probs = [
        participation * mode_probs[alt["mode"]] * conditional[index]
        for index, alt in enumerate(alternatives)
    ]
    return {
        "alternatives": alternatives,
        "probabilities": alt_probs,
        "participation": participation,
        "mode_probabilities": mode_probs,
        "logsum": logsum,
        "beta": beta,
    }


def operating_cost(case: dict[str, Any], design: dict[str, Any]) -> float:
    costs = case.get("costs", {})
    if not costs:
        return 0.0
    length = case["network"]["corridor_length_km"]
    total = 0.0
    for product in PRODUCTS:
        departures = sum(int(value) for value in design["N"][product].values())
        if departures <= 0:
            continue
        total += costs["fixed_per_product_day"][product]
        total += departures * (
            costs["per_run"][product]
            + costs["per_train_km"][product] * length
        )
    return total


def evaluate_design(
    case: dict[str, Any],
    design: dict[str, Any],
    income_state: str,
    electrification_state: str,
) -> dict[str, Any]:
    modal = {"rail": 0.0, "road": 0.0, "auto": 0.0}
    product_pax = {product: 0.0 for product in PRODUCTS}
    seat_pax: dict[str, float] = {}
    class_trip = {name: 0.0 for name in case["sets"]["classes"]}
    class_rail = {name: 0.0 for name in case["sets"]["classes"]}
    class_potential = {name: 0.0 for name in case["sets"]["classes"]}
    class_vot = {
        name: _income_beta(case, name, income_state)["vot_yuan_hr"]
        for name in case["sets"]["classes"]
    }
    rail_load: dict[tuple[str, str, str, str], float] = {}
    market_gc: dict[tuple[str, str], list[tuple[float, float, str]]] = {}
    revenue = 0.0
    consumer_benefit = 0.0
    total_potential = 0.0
    total_trips = 0.0
    vulnerable_trips = 0.0
    generalized_cost_numerator = 0.0
    vulnerable_gc_numerator = 0.0
    probability_error = 0.0
    vulnerable = case["sets"]["vulnerable_class"]

    for segment in case["demand_segments"]:
        response = segment_probabilities(
            case,
            segment,
            design,
            income_state,
            electrification_state,
        )
        qbar = segment["qbar"]
        traveler_class = segment["class"]
        total_potential += qbar
        class_potential[traveler_class] += qbar
        trips = qbar * response["participation"]
        total_trips += trips
        class_trip[traveler_class] += trips
        if traveler_class == vulnerable:
            vulnerable_trips += trips
        consumer_benefit += (
            qbar / response["beta"]["beta_c"] * response["logsum"]
        )
        probability_error = max(
            probability_error,
            abs(sum(response["probabilities"]) - response["participation"]),
        )

        conditional_gc = 0.0
        for alt, probability in zip(
            response["alternatives"], response["probabilities"]
        ):
            flow = qbar * probability
            modal[alt["mode"]] += flow
            conditional_weight = (
                probability / response["participation"]
                if response["participation"] > 0
                else 0.0
            )
            conditional_gc += conditional_weight * generalized_cost(
                alt, response["beta"]
            )
            if alt["mode"] != "rail":
                continue
            product = alt["product"]
            seat = alt["seat"]
            product_pax[product] += flow
            class_rail[traveler_class] += flow
            seat_pax[f"{product}:{seat}"] = (
                seat_pax.get(f"{product}:{seat}", 0.0) + flow
            )
            revenue += flow * alt["rail_fare"]
            for line_segment in case["network"]["od_segments"][segment["od"]]:
                key = (product, seat, segment["period"], line_segment)
                rail_load[key] = rail_load.get(key, 0.0) + flow

        generalized_cost_numerator += trips * conditional_gc
        if traveler_class == vulnerable:
            vulnerable_gc_numerator += trips * conditional_gc
        market_gc.setdefault(
            (segment["od"], segment["period"]), []
        ).append((trips, conditional_gc, traveler_class))

    cost = operating_cost(case, design)
    profit = revenue - cost
    max_load_factor = 0.0
    for (product, seat, period, _), load in rail_load.items():
        seats = case["products"][product]["seat_capacity"][seat]
        capacity = design["N"][product][period] * seats
        if capacity > 0:
            max_load_factor = max(max_load_factor, load / capacity)
        elif load > 1e-8:
            max_load_factor = math.inf

    max_gc_ratio = 1.0
    for values in market_gc.values():
        market_trips = sum(item[0] for item in values)
        if market_trips <= 0:
            continue
        mean_gc = sum(item[0] * item[1] for item in values) / market_trips
        if mean_gc > 0:
            max_gc_ratio = max(
                max_gc_ratio,
                max(item[1] / mean_gc for item in values if item[0] > 0),
            )

    active_products = [
        product
        for product in PRODUCTS
        if sum(design["N"][product].values()) > 0
    ]
    return {
        "total_potential": total_potential,
        "total_trips": total_trips,
        "participation_rate": total_trips / total_potential,
        "modal_pax": modal,
        "rail_pax": modal["rail"],
        "rail_share_among_trips": modal["rail"] / total_trips,
        "road_share_among_trips": modal["road"] / total_trips,
        "auto_share_among_trips": modal["auto"] / total_trips,
        "product_pax": product_pax,
        "seat_pax": seat_pax,
        "class_trip": class_trip,
        "class_rail": class_rail,
        "class_potential": class_potential,
        "class_vot_yuan_hr": class_vot,
        "vulnerable_trips": vulnerable_trips,
        "revenue": revenue,
        "operating_cost": cost,
        "profit": profit,
        "consumer_benefit": consumer_benefit,
        "welfare_level": consumer_benefit + profit,
        "max_load_factor": max_load_factor,
        "mean_generalized_cost": (
            generalized_cost_numerator / total_trips if total_trips else math.nan
        ),
        "vulnerable_mean_generalized_cost": (
            vulnerable_gc_numerator / vulnerable_trips
            if vulnerable_trips
            else math.nan
        ),
        "max_generalized_cost_ratio": max_gc_ratio,
        "probability_error": probability_error,
        "active_products": active_products,
        "departures_by_product": {
            product: sum(design["N"][product].values())
            for product in PRODUCTS
        },
    }


def physical_violations(
    case: dict[str, Any],
    design: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, float]:
    violations: dict[str, float] = {}
    if metrics["max_load_factor"] > 1.0 + 1e-9:
        violations["seat_segment_capacity"] = metrics["max_load_factor"] - 1.0

    max_path_ratio = 0.0
    for period, spec in case["sets"]["periods"].items():
        used = sum(design["N"][product][period] for product in PRODUCTS)
        capacity = (
            case["constraints"]["line_capacity_per_hour"]
            * spec["duration_h"]
        )
        max_path_ratio = max(max_path_ratio, used / capacity)
    metrics["max_path_capacity_ratio"] = max_path_ratio
    if max_path_ratio > 1.0 + 1e-9:
        violations["line_path_capacity"] = max_path_ratio - 1.0

    max_fleet_ratio = 0.0
    for product in PRODUCTS:
        fleet_hours = sum(design["N"][product].values()) * case["products"][
            product
        ]["cycle_time_h"]
        available = case["products"][product]["fleet_size"] * 24.0
        max_fleet_ratio = max(max_fleet_ratio, fleet_hours / available)
    metrics["max_fleet_hour_ratio"] = max_fleet_ratio
    if max_fleet_ratio > 1.0 + 1e-9:
        violations["fleet_hours"] = max_fleet_ratio - 1.0

    minimum = case["constraints"]["min_od_departures_per_period"]
    service_gap = 0.0
    for od in case["sets"]["ods"]:
        for period in case["sets"]["periods"]:
            departures = sum(
                design["N"][product][period]
                for product in PRODUCTS
                if case["attributes"]["rail_fare"].get(od, {}).get(product)
            )
            service_gap = max(service_gap, max(0.0, minimum - departures))
    if service_gap > 0:
        violations["minimum_service"] = service_gap / max(1.0, minimum)

    fare_lower, fare_upper = case["constraints"]["fare_bounds"]
    fare_gap = 0.0
    frequency_gap = 0.0
    for product in PRODUCTS:
        for period in case["sets"]["periods"]:
            departures = design["N"][product][period]
            maximum = case["constraints"]["frequency_max"][product][period]
            if departures < 0 or departures > maximum:
                frequency_gap = max(
                    frequency_gap,
                    max(-departures, departures - maximum) / max(1, maximum),
                )
            if departures > 0:
                fare = design["phi"][product][period]
                fare_gap = max(
                    fare_gap,
                    max(fare_lower - fare, fare - fare_upper, 0.0),
                )
    if frequency_gap > 0:
        violations["frequency_bounds"] = frequency_gap
    if fare_gap > 0:
        violations["fare_bounds"] = fare_gap
    return violations


def assess_design(
    case: dict[str, Any],
    design: dict[str, Any],
    metrics: dict[str, Any],
    state_reference_metrics: dict[str, Any],
    reference_vulnerable_trips: float,
    objective: str,
    loss_tolerance: float,
    retention_floor: float,
) -> dict[str, Any]:
    assessed = dict(metrics)
    assessed["retention_rate"] = (
        metrics["vulnerable_trips"] / reference_vulnerable_trips
    )
    assessed["delta_consumer_benefit"] = (
        metrics["consumer_benefit"]
        - state_reference_metrics["consumer_benefit"]
    )
    assessed["delta_profit"] = (
        metrics["profit"] - state_reference_metrics["profit"]
    )
    assessed["delta_welfare"] = (
        metrics["welfare_level"]
        - state_reference_metrics["welfare_level"]
    )
    violations = physical_violations(case, design, assessed)
    if metrics["profit"] < -loss_tolerance:
        scale = max(1.0, abs(state_reference_metrics["revenue"]))
        violations["financial_floor"] = (
            -loss_tolerance - metrics["profit"]
        ) / scale
    if assessed["retention_rate"] < retention_floor:
        violations["vulnerable_retention"] = (
            retention_floor - assessed["retention_rate"]
        )
    assessed["violations"] = violations
    assessed["feasible"] = not violations
    assessed["penalty"] = sum(value * value for value in violations.values())
    if objective == "profit":
        assessed["objective_value"] = metrics["profit"]
    elif objective == "welfare":
        assessed["objective_value"] = assessed["delta_welfare"]
    else:
        raise ValueError(f"Unknown objective: {objective}")
    return assessed


def _rank(assessed: dict[str, Any]) -> tuple[int, float]:
    if assessed["feasible"]:
        return (1, assessed["objective_value"])
    return (0, -assessed["penalty"])


def make_start_design(
    case: dict[str, Any], active_products: tuple[str, ...]
) -> dict[str, Any]:
    periods = list(case["sets"]["periods"])
    design = {
        "periods": periods,
        "N": {product: {period: 0 for period in periods} for product in PRODUCTS},
        "phi": {
            product: {period: 1.0 for period in periods} for product in PRODUCTS
        },
    }
    for product in active_products:
        source = (
            case["observed_frequency"][product]
            if product == "K"
            else case["reference_design"]["N"][product]
        )
        for period in periods:
            design["N"][product][period] = max(1, int(source[period]))
    return design


def policy_subsets(policy: str) -> list[tuple[str, ...]]:
    if policy in {
        "status_quo_fast",
        "fare_only",
        "frequency_only",
        "joint_fare_frequency",
    }:
        return [("G", "D")]
    if policy == "conventional_activation":
        return [("G", "D"), ("G", "D", "K")]
    if policy == "unrestricted_mixed":
        return [("G", "D", "K"), ("G", "D"), ("G", "K"), ("D", "K")]
    raise ValueError(f"Unknown policy: {policy}")


def policy_controls(policy: str) -> tuple[bool, bool]:
    if policy == "status_quo_fast":
        return False, False
    if policy == "fare_only":
        return True, False
    if policy == "frequency_only":
        return False, True
    return True, True


def optimize_design(
    case: dict[str, Any],
    income_state: str,
    electrification_state: str,
    policy: str,
    objective: str,
    state_reference_metrics: dict[str, Any],
    reference_vulnerable_trips: float,
    loss_tolerance: float,
    retention_floor: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    allow_fare, allow_frequency = policy_controls(policy)
    cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    def score(design: dict[str, Any]) -> dict[str, Any]:
        key = design_key(design)
        if key not in cache:
            raw = evaluate_design(
                case, design, income_state, electrification_state
            )
            cache[key] = assess_design(
                case,
                design,
                raw,
                state_reference_metrics,
                reference_vulnerable_trips,
                objective,
                loss_tolerance,
                retention_floor,
            )
        return cache[key]

    best_design: dict[str, Any] | None = None
    best_assessed: dict[str, Any] | None = None
    lower, upper = case["constraints"]["fare_bounds"]
    fare_grid = [lower + index * (upper - lower) / 4 for index in range(5)]
    periods = list(case["sets"]["periods"])

    for subset in policy_subsets(policy):
        current = make_start_design(case, subset)
        current_score = score(current)

        if allow_fare:
            for _ in range(2):
                changed = False
                for product in subset:
                    for period in periods:
                        if current["N"][product][period] <= 0:
                            continue
                        local_design, local_score = current, current_score
                        candidates = sorted(
                            set(fare_grid + [current["phi"][product][period]])
                        )
                        for candidate in candidates:
                            trial = copy_design(current)
                            trial["phi"][product][period] = candidate
                            trial_score = score(trial)
                            if _rank(trial_score) > _rank(local_score):
                                local_design, local_score = trial, trial_score
                        if design_key(local_design) != design_key(current):
                            current, current_score = local_design, local_score
                            changed = True
                if not changed:
                    break

        if allow_frequency:
            for fine in (False, True):
                for product in subset:
                    for period in periods:
                        maximum = case["constraints"]["frequency_max"][product][
                            period
                        ]
                        present = current["N"][product][period]
                        reference = (
                            case["observed_frequency"][product][period]
                            if product == "K"
                            else case["reference_design"]["N"][product][period]
                        )
                        step = max(1, maximum // (8 if fine else 3))
                        candidates = {
                            0,
                            1,
                            maximum,
                            int(reference),
                            max(0, present - step),
                            min(maximum, present + step),
                        }
                        local_design, local_score = current, current_score
                        for candidate in sorted(candidates):
                            trial = copy_design(current)
                            trial["N"][product][period] = int(candidate)
                            if (
                                policy == "conventional_activation"
                                and "K" in subset
                                and product == "K"
                                and sum(trial["N"]["K"].values()) == 0
                            ):
                                # The K-on branch must represent genuine
                                # conventional-service activation. The separate
                                # G-D subset is the exactly comparable K-off
                                # branch.
                                continue
                            trial_score = score(trial)
                            if _rank(trial_score) > _rank(local_score):
                                local_design, local_score = trial, trial_score
                        current, current_score = local_design, local_score

        if allow_fare and allow_frequency:
            for product in subset:
                for period in periods:
                    if current["N"][product][period] <= 0:
                        continue
                    local_design, local_score = current, current_score
                    center = current["phi"][product][period]
                    candidates = {
                        lower,
                        upper,
                        center,
                        max(lower, center - 0.05),
                        min(upper, center + 0.05),
                    }
                    for candidate in sorted(candidates):
                        trial = copy_design(current)
                        trial["phi"][product][period] = candidate
                        trial_score = score(trial)
                        if _rank(trial_score) > _rank(local_score):
                            local_design, local_score = trial, trial_score
                    current, current_score = local_design, local_score

        if best_assessed is None or _rank(current_score) > _rank(best_assessed):
            best_design, best_assessed = current, current_score

    assert best_design is not None and best_assessed is not None
    best_assessed["evaluations"] = len(cache)
    return best_design, best_assessed


def validate_scale_order(case: dict[str, Any]) -> bool:
    mu = case["utility"]["mu"]
    return all(
        0.0 < mu[mode] <= mu["mode_level"] <= mu["top"] == 1.0
        for mode in MODES
    )
