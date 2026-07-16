#!/usr/bin/env python3
"""Collect data and build the Catalan static dashboard."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from escola_karen.core import analyze_region, load_json, results_from_dicts
from escola_karen.dashboard import build_static_site, persist_dashboard_run


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-report",
        type=Path,
        help="Genera el web a partir d’un informe JSON existent, sense xarxa.",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    parser.add_argument("--now", help="Data ISO opcional per a proves reproduïbles.")
    args = parser.parse_args()

    config = load_json(ROOT / "config.json", {})
    state_path = ROOT / "dashboard" / "state.json"
    old_state = load_json(state_path, {"documents": {}})
    now = datetime.fromisoformat(args.now) if args.now else datetime.now().astimezone()

    if args.from_report:
        source = load_json(args.from_report, {})
        results = results_from_dicts(source.get("regions", []))
        if source.get("generated_at") and not args.now:
            now = datetime.fromisoformat(source["generated_at"])
    else:
        results = [
            analyze_region(name, url, old_state)
            for name, url in config["regions"].items()
        ]

    public_data = ROOT / "dashboard" / "public" / "data"
    report = persist_dashboard_run(
        results,
        set(config["specialties_of_interest"]),
        now,
        public_data,
        state_path,
    )
    build_static_site(ROOT / "dashboard", public_data, args.output)
    print(
        f"Dashboard generat a {args.output} — estat: {report['status']} — "
        f"{report['summary']['offers_count']} ofertes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
