"""Build corridor-independent pattern cases from aligned cases and train rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "solver"))

from case_registry import load_manifest, save_json  # noqa: E402
from pattern_case import build_pattern_case, pattern_summary  # noqa: E402


def build_one(
    aligned_case: Path, trains_csv: Path, output: Path,
    floor_ratio: float, expansion_factor: float,
) -> dict:
    case = build_pattern_case(
        aligned_case, trains_csv,
        existing_service_floor_ratio=floor_ratio,
        frequency_expansion_factor=expansion_factor,
    )
    save_json(output, case)
    return {
        "case_file": str(output.resolve()),
        "patterns": pattern_summary(case),
        "daily_floors": case["pattern_constraints"][
            "minimum_daily_departures_by_product"
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--case-ids", nargs="+")
    parser.add_argument("--aligned-case", type=Path)
    parser.add_argument("--trains-csv", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--existing-service-floor-ratio", type=float, default=0.05)
    parser.add_argument("--frequency-expansion-factor", type=float, default=1.50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reports = []
    if args.manifest:
        records = load_manifest(
            args.manifest, args.case_ids, require_case_files=False
        )
        for record in records:
            if record.aligned_case is None or record.trains_csv is None:
                raise ValueError(
                    f"Case {record.case_id!r} needs aligned_case and trains_csv to build"
                )
            report = build_one(
                record.aligned_case, record.trains_csv, record.case_file,
                args.existing_service_floor_ratio,
                args.frequency_expansion_factor,
            )
            report["case_id"] = record.case_id
            reports.append(report)
            print(f"{record.case_id}: built {len(report['patterns'])} patterns")
    else:
        if not (args.aligned_case and args.trains_csv and args.output):
            raise ValueError(
                "Use --manifest, or supply --aligned-case, --trains-csv and --output"
            )
        report = build_one(
            args.aligned_case.resolve(), args.trains_csv.resolve(),
            args.output.resolve(), args.existing_service_floor_ratio,
            args.frequency_expansion_factor,
        )
        report["case_id"] = args.output.stem
        reports.append(report)
    print(json.dumps({"built": len(reports), "cases": reports}, ensure_ascii=False))


if __name__ == "__main__":
    main()
