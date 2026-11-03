"""Compile synchronized target AIS and own-ship NMEA to AISDEMO2 SD replay."""
from __future__ import annotations

import math
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

from .ais_encode import encode_message_24a_bits, encode_message_24b_bits
from .aivdm_decode import parse_aivdm_sentence
from .model import TimelineRecord
from .player import _should_emit_static, records_to_output

MAGIC = b"AISDEMO2"
HEADER = struct.Struct("<8sIIII24s")
RECORD = struct.Struct("<IHBB")
MAX_PAYLOAD_BITS = 600
MAX_NMEA_BYTES = 80  # 82-byte sentence limit including the appended CR/LF.
MAX_LOOP_MS = 86_400_000


def compile_sd_demo(
    records: list[TimelineRecord], *, name: str = "AIS DEMO",
    replay_speed: float = 1.0, static_interval: int = 60, channel: str = "A",
    include_own: bool = True, start_timestamp: datetime | None = None,
) -> bytes:
    """Keep target traffic, static reports and timed own RMC/GGA/HDT.

    AIS bit fields are packed MSB first. Trailing spare zero bits bring short
    non-octet-aligned messages (e.g. safety text) to an octet boundary, as
    required by the current transmitter's HDLC builder. Long messages are
    rejected instead of silently truncating them.
    """
    if not math.isfinite(replay_speed) or replay_speed <= 0:
        raise ValueError("replay_speed must be finite and positive")
    if channel not in ("A", "B"):
        raise ValueError("channel must be A or B")
    if not records:
        raise ValueError("Timeline is empty")
    times = [float(record.time_sec) for record in records]
    if any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError("Timeline times must be finite and nonnegative")
    period_float = (max(times) + 1.0) * 1000 / replay_speed
    if not math.isfinite(period_float) or period_float > MAX_LOOP_MS:
        raise ValueError("Loop duration must be at most 24 hours")
    loop_ms = max(1, math.ceil(period_float))
    # Reproducible relative AIS seconds; the board has no real-time clock.
    epoch = start_timestamp or datetime(2000, 1, 1, tzinfo=timezone.utc)
    body = bytearray()
    count = 0
    for record in sorted(records, key=lambda r: (float(r.time_sec), r.role != "own")):
        at_ms = min(loop_ms - 1, round(float(record.time_sec) * 1000 / replay_speed))
        if record.role == "own":
            if include_own:
                messages, _ = records_to_output(record, start_timestamp=epoch)
                for message in messages:
                    payload = message.encode("ascii")
                    if not 8 <= len(payload) <= MAX_NMEA_BYTES:
                        raise ValueError(f"Own NMEA sentence exceeds {MAX_NMEA_BYTES} bytes")
                    body += RECORD.pack(at_ms, len(payload) * 8, ord("-"), 1)
                    body += payload
                    count += 1
            continue
        if record.raw_aivdm:
            parsed = parse_aivdm_sentence(record.raw_aivdm, ignore_checksum=True)
            if parsed.total != 1 or parsed.number != 1:
                raise ValueError("Raw multipart/invalid AIVDM is unsupported; reassemble it before export")
        _, payloads = records_to_output(record, start_timestamp=epoch)
        if record.raw_aivdm and not payloads:
            raise ValueError("Raw multipart/invalid AIVDM is unsupported; reassemble it before export")
        if (
            record.role == "target" and record.message_type in (1, 18)
            and record.mmsi and not str(record.mmsi).startswith(("970", "972", "974"))
            and _should_emit_static(record.time_sec, static_interval)
        ):
            payloads += [
                encode_message_24a_bits(mmsi=record.mmsi, name=record.name or ""),
                encode_message_24b_bits(mmsi=record.mmsi, ship_type=record.ship_type or 60),
            ]
        for bits in payloads:
            bits = bits.ljust((len(bits) + 7) // 8 * 8, "0")
            if not 40 <= len(bits) <= MAX_PAYLOAD_BITS or set(bits) - {"0", "1"}:
                raise ValueError(
                    f"At {record.time_sec}s: AIS payload must fit in {MAX_PAYLOAD_BITS} bits "
                    f"(got {len(bits)}); shorten safety text or use a shorter message"
                )
            body += RECORD.pack(at_ms, len(bits), ord(channel), 0)
            body += int(bits, 2).to_bytes(len(bits) // 8, "big")
            count += 1
    if not count:
        raise ValueError("Timeline contains no playable AIS/NMEA messages")
    if count > 0xFFFFFFFF or len(body) > 0xFFFFFFFF - HEADER.size:
        raise ValueError("Demo is too large for the file format")
    label = name.encode("ascii", errors="replace")[:23].ljust(24, b"\0")
    return HEADER.pack(MAGIC, loop_ms, count, len(body), zlib.crc32(body), label) + body


def write_sd_demo(records: list[TimelineRecord], path: str | Path, **options) -> bytes:
    data = compile_sd_demo(records, **options)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return data
