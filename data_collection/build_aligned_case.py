"""Build and calibrate a TRA-V7 rail--road passenger corridor case."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from corridor_common import (
    PRODUCTS,
    adjacent_segments,
    city_names,
    data_paths,
    file_manifest,
    forward_od_pairs,
    load_config,
    load_csv,
    od_segment_map,
    product_type,
    save_json,
    write_csv,
)


PIPELINE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_ROOT))
from case_model import evaluate_design, period_of  # noqa: E402


DEFAULT_PERIODS = {
    "早高峰": {"start": 6, "end": 9, "duration_h": 3.0},
    "日间": {"start": 9, "end": 17, "duration_h": 8.0},
    "晚高峰": {"start": 17, "end": 20, "duration_h": 3.0},
    "夜间": {"start": 20, "end": 6, "duration_h": 10.0},
}
DEFAULT_CLASS_SHARE = {"高收入": 0.25, "中收入": 0.50, "低收入": 0.25}
SEATS = {
    "G": ["商务座", "一等座", "二等座"],
    "D": ["一等座", "二等座"],
    "K": ["硬座", "硬卧", "软卧"],
}
CAPACITY = {
    "G": {"商务座": 18, "一等座": 96, "二等座": 576},
    "D": {"一等座": 72, "二等座": 480},
    "K": {"硬座": 768, "硬卧": 528, "软卧": 72},
}
TOTAL_CAPACITY = {product: sum(values.values()) for product, values in CAPACITY.items()}
LOAD_FACTOR = {"G": 0.78, "D": 0.72, "K": 0.70}
FARE_SEAT_RATIO = {
    "G": {"商务座": 3.00, "一等座": 1.60, "二等座": 1.00},
    "D": {"一等座": 1.60, "二等座": 1.00},
    "K": {"硬座": 1.00, "硬卧": 2.00, "软卧": 3.00},
}
DEFAULT_UTILITY = {
    "高收入": {
        "beta_c": 0.012, "beta_iv": 0.035, "beta_ac": 0.045,
        "beta_wt": 0.050, "beta_sc": 0.025, "beta_rel": 0.020,
        "beta_tr": 0.15, "gamma_com": 0.08, "gamma_flex": 0.10,
    },
    "中收入": {
        "beta_c": 0.020, "beta_iv": 0.030, "beta_ac": 0.040,
        "beta_wt": 0.045, "beta_sc": 0.022, "beta_rel": 0.018,
        "beta_tr": 0.12, "gamma_com": 0.06, "gamma_flex": 0.07,
    },
    "低收入": {
        "beta_c": 0.035, "beta_iv": 0.025, "beta_ac": 0.035,
        "beta_wt": 0.040, "beta_sc": 0.018, "beta_rel": 0.015,
        "beta_tr": 0.10, "gamma_com": 0.04, "gamma_flex": 0.05,
    },
}


def minutes_from_clock(text: str) -> int:
    try:
        hour, minute = text.split(":")[:2]
        return int(hour) * 60 + int(minute)
    except (ValueError, AttributeError):
        return 12 * 60


def duration_minutes(text: str) -> float | None:
    try:
        hour, minute = text.split(":")[:2]
        value = int(hour) * 60 + int(minute)
        return float(value) if 10 < value < 1440 else None
    except (ValueError, AttributeError):
        return None


def is_forward(origin: str, destination: str, index: dict[str, int]) -> bool:
    return origin in index and destination in index and index[origin] < index[destination]


def median_tables(
    train_rows: list[dict[str, str]],
    price_rows: list[dict[str, str]],
    index: dict[str, int],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    times: dict[tuple[str, str], list[float]] = defaultdict(list)
    fares: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in train_rows:
        if not is_forward(row.get("od_origin", ""), row.get("od_dest", ""), index):
            continue
        runtime = duration_minutes(row.get("duration", ""))
        if runtime is not None:
            od = f"{row['od_origin']}-{row['od_dest']}"
            times[(od, product_type(row.get("train_no", "")))].append(runtime)
    for row in price_rows:
        if not is_forward(row.get("od_origin", ""), row.get("od_dest", ""), index):
            continue
        od = f"{row['od_origin']}-{row['od_dest']}"
        product = product_type(row.get("train_code") or row.get("train_no", ""))
        for seat in SEATS[product]:
            raw = row.get(seat)
            if raw in {None, "", "--", "无"}:
                continue
            try:
                fares[(od, product, seat)].append(float(raw))
            except (TypeError, ValueError):
                pass
    runtime_table: dict[str, dict[str, float]] = defaultdict(dict)
    fare_table: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for (od, product), values in times.items():
        runtime_table[od][product] = round(statistics.median(values), 2)
    for (od, product, seat), values in fares.items():
        fare_table[od][product][seat] = round(statistics.median(values), 2)
    imputation_audit: list[dict[str, Any]] = []
    for od, products in fare_table.items():
        for product, observed_seats in products.items():
            ratios = FARE_SEAT_RATIO[product]
            normalized_bases = [
                float(value) / ratios[seat]
                for seat, value in observed_seats.items()
                if seat in ratios
            ]
            if not normalized_bases:
                continue
            normalized_base = statistics.median(normalized_bases)
            for seat in SEATS[product]:
                if seat in observed_seats:
                    continue
                imputed = round(normalized_base * ratios[seat], 2)
                observed_seats[seat] = imputed
                imputation_audit.append(
                    {
                        "od": od,
                        "product": product,
                        "seat": seat,
                        "imputed_fare": imputed,
                        "method": "within-OD product fare normalized by configured seat ratio",
                        "seat_ratio": ratios[seat],
                    }
                )
    return (
        json.loads(json.dumps(runtime_table, ensure_ascii=False)),
        json.loads(json.dumps(fare_table, ensure_ascii=False)),
        imputation_audit,
    )


def build_road(passenger_rows: list[dict[str, str]], index: dict[str, int]) -> dict[str, dict[str, float]]:
    result = {}
    required = {
        "distance_km", "duration_min", "coach_duration_min", "tolls_yuan",
        "private_auto_cost", "coach_fare", "maas_fare", "business_van_fare",
    }
    for row in passenger_rows:
        if not is_forward(row["origin"], row["destination"], index):
            continue
        missing = [key for key in required if row.get(key) in {None, ""}]
        if missing:
            raise ValueError(f"Road row {row['origin']}->{row['destination']} lacks {missing}")
        result[f"{row['origin']}-{row['destination']}"] = {
            "distance_km": float(row["distance_km"]),
            "auto_duration_min": float(row["duration_min"]),
            "coach_duration_min": float(row["coach_duration_min"]),
            "tolls_yuan": float(row["tolls_yuan"]),
            "private_auto_cost": float(row["private_auto_cost"]),
            "coach_fare": float(row["coach_fare"]),
            "maas_fare": float(row["maas_fare"]),
            "business_van_fare": float(row["business_van_fare"]),
        }
    return result


def build_access(
    cities: list[str],
    access_rows: list[dict[str, str]],
    fare_rows: list[dict[str, str]],
) -> dict[str, dict[str, float]]:
    times: dict[str, list[float]] = defaultdict(list)
    fares: dict[str, list[float]] = defaultdict(list)
    for row in access_rows:
        if row.get("drive_duration_min"):
            times[row["city"]].append(float(row["drive_duration_min"]))
    for row in fare_rows:
        if row.get("access_fare"):
            fares[row["city"]].append(float(row["access_fare"]))
    missing = [city for city in cities if not times[city] or not fares[city]]
    if missing:
        raise ValueError(f"No usable station-access observations for: {missing}")
    return {
        city: {
            "time_min": round(statistics.median(times[city]), 2),
            "fare": round(statistics.median(fares[city]), 2),
        }
        for city in cities
    }


def observed_allocation(
    train_rows: list[dict[str, str]],
    road_by_od: dict[str, dict[str, float]],
    index: dict[str, int],
    od_segments: dict[str, list[str]],
    line_segments: list[str],
    periods: dict[str, dict[str, float]],
    load_factor: dict[str, float],
) -> tuple[dict[str, dict[str, int]], dict[tuple[str, str], float], dict[str, Any]]:
    by_train: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in train_rows:
        if is_forward(row.get("od_origin", ""), row.get("od_dest", ""), index):
            by_train[row.get("train_no", "")].append(row)
    observed = {product: {period: 0 for period in periods} for product in PRODUCTS}
    rail_flow: dict[tuple[str, str], float] = defaultdict(float)
    checks: list[float] = []
    for train_no, rows in by_train.items():
        if not train_no:
            continue
        product = product_type(train_no)
        entry_index = min(index[row["od_origin"]] for row in rows)
        entry = min(
            (row for row in rows if index[row["od_origin"]] == entry_index),
            key=lambda row: minutes_from_clock(row.get("start_time", "12:00")),
        )
        period = period_of(entry.get("start_time", "12:00"), periods)
        observed[product][period] += 1
        served = sorted(
            {f"{row['od_origin']}-{row['od_dest']}" for row in rows}
            & set(od_segments)
        )
        if not served:
            continue
        weights = {od: road_by_od[od]["distance_km"] ** -0.60 for od in served}
        segment_weight = {
            line: sum(weight for od, weight in weights.items() if line in od_segments[od])
            for line in line_segments
        }
        peak_weight = max(segment_weight.values())
        scale = TOTAL_CAPACITY[product] * load_factor[product] / peak_weight
        allocation = {od: weight * scale for od, weight in weights.items()}
        for od, flow in allocation.items():
            rail_flow[(od, period)] += flow
        peak_load = max(
            sum(allocation[od] for od in served if line in od_segments[od])
            for line in line_segments
        )
        checks.append(peak_load / (TOTAL_CAPACITY[product] * load_factor[product]))
    if not by_train:
        raise ValueError("No forward-direction train records are available")
    return observed, rail_flow, {
        "unique_forward_trains": len(by_train),
        "maximum_train_allocation_ratio_error": max((abs(value - 1.0) for value in checks), default=0.0),
    }


def rail_share(distance: float, demand: dict[str, Any], od: str) -> float:
    if od in demand.get("rail_share_by_od", {}):
        return float(demand["rail_share_by_od"][od])
    bands = demand.get(
        "rail_share_by_distance",
        [
            {"min_km": 0, "max_km": 100, "share": 0.45},
            {"min_km": 100, "max_km": 200, "share": 0.60},
            {"min_km": 200, "max_km": 350, "share": 0.70},
            {"min_km": 350, "max_km": 600, "share": 0.65},
            {"min_km": 600, "max_km": 100000, "share": 0.60},
        ],
    )
    for band in bands:
        if float(band["min_km"]) <= distance < float(band["max_km"]):
            value = float(band["share"])
            if not 0 < value < 1:
                raise ValueError("Rail-share assumptions must lie strictly between 0 and 1")
            return value
    raise ValueError(f"No rail-share distance band covers {od} ({distance} km)")


def build_demand_segments(
    config: dict[str, Any],
    road: dict[str, dict[str, float]],
    allocated_rail: dict[tuple[str, str], float],
    periods: dict[str, dict[str, float]],
    class_share: dict[str, float],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    demand = config.get("demand", {})
    method = str(demand.get("method", "capacity_loadfactor_mode_share"))
    participation = float(demand.get("reference_participation_target", 0.85))
    if not 0 < participation <= 1:
        raise ValueError("reference_participation_target must be in (0, 1]")
    segments = []
    audit_rows = []
    target_rail_total = 0.0
    target_market_total = 0.0
    if method == "explicit_od_daily_total":
        totals = demand.get("od_daily_total", {})
        missing = [od for od in road if od not in totals]
        if missing:
            raise ValueError(f"demand.od_daily_total is missing ODs: {missing}")
        raw_period_share = demand.get(
            "period_share", {name: spec["duration_h"] for name, spec in periods.items()}
        )
        scale = sum(float(raw_period_share[name]) for name in periods)
        period_share = {name: float(raw_period_share[name]) / scale for name in periods}
        for od, attrs in road.items():
            daily = float(totals[od])
            share = rail_share(attrs["distance_km"], demand, od)
            for period in periods:
                market = daily * period_share[period]
                target_market_total += market
                target_rail_total += market * share
                audit_rows.append(
                    {"od": od, "period": period, "rail_share": share, "target_market_trips": market, "method": method}
                )
                for traveler_class, class_fraction in class_share.items():
                    target = market * class_fraction
                    segments.append(
                        {
                            "id": f"{od}|{traveler_class}|{period}", "od": od,
                            "class": traveler_class, "period": period,
                            "target_reference_trips": target, "qbar": target / participation,
                        }
                    )
    elif method == "capacity_loadfactor_mode_share":
        for od, attrs in road.items():
            share = rail_share(attrs["distance_km"], demand, od)
            for period in periods:
                rail_trips = allocated_rail.get((od, period), 0.0)
                if rail_trips <= 0:
                    continue
                market = rail_trips / share
                target_rail_total += rail_trips
                target_market_total += market
                audit_rows.append(
                    {"od": od, "period": period, "rail_share": share, "estimated_rail_trips": rail_trips, "target_market_trips": market, "method": method}
                )
                for traveler_class, class_fraction in class_share.items():
                    target = market * class_fraction
                    segments.append(
                        {
                            "id": f"{od}|{traveler_class}|{period}", "od": od,
                            "class": traveler_class, "period": period,
                            "target_reference_trips": target, "qbar": target / participation,
                        }
                    )
    else:
        raise ValueError(f"Unsupported demand.method: {method}")
    if not segments or target_market_total <= 0:
        raise ValueError("Demand generation produced no positive segments")
    calibration = {
        "demand_method": method,
        "reference_participation_target": participation,
        "target_rail_share": target_rail_total / target_market_total,
        "target_rail_trips": target_rail_total,
        "target_market_trips": target_market_total,
        "rail_share_source": "configured OD values or distance-band assumptions",
    }
    return segments, calibration, audit_rows


def product_specs(length: float, config: dict[str, Any]) -> dict[str, Any]:
    model = config.get("model", {})
    fleet = model.get("fleet_size", {"G": 25, "D": 15, "K": 12})
    speeds = {"G": 300.0, "D": 200.0, "K": 120.0}
    names = {"G": "high_speed", "D": "emu", "K": "conventional"}
    comforts = {
        "G": {"商务座": 5.0, "一等座": 4.0, "二等座": 3.0},
        "D": {"一等座": 4.0, "二等座": 3.0},
        "K": {"硬座": 2.0, "硬卧": 3.0, "软卧": 4.0},
    }
    return {
        product: {
            "name": names[product],
            "seat_capacity": CAPACITY[product],
            "seat_comfort": comforts[product],
            "flexibility": {"G": 2.0, "D": 2.0, "K": 1.0}[product],
            "reliability_fraction": {"G": 0.02, "D": 0.03, "K": 0.08}[product],
            "cycle_time_h": 2 * length / speeds[product] + 0.50,
            "fleet_size": int(fleet.get(product, {"G": 25, "D": 15, "K": 12}[product])),
        }
        for product in PRODUCTS
    }


def utility_block(config: dict[str, Any], classes: list[str]) -> dict[str, Any]:
    model = config.get("model", {})
    by_class = dict(DEFAULT_UTILITY)
    by_class.update(model.get("utility_by_class", {}))
    missing = [name for name in classes if name not in by_class]
    if missing:
        raise ValueError(f"model.utility_by_class is required for custom classes: {missing}")
    mu = {"rail": 0.45, "road": 0.50, "auto": 0.55, "mode_level": 0.75, "top": 1.0}
    mu.update(model.get("nesting_mu", {}))
    asc_seat = {}
    for product, capacities in CAPACITY.items():
        reference = max(capacities.values())
        asc_seat[product] = {
            seat: round(mu["rail"] * math.log(capacity / reference), 6)
            for seat, capacity in capacities.items()
        }
    default_rho = {"高收入": 0.70, "中收入": 0.80, "低收入": 0.90}
    rho = {name: float(model.get("income_elasticity", {}).get(name, default_rho.get(name, 0.80))) for name in classes}
    return {
        "by_class": {name: by_class[name] for name in classes},
        "rho": rho,
        "mu": mu,
        "asc_mode": {name: {"rail": 0.0, "road": 0.0, "auto": 0.0} for name in classes},
        "alpha_travel": {name: 0.0 for name in classes},
        "asc_product": {"G": 0.15, "D": 0.0, "K": -0.10},
        "asc_seat": asc_seat,
        "asc_alternative": {"private_auto": 0.0, "coach": -0.10, "maas": 0.05, "business_van": -0.15},
    }


def scenarios(config: dict[str, Any], classes: list[str]) -> dict[str, Any]:
    supplied = config.get("scenarios")
    if supplied:
        return supplied
    reference = {name: 0.0 for name in classes}
    common = {name: -0.10 for name in classes}
    polarized_defaults = {"高收入": 0.02, "中收入": -0.08, "低收入": -0.15}
    polarized = {name: polarized_defaults.get(name, -0.10) for name in classes}
    return {
        "income": {"reference": reference, "common_downturn": common, "polarized_downturn": polarized},
        "electrification": {
            "none": {"auto_intensity": 0.0, "road_services": [], "pass_through": 0.0},
            "auto_only": {"auto_intensity": 0.50, "road_services": [], "pass_through": 0.0},
            "auto_maas_low": {"auto_intensity": 0.50, "road_services": ["maas", "business_van"], "pass_through": 0.30},
            "auto_maas_high": {"auto_intensity": 0.50, "road_services": ["maas", "business_van"], "pass_through": 0.70},
            "all_road_low": {"auto_intensity": 0.50, "road_services": ["coach", "maas", "business_van"], "pass_through": 0.30},
            "all_road_high": {"auto_intensity": 0.50, "road_services": ["coach", "maas", "business_van"], "pass_through": 0.70},
        },
    }


def make_base_case(config: dict[str, Any], data_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    paths = data_paths(config, data_dir)
    required_keys = ("trains", "prices", "amap_od", "amap_access", "road_passenger", "access_fares")
    missing = [str(paths[key]) for key in required_keys if not paths[key].exists()]
    if missing:
        raise FileNotFoundError("Required pipeline files are missing: " + ", ".join(missing))
    cities = city_names(config)
    index = {city: position for position, city in enumerate(cities)}
    periods = config.get("periods", DEFAULT_PERIODS)
    class_share = {key: float(value) for key, value in config.get("demand", {}).get("class_share", DEFAULT_CLASS_SHARE).items()}
    classes = list(class_share)
    vulnerable = str(config.get("demand", {}).get("vulnerable_class", classes[-1]))
    if vulnerable not in classes:
        raise ValueError("demand.vulnerable_class must be one of demand.class_share")
    line_segments = adjacent_segments(config)
    od_segments = od_segment_map(config)
    train_rows = load_csv(paths["trains"])
    price_rows = load_csv(paths["prices"])
    road = build_road(load_csv(paths["road_passenger"]), index)
    missing_ods = [od for od in od_segments if od not in road]
    if missing_ods:
        raise ValueError(f"Road data is missing forward ODs: {missing_ods}")
    segment_lengths = {line: road[line]["distance_km"] for line in line_segments}
    length = sum(segment_lengths.values())
    runtime, rail_fare, fare_imputation = median_tables(train_rows, price_rows, index)
    missing_rail_ods = [od for od in od_segments if od not in runtime or od not in rail_fare]
    if missing_rail_ods:
        raise ValueError(f"12306 data has no usable runtime/fare for forward ODs: {missing_rail_ods}")
    load_factor = dict(LOAD_FACTOR)
    load_factor.update({key: float(value) for key, value in config.get("demand", {}).get("load_factor", {}).items()})
    observed, rail_flow, allocation_audit = observed_allocation(
        train_rows, road, index, od_segments, line_segments, periods, load_factor
    )
    segments, calibration, demand_audit = build_demand_segments(
        config, road, rail_flow, periods, class_share
    )
    available = [
        product for product in PRODUCTS
        if sum(observed[product].values()) > 0
        and any(product in rail_fare.get(od, {}) for od in od_segments)
    ]
    configured_reference = config.get("model", {}).get("reference_products")
    if configured_reference is None:
        reference_products = [product for product in ("G", "D") if product in available] or available
    else:
        reference_products = [str(product) for product in configured_reference]
    invalid_reference = [product for product in reference_products if product not in available]
    if invalid_reference:
        raise ValueError(f"Configured reference products lack observed train/fare data: {invalid_reference}")
    if not reference_products:
        raise ValueError("No rail product is available for the reference design")
    reference_n = {
        product: {
            period: observed[product][period] if product in reference_products else 0
            for period in periods
        }
        for product in PRODUCTS
    }
    frequency_max = {
        product: {
            period: max(2, math.ceil(1.5 * max(1, observed[product][period])))
            for period in periods
        }
        for product in PRODUCTS
    }
    model = config.get("model", {})
    case = {
        "meta": {
            "name": str(config["name"]), "version": "1.0",
            "case_type": str(config.get("case_type", "calibrated numerical illustration")),
            "direction": f"{cities[0]}->{cities[-1]}",
            "source_manifest": file_manifest([paths[key] for key in required_keys]),
            "pipeline_case_id": config["case_id"],
            "demand_data_status": (
                "observed/user-supplied" if calibration["demand_method"] == "explicit_od_daily_total"
                else "assumption-derived from rail supply"
            ),
        },
        "sets": {
            "cities": cities, "ods": list(od_segments), "periods": periods,
            "classes": classes, "vulnerable_class": vulnerable, "products": list(PRODUCTS),
        },
        "network": {
            "segments": line_segments, "segment_lengths_km": segment_lengths,
            "od_segments": od_segments, "corridor_length_km": length,
        },
        "products": product_specs(length, config),
        "attributes": {
            "rail_fare": rail_fare, "rail_runtime_min": runtime, "road_by_od": road,
            "access_by_city": build_access(cities, load_csv(paths["amap_access"]), load_csv(paths["access_fares"])),
        },
        "demand_segments": segments,
        "observed_frequency": observed,
        "reference_design": {
            "periods": list(periods), "N": reference_n,
            "phi": {product: {period: 1.0 for period in periods} for product in PRODUCTS},
        },
        "utility": utility_block(config, classes),
        "schedule": {"vartheta_min": 15.0, "terminal_wait_min": 10.0},
        "electrification_savings": {
            "private_auto_per_km": 0.58, "maas_per_km": 0.20,
            "business_van_per_km": 0.30, "coach_per_km": 0.12,
        },
        "scenarios": scenarios(config, classes),
        "constraints": {
            "fare_bounds": model.get("fare_bounds", [0.80, 1.20]),
            "frequency_max": frequency_max,
            "line_capacity_per_hour": float(model.get("line_capacity_per_hour", 16)),
            "min_od_departures_per_period": int(model.get("min_od_departures_per_period", 1)),
            "loss_tolerance_options": model.get("loss_tolerance_options", [0.0, 500000.0, 2000000.0]),
            "retention_floor_options": model.get("retention_floor_options", [0.90, 0.95, 1.00]),
        },
        "calibration": {
            **calibration,
            "demand_allocation": (
                "unique-train OD weights scaled to each train's peak segment load"
                if calibration["demand_method"] == "capacity_loadfactor_mode_share"
                else "user-supplied OD daily totals split by configured period/class shares"
            ),
            "load_factor": load_factor,
            "fare_imputation": fare_imputation,
            "fare_imputation_count": len(fare_imputation),
            "reference_products": reference_products,
            "cost_reference_operating_ratio": float(model.get("cost_reference_operating_ratio", 0.92)),
        },
        "costs": {},
    }
    return case, allocation_audit, demand_audit


def calibrate_constants(case: dict[str, Any]) -> dict[str, Any]:
    z0 = case["reference_design"]
    target_share = case["calibration"]["target_rail_share"]
    target_participation = case["calibration"]["reference_participation_target"]
    steps = {}
    for traveler_class in case["sets"]["classes"]:
        for _outer in range(8):
            lower, upper = -15.0, 15.0
            for _ in range(50):
                midpoint = (lower + upper) / 2
                case["utility"]["asc_mode"][traveler_class]["rail"] = midpoint
                metrics = evaluate_design(case, z0, "reference", "none")
                trips = metrics["class_trip"][traveler_class]
                share = metrics["class_rail"][traveler_class] / trips if trips else 0.0
                if share < target_share:
                    lower = midpoint
                else:
                    upper = midpoint
            case["utility"]["asc_mode"][traveler_class]["rail"] = (lower + upper) / 2
            lower, upper = -25.0, 25.0
            for _ in range(50):
                midpoint = (lower + upper) / 2
                case["utility"]["alpha_travel"][traveler_class] = midpoint
                metrics = evaluate_design(case, z0, "reference", "none")
                potential = metrics["class_potential"][traveler_class]
                participation = metrics["class_trip"][traveler_class] / potential if potential else 0.0
                if participation < target_participation:
                    lower = midpoint
                else:
                    upper = midpoint
            case["utility"]["alpha_travel"][traveler_class] = (lower + upper) / 2
        steps[traveler_class] = {
            "rail_mode_asc": case["utility"]["asc_mode"][traveler_class]["rail"],
            "travel_constant": case["utility"]["alpha_travel"][traveler_class],
        }
    return steps


def calibrate_costs(case: dict[str, Any]) -> dict[str, Any]:
    z0 = case["reference_design"]
    metrics = evaluate_design(case, z0, "reference", "none")
    target_cost = case["calibration"]["cost_reference_operating_ratio"] * metrics["revenue"]
    fixed_target = 0.08 * target_cost
    variable_target = target_cost - fixed_target
    relative = {"G": 1.00, "D": 0.82, "K": 0.65}
    fixed_weight = {"G": 1.00, "D": 0.75, "K": 0.50}
    active = case["calibration"]["reference_products"]
    length = case["network"]["corridor_length_km"]
    raw_variable = sum(
        sum(z0["N"][product].values()) * relative[product] * (length + 50.0)
        for product in active
    )
    if raw_variable <= 0 or target_cost <= 0:
        raise ValueError("Reference design has no positive rail operation/revenue for cost calibration")
    variable_scale = variable_target / raw_variable
    fixed_scale = fixed_target / sum(fixed_weight[product] for product in active)
    case["costs"] = {
        "fixed_per_product_day": {product: fixed_scale * fixed_weight[product] for product in PRODUCTS},
        "per_run": {product: variable_scale * relative[product] * 50.0 for product in PRODUCTS},
        "per_train_km": {product: variable_scale * relative[product] for product in PRODUCTS},
        "calibration_note": "Normalized to the configured reference operating ratio; not observed accounting cost.",
    }
    return evaluate_design(case, z0, "reference", "none")


def build(config: dict[str, Any], data_dir: Path, output_dir: Path) -> dict[str, Any]:
    case, allocation_audit, demand_audit = make_base_case(config, data_dir)
    constant_steps = calibrate_constants(case)
    pre_cost = evaluate_design(case, case["reference_design"], "reference", "none")
    demand_rescale = 1.0
    if pre_cost["max_load_factor"] > 0.92:
        demand_rescale = 0.92 / pre_cost["max_load_factor"]
        for segment in case["demand_segments"]:
            segment["qbar"] *= demand_rescale
            segment["target_reference_trips"] *= demand_rescale
    case["calibration"]["demand_capacity_rescale"] = demand_rescale
    final_reference = calibrate_costs(case)
    output_dir.mkdir(parents=True, exist_ok=True)
    case_path = output_dir / "aligned_case.json"
    summary_path = output_dir / "calibration_summary.json"
    demand_path = data_paths(config, data_dir)["demand_estimate"]
    assumptions_path = data_paths(config, data_dir)["demand_assumptions"]
    write_csv(demand_path, demand_audit)
    save_json(
        assumptions_path,
        {
            "method": case["calibration"]["demand_method"],
            "status": case["meta"]["demand_data_status"],
            "load_factor": case["calibration"]["load_factor"],
            "target_rail_share": case["calibration"]["target_rail_share"],
            "reference_participation_target": case["calibration"]["reference_participation_target"],
            "capacity_rescale": demand_rescale,
        },
    )
    save_json(case_path, case)
    summary = {
        "case": str(case_path),
        "allocation_audit": allocation_audit,
        "constant_calibration": constant_steps,
        "demand_capacity_rescale": demand_rescale,
        "reference_metrics": final_reference,
        "demand_estimate_file": str(demand_path),
        "demand_assumptions_file": str(assumptions_path),
    }
    save_json(summary_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a calibrated TRA-V7 aligned case")
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    config, _ = load_config(args.config)
    summary = build(config, Path(args.data_dir).resolve(), Path(args.output_dir).resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
