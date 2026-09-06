from __future__ import annotations

import math
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .ais_encode import (
    encode_message_21_bits,
    encode_message_24a_bits,
    encode_message_24b_bits,
    encode_position_bits,
    payload_bits_to_aivdm,
)
from .aivdm_decode import aivdm_to_payload_bits
from .exporters import Exporter
from .model import TimelineRecord
from .nmea import make_gga, make_hdt, make_rmc


def records_to_output(
    record: TimelineRecord,
    *,
    start_timestamp: datetime | None = None,
) -> tuple[list[str], list[str]]:
    timestamp = _record_timestamp(record, start_timestamp=start_timestamp)
    nmea_messages: list[str] = []
    bitstrings: list[str] = []
    if record.role == "own":
        if record.lat is None or record.lon is None:
            return [], []
        nmea_messages.extend(
            [
                make_rmc(timestamp, record.lat, record.lon, record.sog_kn or 0.0, record.cog_deg or 0.0),
                make_gga(timestamp, record.lat, record.lon),
                make_hdt(record.heading_deg if record.heading_deg is not None else record.cog_deg or 0.0),
            ]
        )
        return nmea_messages, bitstrings
    if record.raw_aivdm:
        nmea_messages.append(record.raw_aivdm)
        try:
            bitstrings.append(aivdm_to_payload_bits(record.raw_aivdm))
        except ValueError:
            pass
        return nmea_messages, bitstrings
    if record.lat is None or record.lon is None or record.mmsi is None:
        return [], []
    if record.message_type == 21:
        bits = encode_message_21_bits(
            mmsi=record.mmsi,
            name=record.name or "",
            lat=record.lat,
            lon=record.lon,
            aid_type=record.aton_type or 0,
            virtual=record.aton_virtual,
            off_position=record.aton_off_position,
            timestamp=timestamp,
        )
    else:
        bits = encode_position_bits(
            record.message_type or 18,
            mmsi=record.mmsi,
            lat=record.lat,
            lon=record.lon,
            sog_kn=record.sog_kn or 0.0,
            cog_deg=record.cog_deg or record.heading_deg or 0.0,
            heading_deg=record.heading_deg,
            timestamp=timestamp,
        )
    nmea_messages.append(payload_bits_to_aivdm(bits))
    bitstrings.append(bits)
    return nmea_messages, bitstrings


def play_timeline(
    records: list[TimelineRecord],
    *,
    nmea_exporters: list[Exporter] | None = None,
    own_nmea_exporters: list[Exporter] | None = None,
    aivdm_exporters: list[Exporter] | None = None,
    bitstring_exporters: list[Exporter] | None = None,
    replay_speed: float = 1.0,
    replay_mode: str = "fixed-step",
    static_interval: int = 60,
    start_timestamp: datetime | None = None,
    echo_output: bool = False,
) -> None:
    nmea_exporters = nmea_exporters or []
    own_nmea_exporters = own_nmea_exporters or []
    aivdm_exporters = aivdm_exporters or []
    bitstring_exporters = bitstring_exporters or []
    playback_start_timestamp = start_timestamp or datetime.now(timezone.utc)
    grouped: dict[float, list[TimelineRecord]] = defaultdict(list)
    for record in records:
        grouped[float(record.time_sec)].append(record)
    last_time: float | None = None
    for current_time in sorted(grouped):
        if last_time is not None:
            delay = max(0.0, current_time - last_time) / max(replay_speed, 1e-9)
            if replay_mode == "original-timing" or delay > 0:
                time.sleep(delay)
        last_time = current_time
        for record in grouped[current_time]:
            nmea_messages, bitstrings = records_to_output(record, start_timestamp=playback_start_timestamp)
            for msg in nmea_messages:
                if record.role == "own":
                    _send_all(own_nmea_exporters, msg)
                elif msg.startswith("!AI"):
                    _send_all(aivdm_exporters, msg)
                _send_all(nmea_exporters, msg)
                if echo_output:
                    _echo(current_time, record, "TX", msg)
            for bits in bitstrings:
                _send_all(bitstring_exporters, bits)
                if echo_output and bitstring_exporters:
                    _echo(current_time, record, "BIT", bits)
            if (
                record.role == "target"
                and record.message_type in (1, 18)
                and record.mmsi
                and not str(record.mmsi).startswith(("970", "972", "974"))
                and _should_emit_static(current_time, static_interval)
            ):
                _emit_static(record, aivdm_exporters, nmea_exporters, bitstring_exporters, current_time=current_time, echo_output=echo_output)


def _emit_static(
    record: TimelineRecord,
    aivdm_exporters: list[Exporter],
    nmea_exporters: list[Exporter],
    bitstring_exporters: list[Exporter],
    *,
    current_time: float,
    echo_output: bool,
) -> None:
    bits_items = [
        encode_message_24a_bits(mmsi=record.mmsi or 0, name=record.name or ""),
        encode_message_24b_bits(mmsi=record.mmsi or 0, ship_type=record.ship_type or 60),
    ]
    for bits in bits_items:
        msg = payload_bits_to_aivdm(bits)
        _send_all(aivdm_exporters, msg)
        _send_all(nmea_exporters, msg)
        _send_all(bitstring_exporters, bits)
        if echo_output:
            _echo(current_time, record, "TX", msg)
            if bitstring_exporters:
                _echo(current_time, record, "BIT", bits)


def _should_emit_static(time_sec: float, interval: int) -> bool:
    if interval <= 0:
        return False
    return math.isclose(time_sec % interval, 0.0, abs_tol=1e-6)


def _send_all(exporters: list[Exporter], message: str) -> None:
    for exporter in exporters:
        exporter.send(message)


def _echo(time_sec: float, record: TimelineRecord, kind: str, message: str) -> None:
    mmsi = record.mmsi if record.mmsi is not None else "-"
    print(f"[{time_sec:8.1f}s] {record.role:<6} {mmsi} {kind} {message}")


def _record_timestamp(record: TimelineRecord, *, start_timestamp: datetime | None = None) -> datetime:
    if isinstance(record.timestamp_utc, datetime):
        return record.timestamp_utc
    if isinstance(record.timestamp_utc, str) and record.timestamp_utc:
        text = record.timestamp_utc.replace("Z", "+00:00")
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    base = start_timestamp or datetime.now(timezone.utc)
    return base + timedelta(seconds=float(record.time_sec))
