"""Manifest and path utilities for corridor-independent case execution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    label: str
    case_file: Path
    aligned_case: Path | None = None
    trains_csv: Path | None = None


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _resolve(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def load_manifest(
    manifest_path: str | Path,
    selected_ids: Iterable[str] | None = None,
    *,
    require_case_files: bool = True,
) -> list[CaseRecord]:
    manifest = Path(manifest_path).resolve()
    payload = load_json(manifest)
    entries = payload.get("cases")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Manifest must contain a non-empty 'cases' list")
    selected = set(selected_ids or [])
    records: list[CaseRecord] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Manifest case #{index} must be an object")
        case_id = str(entry.get("id", "")).strip()
        if not SAFE_ID.fullmatch(case_id):
            raise ValueError(
                f"Case id {case_id!r} must match {SAFE_ID.pattern}; "
                "use label for a human-readable or Chinese name"
            )
        if case_id in seen:
            raise ValueError(f"Duplicate case id: {case_id}")
        seen.add(case_id)
        if selected and case_id not in selected:
            continue
        case_file = _resolve(manifest.parent, entry.get("case_file"))
        if case_file is None:
            raise ValueError(f"Case {case_id!r} is missing case_file")
        aligned_case = _resolve(manifest.parent, entry.get("aligned_case"))
        trains_csv = _resolve(manifest.parent, entry.get("trains_csv"))
        if require_case_files and not case_file.is_file():
            raise FileNotFoundError(
                f"Case {case_id!r} not found: {case_file}. "
                "Run build_pattern_case.py first when aligned_case/trains_csv are used."
            )
        records.append(CaseRecord(
            case_id=case_id,
            label=str(entry.get("label") or case_id),
            case_file=case_file,
            aligned_case=aligned_case,
            trains_csv=trains_csv,
        ))
    if selected:
        missing = selected - {record.case_id for record in records}
        if missing:
            raise ValueError(f"Unknown selected case ids: {sorted(missing)}")
    if not records:
        raise ValueError("No cases selected")
    return records


def case_states(case: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    scenarios = case.get("scenarios", {})
    incomes = tuple(scenarios.get("income", {}))
    electrifications = tuple(scenarios.get("electrification", {}))
    if not incomes or not electrifications:
        raise ValueError("Case must define non-empty income and electrification scenarios")
    return incomes, electrifications


def reference_states(case: dict[str, Any]) -> tuple[str, str]:
    """Return input-declared baseline states, with first-key fallbacks."""
    incomes, electrifications = case_states(case)
    declared = case.get("reference_scenario", {})
    income = str(declared.get("income_state", incomes[0]))
    electric = str(
        declared.get("electrification_state", electrifications[0])
    )
    if income not in incomes:
        raise ValueError(
            f"reference_scenario.income_state {income!r} is not available"
        )
    if electric not in electrifications:
        raise ValueError(
            "reference_scenario.electrification_state "
            f"{electric!r} is not available"
        )
    return income, electric


def select_states(
    available: Iterable[str], requested: Iterable[str] | None, dimension: str
) -> tuple[str, ...]:
    options = tuple(available)
    if requested is None:
        return options
    chosen = tuple(dict.fromkeys(requested))
    missing = sorted(set(chosen) - set(options))
    if missing:
        raise ValueError(
            f"Unknown {dimension} states {missing}; available states are {list(options)}"
        )
    return chosen
