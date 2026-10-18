"""Build service-pattern-aware cases from aligned cases and observed trains.

Every G, D, and K service observed on the reference date belongs to the
incumbent portfolio.  Optional synthetic patterns are supplied explicitly in
the aligned case and are kept at zero in the reference design.  This separation
prevents an observed K train from being misclassified as a reopening decision.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


PRODUCTS = ("G", "D", "K")
SPEED_KMH = {"G": 300.0, "D": 200.0, "K": 120.0}


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def product_type(train_no: str) -> str:
    code = str(train_no).strip().upper()
    if code.startswith(("G", "C")):
        return "G"
    if code.startswith("D"):
        return "D"
    return "K"


def minutes_from_clock(text: str) -> int:
    try:
        hour, minute = str(text).split(":")[:2]
        return int(hour) * 60 + int(minute)
    except (TypeError, ValueError):
        return 12 * 60


def period_of(text: str, periods: dict[str, dict[str, float]]) -> str:
    hour = minutes_from_clock(text) / 60.0
    for name, spec in periods.items():
        start = float(spec["start"])
        end = float(spec["end"])
        if start <= hour < end:
            return name
    # Period definitions in the cases cover 24 hours; retain a deterministic
    # fallback for malformed source times.
    return next(reversed(periods))


def _od_endpoints(case: dict[str, Any], od: str) -> tuple[str, str]:
    endpoints = case["network"].get("od_endpoints", {}).get(od)
    if endpoints is None:
        endpoints = od.split("-", 1)
    if len(endpoints) != 2:
        raise ValueError(f"OD {od!r} needs two endpoints")
    return str(endpoints[0]), str(endpoints[1])


def _ordered_od_key(
    case: dict[str, Any], od: str, city_index: dict[str, int]
) -> tuple[int, int]:
    origin, destination = _od_endpoints(case, od)
    return city_index[origin], city_index[destination]


def _route_segments_for_ods(case: dict[str, Any], served_ods: list[str]) -> list[str]:
    used: set[str] = set()
    for od in served_ods:
        used.update(case["network"]["od_segments"][od])
    return [segment for segment in case["network"]["segments"] if segment in used]


def _route_length(case: dict[str, Any], route_segments: list[str]) -> float:
    lengths = case["network"]["segment_lengths_km"]
    return float(sum(float(lengths[segment]) for segment in route_segments))


def _pattern_id(index: int, served_ods: list[str]) -> str:
    compact = "__".join(od.replace("-", "_") for od in served_ods)
    return f"K_P{index:02d}_{compact}"


def build_pattern_case(
    base_case_path: str | Path,
    trains_csv_path: str | Path,
    *,
    existing_service_floor_ratio: float = 0.05,
    frequency_expansion_factor: float = 1.50,
) -> dict[str, Any]:
    """Return an enriched case with incumbent and optional candidate patterns.

    ``existing_service_floor_ratio`` is retained for command-line compatibility
    with older packages.  Version 2.0 instead applies the manuscript's clearer
    rule: every incumbent pattern must operate at least once per day.
    """
    if not 0.0 < existing_service_floor_ratio <= 1.0:
        raise ValueError("existing_service_floor_ratio must lie in (0, 1]")
    if frequency_expansion_factor < 1.0:
        raise ValueError("frequency_expansion_factor must be at least 1")

    case = load_json(base_case_path)
    periods = list(case["sets"]["periods"])
    ods = list(case["sets"]["ods"])
    city_index = {city: i for i, city in enumerate(case["sets"]["cities"])}
    endpoint_to_od = {
        _od_endpoints(case, od): od for od in ods
    }

    patterns: list[dict[str, Any]] = []

    # Preserve the observed G/D reference frequencies exactly.
    for product in ("G", "D"):
        served_ods = [
            od for od in ods
            if case["attributes"]["rail_fare"].get(od, {}).get(product)
        ]
        if not served_ods:
            continue
        route_segments = _route_segments_for_ods(case, served_ods)
        observed = {
            period: int(case["observed_frequency"][product][period])
            for period in periods
        }
        maximum = {
            period: int(case["constraints"]["frequency_max"][product][period])
            for period in periods
        }
        length = _route_length(case, route_segments)
        patterns.append({
            "id": f"{product}_CORRIDOR",
            "product": product,
            "status": "incumbent_observed",
            "served_ods": served_ods,
            "route_segments": route_segments,
            "route_length_km": length,
            "cycle_time_h": 2.0 * length / SPEED_KMH[product] + 0.50,
            "observed_frequency": observed,
            "frequency_max": maximum,
            "activation_cost": 0.0,
        })

    # Group individual K trains by the exact set of forward ODs they serve.
    # The same through train can appear in multiple OD query rows; grouping by
    # train number first prevents double counting.
    by_train: dict[str, list[dict[str, str]]] = defaultdict(list)
    with Path(trains_csv_path).open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            train_no = str(row.get("train_no", "")).strip()
            origin = str(row.get("od_origin", "")).strip()
            destination = str(row.get("od_dest", "")).strip()
            od = endpoint_to_od.get((origin, destination))
            if not train_no or product_type(train_no) != "K" or od not in ods:
                continue
            if city_index.get(origin, 10**6) >= city_index.get(destination, -1):
                continue
            by_train[train_no].append(row)

    pattern_counts: dict[tuple[str, ...], dict[str, int]] = defaultdict(
        lambda: {period: 0 for period in periods}
    )
    for rows in by_train.values():
        served = sorted(
            {
                endpoint_to_od[(row["od_origin"], row["od_dest"])]
                for row in rows
            },
            key=lambda od: _ordered_od_key(case, od, city_index),
        )
        if not served:
            continue
        entry_origin_index = min(city_index[row["od_origin"]] for row in rows)
        entry_rows = [
            row for row in rows
            if city_index[row["od_origin"]] == entry_origin_index
        ]
        entry = min(entry_rows, key=lambda row: minutes_from_clock(row.get("start_time", "12:00")))
        pattern_counts[tuple(served)][period_of(entry.get("start_time", "12:00"), case["sets"]["periods"])] += 1

    # Stable order: broadest coverage first, then input city order.
    ordered_patterns = sorted(
        pattern_counts,
        key=lambda served: (
            -len(served),
            tuple(_ordered_od_key(case, od, city_index) for od in served),
        ),
    )
    k_fixed = float(case["costs"]["fixed_per_product_day"]["K"])
    for index, served_tuple in enumerate(ordered_patterns, start=1):
        served_ods = list(served_tuple)
        route_segments = _route_segments_for_ods(case, served_ods)
        length = _route_length(case, route_segments)
        observed = dict(pattern_counts[served_tuple])
        maximum = {
            period: max(
                2,
                int(math.ceil(frequency_expansion_factor * max(1, observed[period]))),
            )
            for period in periods
        }
        patterns.append({
            "id": _pattern_id(index, served_ods),
            "product": "K",
            "status": "incumbent_observed",
            "served_ods": served_ods,
            "route_segments": route_segments,
            "route_length_km": length,
            "cycle_time_h": 2.0 * length / SPEED_KMH["K"] + 0.50,
            "observed_frequency": observed,
            "frequency_max": maximum,
            "activation_cost": 0.0,
        })

    if not any(pattern["product"] == "K" for pattern in patterns):
        raise ValueError("No observed forward-direction K service pattern was found")

    # Synthetic candidates are never inferred from the observed train rows.
    # They must be declared transparently in the aligned case.
    seen_ids = {pattern["id"] for pattern in patterns}
    for raw in case.get("synthetic_service_patterns", []):
        candidate = dict(raw)
        pattern_id = str(candidate.get("id", "")).strip()
        if not pattern_id or pattern_id in seen_ids:
            raise ValueError(f"Invalid or duplicate synthetic pattern id: {pattern_id!r}")
        product = str(candidate.get("product", "K"))
        if product != "K":
            raise ValueError("This model version permits only synthetic K patterns")
        served_ods = [str(od) for od in candidate.get("served_ods", [])]
        route_segments = [str(seg) for seg in candidate.get("route_segments", [])]
        if not served_ods or not set(served_ods).issubset(ods):
            raise ValueError(f"Synthetic pattern {pattern_id!r} has invalid served_ods")
        if not route_segments or not set(route_segments).issubset(
            case["network"]["segments"]
        ):
            raise ValueError(f"Synthetic pattern {pattern_id!r} has invalid route_segments")
        maximum_raw = candidate.get("frequency_max", {})
        maximum = {period: int(maximum_raw.get(period, 0)) for period in periods}
        if any(value < 0 for value in maximum.values()):
            raise ValueError(f"Synthetic pattern {pattern_id!r} has a negative maximum")
        share = float(candidate.get("activation_cost_share_of_k_fixed", 0.15))
        if share < 0:
            raise ValueError(f"Synthetic pattern {pattern_id!r} has a negative activation share")
        patterns.append({
            "id": pattern_id,
            "product": "K",
            "status": "candidate_synthetic",
            "served_ods": served_ods,
            "route_segments": route_segments,
            "route_length_km": float(candidate["route_length_km"]),
            "cycle_time_h": float(candidate["cycle_time_h"]),
            "observed_frequency": {period: 0 for period in periods},
            "frequency_max": maximum,
            "activation_cost": share * k_fixed,
            "activation_cost_share_of_k_fixed": share,
            "minimum_daily_departures_if_active": int(
                candidate.get("minimum_daily_departures_if_active", 1)
            ),
            "synthetic_definition": candidate.get("synthetic_definition", ""),
        })
        seen_ids.add(pattern_id)

    daily_floors = {product: 0 for product in PRODUCTS}

    enriched = dict(case)
    enriched["meta"] = dict(case["meta"])
    enriched["meta"]["pattern_model_version"] = "2.0-incumbent-candidate"
    enriched["meta"]["pattern_source_trains"] = str(Path(trains_csv_path).resolve())
    enriched["service_patterns"] = patterns
    enriched["pattern_constraints"] = {
        "incumbent_status": "incumbent_observed",
        "candidate_status": "candidate_synthetic",
        "required_existing_products": ["G", "D", "K"],
        "minimum_daily_departures_by_product": daily_floors,
        "minimum_daily_departures_by_incumbent_pattern": 1,
        "minimum_daily_departures_by_candidate_when_active": 1,
        "candidate_eligibility_rule": "explicit synthetic definitions only",
        "k_eligibility_rule": "observed K patterns are incumbent; explicit synthetic K patterns are P4 candidates",
        "existing_service_floor_ratio": existing_service_floor_ratio,
        "frequency_expansion_factor": frequency_expansion_factor,
        "minimum_active_pattern_daily_departures": 1,
    }
    enriched["pattern_reference_design"] = {
        "periods": periods,
        "N": {
            pattern["id"]: {
                period: (
                    int(pattern["observed_frequency"][period])
                    if pattern["status"] == "incumbent_observed" else 0
                )
                for period in periods
            }
            for pattern in patterns
        },
        "phi": {
            product: {period: 1.0 for period in periods}
            for product in PRODUCTS
        },
    }
    return enriched


def pattern_summary(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": pattern["id"],
            "product": pattern["product"],
            "status": pattern["status"],
            "served_ods": pattern["served_ods"],
            "observed_daily_departures": int(sum(pattern["observed_frequency"].values())),
            "maximum_daily_departures": int(sum(pattern["frequency_max"].values())),
        }
        for pattern in case["service_patterns"]
    ]
