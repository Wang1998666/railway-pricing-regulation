"""Collect Amap road/access data and derive passenger-road generalized costs."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from corridor_common import (
    city_names,
    city_specs,
    data_paths,
    load_config,
    load_csv,
    od_pairs,
    parse_location,
    save_json,
    write_csv,
)


GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
DRIVING_URL = "https://restapi.amap.com/v3/direction/driving"
WALKING_URL = "https://restapi.amap.com/v3/direction/walking"


def load_local_env() -> None:
    """Load local, untracked credentials without overriding process settings."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            os.environ.setdefault(name, value)


def fare(distance_km: float, duration_min: float, rule: dict[str, Any]) -> float:
    value = float(rule.get("base_fare", 0.0))
    value += max(0.0, distance_km - float(rule.get("base_distance_km", 0.0))) * float(rule.get("per_km", 0.0))
    value += duration_min * float(rule.get("per_min", 0.0))
    return round(max(value, float(rule.get("minimum_fare", 0.0))), 2)


def cost_rules(config: dict[str, Any]) -> dict[str, Any]:
    supplied = config.get("road_costs", {})
    defaults: dict[str, Any] = {
        "private_auto": {
            "fuel_per_km": 0.70,
            "depreciation_per_km": 0.15,
            "parking": 10.0,
        },
        "coach": {"per_km": 0.30, "booking_fee": 5.0},
        "maas": {
            "base_fare": 0.0,
            "base_distance_km": 0.0,
            "per_km": 0.50,
            "per_min": 0.10,
            "minimum_fare": 25.0,
        },
        "business_van": {
            "base_fare": 0.0,
            "base_distance_km": 0.0,
            "per_km": 2.20,
            "per_min": 0.40,
            "minimum_fare": 50.0,
        },
        "station_access": {
            "base_fare": 13.0,
            "base_distance_km": 3.0,
            "per_km": 1.80,
            "per_min": 0.35,
            "minimum_fare": 13.0,
        },
    }
    for key, value in supplied.items():
        if isinstance(value, dict) and key in defaults:
            defaults[key].update(value)
        else:
            defaults[key] = value
    return defaults


