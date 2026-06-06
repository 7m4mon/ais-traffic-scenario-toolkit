from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ais_scenario_toolkit.compiler import compile_scenario, load_scenario
from ais_scenario_toolkit.io import write_timeline_csv, write_timeline_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile scenario JSON to timeline JSONL/CSV.")
    parser.add_argument("--scenario", required=True, help="Input scenario JSON")
    parser.add_argument("--output", required=True, help="Output timeline JSONL")
    parser.add_argument("--csv", help="Optional output timeline CSV")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    records = compile_scenario(scenario)
    write_timeline_jsonl(records, args.output)
    if args.csv:
        write_timeline_csv(records, args.csv)
    print(f"Wrote {len(records)} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
