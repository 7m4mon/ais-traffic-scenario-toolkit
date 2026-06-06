from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .aivdm_decode import AivdmFragmentAssembler, decode_position_report

SENTENCE_RE = re.compile(r"([!$]AI(?:VDM|VDO),.*?\*[0-9A-Fa-f]{2})")
META_RE = re.compile(r"\((.*)\)\s*$")


@dataclass
class ParsedAivdmLine:
    raw_aivdm: str
    metadata: dict[str, str]
    timestamp_utc: datetime | None
    message_type: int | None
    mmsi: int | None
    lat: float | None
    lon: float | None
    sog_kn: float | None
    cog_deg: float | None
    heading_deg: float | None
    name: str | None
    rx_signalpower_db: float | None
    rx_ppm: float | None
    rx_timestamp_raw: str | None
    repeat: int | None = None
    ship_type: int | None = None


def parse_aiscatcher_line(
    line: str,
    *,
    ignore_checksum: bool = True,
    log_timezone: str = "UTC",
    assembler: AivdmFragmentAssembler | None = None,
) -> ParsedAivdmLine | None:
    match = SENTENCE_RE.search(line)
    if not match:
        return None
    raw = match.group(1)
    metadata = parse_metadata(line)
    timestamp_raw = metadata.get("timestamp")
    timestamp_utc = parse_aiscatcher_timestamp(timestamp_raw, log_timezone=log_timezone) if timestamp_raw else None
    rx_signalpower = _optional_float(metadata.get("signalpower"))
    rx_ppm = _optional_float(metadata.get("ppm"))
    bits = None
    local_assembler = assembler or AivdmFragmentAssembler(ignore_checksum=ignore_checksum)
    try:
        bits = local_assembler.add(raw)
    except ValueError:
        if not ignore_checksum:
            raise
    decoded = decode_position_report(bits) if bits else {}
    return ParsedAivdmLine(
        raw_aivdm=raw,
        metadata=metadata,
        timestamp_utc=timestamp_utc,
        message_type=_optional_int(metadata.get("MSG", decoded.get("message_type"))),
        mmsi=_optional_int(metadata.get("MMSI", decoded.get("mmsi"))),
        lat=decoded.get("lat"),
        lon=decoded.get("lon"),
        sog_kn=decoded.get("sog_kn"),
        cog_deg=decoded.get("cog_deg"),
        heading_deg=decoded.get("heading_deg"),
        name=decoded.get("name"),
        rx_signalpower_db=rx_signalpower,
        rx_ppm=rx_ppm,
        rx_timestamp_raw=timestamp_raw,
        repeat=_optional_int(decoded.get("repeat", metadata.get("REPEAT"))),
        ship_type=_optional_int(decoded.get("ship_type")),
    )


def parse_metadata(line: str) -> dict[str, str]:
    match = META_RE.search(line)
    if not match:
        return {}
    metadata: dict[str, str] = {}
    for item in match.group(1).split(","):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def parse_aiscatcher_timestamp(value: str, *, log_timezone: str = "UTC") -> datetime:
    dt = datetime.strptime(value, "%Y%m%d%H%M%S")
    if log_timezone.lower() == "utc":
        return dt.replace(tzinfo=timezone.utc)
    if log_timezone.lower() == "local":
        return dt.astimezone().astimezone(timezone.utc)
    return dt.replace(tzinfo=ZoneInfo(log_timezone)).astimezone(timezone.utc)


def _optional_float(value) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value) -> int | None:
    if value is None:
        return None
    return int(value)