def derive_cost_files(config: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    paths = data_paths(config, data_dir)
    road_rows = load_csv(paths["amap_od"])
    access_rows = load_csv(paths["amap_access"])
    rules = cost_rules(config)
    passenger_rows = []
    for row in road_rows:
        distance = float(row["distance_km"])
        duration = float(row["duration_min"])
        tolls = float(row.get("tolls_yuan") or 0.0)
        auto = rules["private_auto"]
        private_cost = (
            (float(auto["fuel_per_km"]) + float(auto.get("depreciation_per_km", 0.0))) * distance
            + tolls
            + float(auto.get("parking", 0.0))
        )
        passenger_rows.append(
            {
                "origin": row["origin"],
                "destination": row["destination"],
                "distance_km": round(distance, 3),
                "duration_min": round(duration, 3),
                "coach_duration_min": round(float(row.get("coach_duration_min") or duration * 1.30), 3),
                "tolls_yuan": round(tolls, 2),
                "private_auto_cost": round(private_cost, 2),
                "coach_fare": round(float(rules["coach"]["per_km"]) * distance + float(rules["coach"].get("booking_fee", 0.0)), 2),
                "maas_fare": fare(distance, duration, rules["maas"]),
                "business_van_fare": fare(distance, duration, rules["business_van"]),
            }
        )
    access_fares = []
    for row in access_rows:
        distance = float(row.get("drive_distance_km") or 0.0)
        duration = float(row.get("drive_duration_min") or 0.0)
        access_fares.append(
            {
                "city": row["city"],
                "station": row["station"],
                "distance_km": round(distance, 3),
                "duration_min": round(duration, 3),
                "access_fare": fare(distance, duration, rules["station_access"]),
            }
        )
    write_csv(paths["road_passenger"], passenger_rows)
    write_csv(paths["access_fares"], access_fares)
    save_json(data_dir / f"{config['case_id']}_road_cost_rules.json", rules)
    return {
        "road_passenger_file": str(paths["road_passenger"]),
        "access_fares_file": str(paths["access_fares"]),
        "road_od_records": len(passenger_rows),
        "access_records": len(access_fares),
    }


def discover_stations(config: dict[str, Any], data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    specs = city_specs(config)
    result: dict[str, list[dict[str, Any]]] = {name: [] for name in city_names(config)}
    for name, spec in specs.items():
        for station in spec.get("stations", []):
            if isinstance(station, str):
                result[name].append({"name": station})
            else:
                result[name].append(dict(station))
    if all(result.values()):
        return result
    train_path = data_paths(config, data_dir)["trains"]
    if not train_path.exists():
        missing = [city for city, stations in result.items() if not stations]
        raise FileNotFoundError(
            f"Stations are missing for {missing}; configure them or collect rail data first"
        )
    seen = {city: {str(item["name"]) for item in stations} for city, stations in result.items()}
    for row in load_csv(train_path):
        candidates = (
            (row.get("od_origin"), row.get("from_station")),
            (row.get("od_dest"), row.get("to_station")),
        )
        for city, station in candidates:
            if city in result and station and station not in seen[city]:
                result[city].append({"name": station})
                seen[city].add(station)
    return result


async def amap_get(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("status")) != "1":
        raise RuntimeError(f"Amap error {payload.get('infocode')}: {payload.get('info')}")
    return payload


async def geocode(client: httpx.AsyncClient, key: str, address: str, city: str | None = None) -> str:
    params: dict[str, Any] = {"key": key, "address": address}
    if city:
        params["city"] = city
    payload = await amap_get(client, GEOCODE_URL, params)
    geocodes = payload.get("geocodes", [])
    if not geocodes:
        raise RuntimeError(f"Amap could not geocode: {address}")
    return str(geocodes[0]["location"])


async def driving(client: httpx.AsyncClient, key: str, origin: str, destination: str) -> dict[str, float]:
    payload = await amap_get(
        client,
        DRIVING_URL,
        {"key": key, "origin": origin, "destination": destination, "strategy": 10, "extensions": "all"},
    )
    paths = payload.get("route", {}).get("paths", [])
    if not paths:
        raise RuntimeError("Amap driving response contained no path")
    path = paths[0]
    return {
        "distance_km": float(path.get("distance", 0.0)) / 1000.0,
        "duration_min": float(path.get("duration", 0.0)) / 60.0,
        "tolls_yuan": float(path.get("tolls") or 0.0),
        "toll_distance_km": float(path.get("toll_distance") or 0.0) / 1000.0,
    }


async def walking(client: httpx.AsyncClient, key: str, origin: str, destination: str) -> dict[str, float]:
    payload = await amap_get(client, WALKING_URL, {"key": key, "origin": origin, "destination": destination})
    paths = payload.get("route", {}).get("paths", [])
    if not paths:
        return {"walk_distance_km": 0.0, "walk_duration_min": 0.0}
    path = paths[0]
    return {
        "walk_distance_km": float(path.get("distance", 0.0)) / 1000.0,
        "walk_duration_min": float(path.get("duration", 0.0)) / 60.0,
    }


async def collect(config: dict[str, Any], data_dir: Path, key: str, delay: float) -> dict[str, Any]:
    specs = city_specs(config)
    stations = discover_stations(config, data_dir)
    timeout = float(config.get("collection", {}).get("timeout_seconds", 30.0))
    async with httpx.AsyncClient(timeout=timeout) as client:
        centers: dict[str, str] = {}
        for name in city_names(config):
            location = parse_location(specs[name].get("center"))
            centers[name] = location or await geocode(
                client,
                key,
                str(specs[name].get("geocode_query", f"{name}市政府")),
                str(specs[name].get("geocode_city", name)),
            )
            if delay:
                await asyncio.sleep(delay)
        station_locations: dict[str, dict[str, str]] = {city: {} for city in centers}
        for city, items in stations.items():
            for item in items:
                name = str(item["name"])
                location = parse_location(item.get("location"))
                station_locations[city][name] = location or await geocode(
                    client, key, str(item.get("geocode_query", f"{name}站")), city
                )
                if delay:
                    await asyncio.sleep(delay)

        road_rows = []
        raw_routes = []
        coach_factor = float(config.get("road_costs", {}).get("coach_time_factor", 1.30))
        for origin, destination in od_pairs(config):
            route = await driving(client, key, centers[origin], centers[destination])
            row = {
                "origin": origin,
                "destination": destination,
                **{key_name: round(value, 3) for key_name, value in route.items()},
                "coach_duration_min": round(route["duration_min"] * coach_factor, 3),
            }
            road_rows.append(row)
            raw_routes.append({"kind": "intercity", **row})
            print(f"road {origin} -> {destination}: {route['distance_km']:.1f} km")
            if delay:
                await asyncio.sleep(delay)

        access_rows = []
        for city, items in station_locations.items():
            for station, location in items.items():
                drive = await driving(client, key, centers[city], location)
                walk = await walking(client, key, centers[city], location)
                row = {
                    "city": city,
                    "station": station,
                    "drive_distance_km": round(drive["distance_km"], 3),
                    "drive_duration_min": round(drive["duration_min"], 3),
                    "walk_distance_km": round(walk["walk_distance_km"], 3),
                    "walk_duration_min": round(walk["walk_duration_min"], 3),
                }
                access_rows.append(row)
                raw_routes.append({"kind": "access", **row})
                if delay:
                    await asyncio.sleep(delay)

    paths = data_paths(config, data_dir)
    write_csv(paths["amap_od"], road_rows)
    write_csv(paths["amap_access"], access_rows)
    save_json(
        paths["road_raw"],
        {
            "case_id": config["case_id"],
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_url": "https://lbs.amap.com/api/webservice/guide/api/direction/",
            "city_centers": centers,
            "station_locations": station_locations,
            "routes": raw_routes,
        },
    )
    derived = derive_cost_files(config, data_dir)
    return {
        "amap_od_file": str(paths["amap_od"]),
        "amap_access_file": str(paths["amap_access"]),
        "raw_file": str(paths["road_raw"]),
        **derived,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Config-driven Amap road collector")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--derive-only", action="store_true", help="Use existing Amap CSVs; do not call the API")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=None)
    args = parser.parse_args()
    load_local_env()
    config, _ = load_config(args.config)
    data_dir = Path(args.output_dir).resolve()
    delay = float(
        args.delay
        if args.delay is not None
        else config.get("collection", {}).get("request_delay_seconds", 0.5)
    )
    if args.dry_run:
        stations = discover_stations(config, data_dir)
        print(json.dumps({"od_pairs": od_pairs(config), "stations": stations}, ensure_ascii=False, indent=2))
        return
    if args.derive_only:
        summary = derive_cost_files(config, data_dir)
    else:
        env_name = str(config.get("collection", {}).get("amap_key_env", "AMAP_API_KEY"))
        key = os.environ.get(env_name)
        if not key:
            raise SystemExit(f"Amap key is not set. Define environment variable {env_name}.")
        summary = asyncio.run(collect(config, data_dir, key, delay))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
