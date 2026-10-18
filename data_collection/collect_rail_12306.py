"""Collect timetable and fare observations from the bundled 12306 client."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from corridor_common import (
    city_specs,
    data_paths,
    load_config,
    od_pairs,
    query_date,
    save_json,
    write_csv,
)


ROOT = Path(__file__).resolve().parent
VENDOR_SRC = ROOT / "vendor" / "mcp-server-12306" / "src"


def parse_result(result_list: Any) -> dict[str, Any]:
    if not result_list:
        return {"success": False, "error": "empty response"}
    first = result_list[0] if isinstance(result_list, list) else result_list
    text = first.get("text", "{}") if isinstance(first, dict) else getattr(first, "text", "{}")
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return {"success": False, "error": "12306 response was not valid JSON", "raw": str(text)}


def rail_query_name(specs: dict[str, dict[str, Any]], city: str) -> str:
    return str(specs[city].get("rail_query", city))


async def collect(config: dict[str, Any], output_dir: Path, travel_date: str, delay: float) -> dict[str, Any]:
    if not VENDOR_SRC.exists():
        raise FileNotFoundError(f"Bundled 12306 source is missing: {VENDOR_SRC}")
    sys.path.insert(0, str(VENDOR_SRC))
    from mcp_12306.services.ticket_service import (  # noqa: PLC0415
        query_ticket_price_validated,
        query_tickets_validated,
        station_service,
    )

    specs = city_specs(config)
    pairs = od_pairs(config)
    print(f"12306 query date: {travel_date}; OD pairs: {len(pairs)}")
    await station_service.load_stations()
    trains: list[dict[str, Any]] = []
    prices: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, (origin, destination) in enumerate(pairs, 1):
        args = {
            "from_station": rail_query_name(specs, origin),
            "to_station": rail_query_name(specs, destination),
            "train_date": travel_date,
        }
        print(f"[{index}/{len(pairs)}] trains {origin} -> {destination}")
        try:
            payload = parse_result(await query_tickets_validated(args))
            if not payload.get("success"):
                raise RuntimeError(str(payload.get("error", "unknown 12306 error")))
            items = payload.get("trains", [])
            for item in items:
                row = dict(item)
                row["od_origin"] = origin
                row["od_dest"] = destination
                trains.append(row)
            print(f"  {len(items)} timetable records")
        except Exception as exc:  # network/API errors must be retained in the manifest
            errors.append({"stage": "trains", "origin": origin, "destination": destination, "error": str(exc)})
            print(f"  failed: {exc}")
        if delay and index < len(pairs):
            await asyncio.sleep(delay)

    for index, (origin, destination) in enumerate(pairs, 1):
        args = {
            "from_station": rail_query_name(specs, origin),
            "to_station": rail_query_name(specs, destination),
            "train_date": travel_date,
        }
        print(f"[{index}/{len(pairs)}] fares  {origin} -> {destination}")
        try:
            payload = parse_result(await query_ticket_price_validated(args))
            if not payload.get("success"):
                raise RuntimeError(str(payload.get("error", "unknown 12306 fare error")))
            items = payload.get("data", [])
            if not isinstance(items, list):
                raise RuntimeError("12306 fare response did not contain a list")
            for item in items:
                row = dict(item)
                row["od_origin"] = origin
                row["od_dest"] = destination
                row.update(row.pop("prices", {}) or {})
                prices.append(row)
            print(f"  {len(items)} fare records")
        except Exception as exc:
            errors.append({"stage": "prices", "origin": origin, "destination": destination, "error": str(exc)})
            print(f"  failed: {exc}")
        if delay and index < len(pairs):
            await asyncio.sleep(delay)

    if not trains:
        raise RuntimeError("No 12306 timetable records were collected; inspect network/date/city names")
    if not prices:
        raise RuntimeError("No 12306 fare records were collected; an aligned case cannot be built")

    paths = data_paths(config, output_dir, travel_date)
    ticket_fields = [
        "od_origin", "od_dest", "train_no", "from_station", "from_station_code",
        "to_station", "to_station_code", "start_time", "arrive_time", "duration",
        "business", "first_class", "second_class", "soft_sleeper", "hard_sleeper",
        "hard_seat", "soft_seat", "no_seat", "dongwo", "advanced_soft_sleeper",
    ]
    flat_trains = []
    for item in trains:
        row = dict(item)
        row.update(row.pop("seats", {}) or {})
        flat_trains.append(row)
    write_csv(paths["trains"], flat_trains, ticket_fields)
    write_csv(paths["prices"], prices)
    raw = {
        "case_id": config["case_id"],
        "date": travel_date,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": "https://kyfw.12306.cn/otn/leftTicketPrice/init",
        "od_pairs": pairs,
        "trains": trains,
        "prices": prices,
        "errors": errors,
    }
    save_json(paths["rail_raw"], raw)
    return {
        "trains_file": str(paths["trains"]),
        "prices_file": str(paths["prices"]),
        "raw_file": str(paths["rail_raw"]),
        "train_records": len(trains),
        "price_records": len(prices),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Config-driven 12306 corridor collector")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD; overrides config")
    parser.add_argument("--delay", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config, _ = load_config(args.config)
    travel_date = query_date(config, args.date)
    delay = float(
        args.delay
        if args.delay is not None
        else config.get("collection", {}).get("request_delay_seconds", 2.0)
    )
    if args.dry_run:
        print(json.dumps({"date": travel_date, "od_pairs": od_pairs(config)}, ensure_ascii=False, indent=2))
        return
    summary = asyncio.run(collect(config, Path(args.output_dir).resolve(), travel_date, delay))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
