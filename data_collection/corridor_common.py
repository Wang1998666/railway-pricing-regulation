"""Shared configuration and file helpers for rail--road corridor cases."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


PRODUCTS = ("G", "D", "K")


def load_config(path: str | Path) -> tuple[dict[str, Any], Path]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_config(config)
    return config, config_path


def validate_config(config: dict[str, Any]) -> None:
    missing = [key for key in ("case_id", "name", "cities") if key not in config]
    if missing:
        raise ValueError("Corridor config is missing: " + ", ".join(missing))
    case_id = str(config["case_id"])
    if not case_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in case_id):
        raise ValueError("case_id may contain only letters, digits, '_' and '-'")
    cities = config["cities"]
    if not isinstance(cities, list) or len(cities) < 2:
        raise ValueError("cities must contain at least two ordered city objects")
    names = [city_name(city) for city in cities]
    if len(set(names)) != len(names):
        raise ValueError("City names must be unique and ordered along the corridor")
    shares = config.get("demand", {}).get(
        "class_share", {"高收入": 0.25, "中收入": 0.50, "低收入": 0.25}
    )
    if not shares or abs(sum(float(value) for value in shares.values()) - 1.0) > 1e-8:
        raise ValueError("demand.class_share must sum to 1")


def city_name(city: str | dict[str, Any]) -> str:
    return city if isinstance(city, str) else str(city["name"])


def city_names(config: dict[str, Any]) -> list[str]:
    return [city_name(city) for city in config["cities"]]


def city_specs(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in config["cities"]:
        if isinstance(item, str):
            result[item] = {"name": item}
        else:
            result[str(item["name"])] = dict(item)
    return result


def query_date(config: dict[str, Any], override: str | None = None) -> str:
    return override or str(
        config.get("query_date")
        or (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    )


def date_tag(config: dict[str, Any], override: str | None = None) -> str:
    return query_date(config, override).replace("-", "")


def od_pairs(config: dict[str, Any], scope: str | None = None) -> list[tuple[str, str]]:
    names = city_names(config)
    selected = scope or str(config.get("od_scope", "forward"))
    if selected not in {"forward", "both", "endpoints"}:
        raise ValueError("od_scope must be 'forward', 'both', or 'endpoints'")
    if selected == "endpoints":
        if len(names) != 2:
            raise ValueError("od_scope='endpoints' is only valid for a two-city corridor")
        return [(names[0], names[-1])]
    forward = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    if selected == "forward":
        return forward
    return forward + [(destination, origin) for origin, destination in forward]


def forward_od_pairs(config: dict[str, Any]) -> list[tuple[str, str]]:
    names = city_names(config)
    return [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]


def adjacent_segments(config: dict[str, Any]) -> list[str]:
    names = city_names(config)
    return [f"{names[i]}-{names[i + 1]}" for i in range(len(names) - 1)]


def od_segment_map(config: dict[str, Any]) -> dict[str, list[str]]:
    names = city_names(config)
    result: dict[str, list[str]] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            result[f"{names[i]}-{names[j]}"] = [
                f"{names[k]}-{names[k + 1]}" for k in range(i, j)
            ]
    return result


def data_paths(config: dict[str, Any], data_dir: str | Path, date_override: str | None = None) -> dict[str, Path]:
    root = Path(data_dir).resolve()
    prefix = str(config["case_id"])
    tag = date_tag(config, date_override)
    overrides = config.get("input_files", {})
    defaults = {
        "trains": f"{prefix}_trains_{tag}.csv",
        "prices": f"{prefix}_prices_{tag}.csv",
        "rail_raw": f"{prefix}_rail_raw_{tag}.json",
        "amap_od": f"{prefix}_amap_od.csv",
        "amap_access": f"{prefix}_amap_access.csv",
        "road_raw": f"{prefix}_amap_raw.json",
        "road_passenger": f"{prefix}_road_passenger.csv",
        "access_fares": f"{prefix}_access_fares.csv",
        "demand_estimate": f"{prefix}_demand_estimate.csv",
        "demand_assumptions": f"{prefix}_demand_assumptions.json",
    }
    return {key: root / str(overrides.get(key, value)) for key, value in defaults.items()}


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    materialized = list(rows)
    if fieldnames is None:
        ordered: list[str] = []
        seen: set[str] = set()
        for row in materialized:
            for key in row:
                if key not in seen:
                    ordered.append(key)
                    seen.add(key)
        fieldnames = ordered
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)


def save_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def product_type(train_code: str) -> str:
    code = (train_code or "").upper()
    if code.startswith(("G", "C")):
        return "G"
    if code.startswith("D"):
        return "D"
    return "K"


def file_manifest(paths: Iterable[Path]) -> list[dict[str, Any]]:
    result = []
    for path in paths:
        result.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return result


def parse_location(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        parts = [str(value[0]), str(value[1])]
    else:
        raise ValueError(f"Invalid location value: {value!r}")
    if len(parts) != 2:
        raise ValueError(f"Location must be 'longitude,latitude': {value!r}")
    float(parts[0])
    float(parts[1])
    return f"{parts[0]},{parts[1]}"
