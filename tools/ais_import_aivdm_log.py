from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ais_scenario_toolkit.io import write_timeline_csv, write_timeline_jsonl
from ais_scenario_toolkit.log_importer import import_aivdm_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Import AIS-Catcher AIVDM console log to timeline JSONL/CSV.")
    parser.add_argument("--input", required=True, help="Input AIS-Catcher log")
    parser.add_argument("--output", required=True, help="Output timeline JSONL")
    parser.add_argument("--csv", help="Optional output timeline CSV")
    parser.add_argument("--origin-lat", type=float)
    parser.add_argument("--origin-lon", type=float)
    parser.add_argument("--own-mmsi", type=int)
    parser.add_argument("--own-source", choices=["none", "synthetic", "nmea-log"], default="none")
    parser.add_argument("--own-heading", type=float, default=0.0)
    parser.add_argument("--own-speed", type=float, default=0.0)
    parser.add_argument("--ignore-checksum", action="store_true")
    parser.add_argument("--log-timezone", default="UTC")
    args = parser.parse_args()

    if args.own_source == "nmea-log":
        parser.error("--own-source nmea-log is reserved for future NMEA own-ship log import")
    records = import_aivdm_log(
        args.input,
        origin_lat=args.origin_lat,
        origin_lon=args.origin_lon,
        own_mmsi=args.own_mmsi,
        own_source=args.own_source,
        own_heading_deg=args.own_heading,
        own_speed_kn=args.own_speed,
        ignore_checksum=args.ignore_checksum,
        log_timezone=args.log_timezone,
    )
    write_timeline_jsonl(records, args.output)
    if args.csv:
        write_timeline_csv(records, args.csv)
    print(f"Wrote {len(records)} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
