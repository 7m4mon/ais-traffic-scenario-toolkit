from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ais_scenario_toolkit.exporters import (
    DryRunExporter,
    SerialExporter,
    TcpServerExporter,
    UdpExporter,
    WebSocketTextExporter,
    parse_host_port,
)
from ais_scenario_toolkit.io import read_timeline_jsonl
from ais_scenario_toolkit.player import play_timeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay timeline to NMEA/AIVDM/bit-string outputs.")
    parser.add_argument("timeline_pos", nargs="?", help="Timeline JSONL, positional alias")
    parser.add_argument("--timeline", help="Timeline JSONL")
    parser.add_argument("--nmea-tcp-server", help="HOST:PORT mixed own NMEA + target AIVDM TCP server")
    parser.add_argument("--aivdm-tcp-server", help="HOST:PORT target AIVDM-only TCP server")
    parser.add_argument("--nmea-udp", help="HOST:PORT mixed own NMEA + target AIVDM UDP output")
    parser.add_argument("--own-nmea-serial", help="Serial port for own RMC/GGA/HDT only")
    parser.add_argument("--target-aivdm-serial", help="Serial port for target AIVDM only")
    parser.add_argument("--baud", type=int, default=4800)
    parser.add_argument("--bitstring-ws", help="ws:// URL for AIS payload bit strings")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--echo-output", action="store_true", help="Print each message as it is sent during replay")
    parser.add_argument("--replay-speed", type=float, default=1.0)
    parser.add_argument("--replay-mode", choices=["fixed-step", "original-timing"], default="fixed-step")
    parser.add_argument("--static-interval", type=int, default=60)
    args = parser.parse_args()

    timeline = args.timeline or args.timeline_pos
    if not timeline:
        parser.error("timeline path is required")
    records = read_timeline_jsonl(timeline)
    nmea_exporters = []
    own_nmea_exporters = []
    aivdm_exporters = []
    bitstring_exporters = []
    if args.nmea_tcp_server:
        nmea_exporters.append(TcpServerExporter(*parse_host_port(args.nmea_tcp_server)))
    if args.aivdm_tcp_server:
        aivdm_exporters.append(TcpServerExporter(*parse_host_port(args.aivdm_tcp_server)))
    if args.nmea_udp:
        nmea_exporters.append(UdpExporter(*parse_host_port(args.nmea_udp)))
    if args.own_nmea_serial:
        own_nmea_exporters.append(SerialExporter(args.own_nmea_serial, args.baud))
    if args.target_aivdm_serial:
        aivdm_exporters.append(SerialExporter(args.target_aivdm_serial, args.baud))
    if args.bitstring_ws:
        bitstring_exporters.append(WebSocketTextExporter(args.bitstring_ws))
    if args.dry_run or not (nmea_exporters or own_nmea_exporters or aivdm_exporters or bitstring_exporters):
        nmea_exporters.append(DryRunExporter())
        bitstring_exporters.append(DryRunExporter(prefix="BIT "))
    exporters = nmea_exporters + own_nmea_exporters + aivdm_exporters + bitstring_exporters
    try:
        play_timeline(
            records,
            nmea_exporters=nmea_exporters,
            own_nmea_exporters=own_nmea_exporters,
            aivdm_exporters=aivdm_exporters,
            bitstring_exporters=bitstring_exporters,
            replay_speed=args.replay_speed,
            replay_mode=args.replay_mode,
            static_interval=args.static_interval,
            echo_output=args.echo_output,
        )
    finally:
        for exporter in exporters:
            exporter.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
