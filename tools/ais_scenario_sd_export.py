from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ais_scenario_toolkit.io import read_timeline_jsonl
from ais_scenario_toolkit.sd_demo import HEADER, write_sd_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Export synchronized AIS and own GPS to SD demo.bin (AISDEMO2).")
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--name", help="OLED label (up to 23 ASCII characters)")
    parser.add_argument("--replay-speed", type=float, default=1.0)
    parser.add_argument("--static-interval", type=int, default=60)
    parser.add_argument("--channel", choices=("A", "B"), default="A", help="RF channel for all records")
    parser.add_argument("--ais-only", action="store_true", help="Exclude own-ship NMEA output")
    parser.add_argument("--start-utc", help="Synthetic GPS start time (ISO 8601 with timezone); default: export time")
    args = parser.parse_args()
    try:
        start = datetime.now(timezone.utc).replace(microsecond=0)
        if args.start_utc:
            start = datetime.fromisoformat(args.start_utc.replace("Z", "+00:00"))
            if start.tzinfo is None:
                raise ValueError("--start-utc needs Z or a timezone offset")
            start = start.astimezone(timezone.utc)
        data = write_sd_demo(
            read_timeline_jsonl(args.timeline), args.output,
            name=args.name or args.timeline.stem, replay_speed=args.replay_speed,
            static_interval=args.static_interval, channel=args.channel,
            include_own=not args.ais_only, start_timestamp=start,
        )
    except (OSError, ValueError, OverflowError) as exc:
        parser.exit(2, f"SD export failed: {exc}\n")
    _, period, count, _, _, _ = HEADER.unpack_from(data)
    print(f"{args.output}: {count} AIS/NMEA records, {len(data)} bytes, loop {period / 1000:g}s")
    print("Copy this file to the FAT16/FAT32 card root as demo.bin. Swap cards with power OFF.")
    if args.ais_only:
        print("Own-ship NMEA excluded (--ais-only).")
    else:
        print("Own RMC/GGA/HDT: USART3 TX PB10, 38400 baud, 8N1, via an RS-422 driver.")
    print("Stored GPS/AIS timestamps repeat on every loop; no real-time clock is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
