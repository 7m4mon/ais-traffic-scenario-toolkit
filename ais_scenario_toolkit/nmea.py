from __future__ import annotations

from datetime import datetime, timezone


def nmea_checksum_body(body: str) -> str:
    checksum = 0
    for ch in body:
        checksum ^= ord(ch)
    return f"{checksum:02X}"


def nmea_sentence(talker_and_body: str, prefix: str = "$") -> str:
    return f"{prefix}{talker_and_body}*{nmea_checksum_body(talker_and_body)}"


def validate_nmea_checksum(sentence: str) -> bool:
    text = sentence.strip()
    if not text.startswith(("!", "$")) or "*" not in text:
        return False
    body, checksum = text[1:].split("*", 1)
    return nmea_checksum_body(body) == checksum[:2].upper()


def format_lat(lat: float) -> tuple[str, str]:
    hemi = "N" if lat >= 0 else "S"
    value = abs(lat)
    degrees = int(value)
    minutes = (value - degrees) * 60.0
    return f"{degrees:02d}{minutes:07.4f}", hemi


def format_lon(lon: float) -> tuple[str, str]:
    hemi = "E" if lon >= 0 else "W"
    value = abs(lon)
    degrees = int(value)
    minutes = (value - degrees) * 60.0
    return f"{degrees:03d}{minutes:07.4f}", hemi


def make_rmc(timestamp: datetime, lat: float, lon: float, sog_kn: float, cog_deg: float) -> str:
    timestamp = _as_utc(timestamp)
    lat_text, ns = format_lat(lat)
    lon_text, ew = format_lon(lon)
    body = (
        f"GPRMC,{timestamp:%H%M%S}.00,A,{lat_text},{ns},{lon_text},{ew},"
        f"{sog_kn:.1f},{cog_deg:.1f},{timestamp:%d%m%y},,,A"
    )
    return nmea_sentence(body)


def make_gga(timestamp: datetime, lat: float, lon: float, fix_quality: int = 1, satellites: int = 8) -> str:
    timestamp = _as_utc(timestamp)
    lat_text, ns = format_lat(lat)
    lon_text, ew = format_lon(lon)
    body = f"GPGGA,{timestamp:%H%M%S}.00,{lat_text},{ns},{lon_text},{ew},{fix_quality},{satellites:02d},1.0,0.0,M,0.0,M,,"
    return nmea_sentence(body)


def make_hdt(heading_deg: float) -> str:
    return nmea_sentence(f"GPHDT,{heading_deg:.1f},T")


def _as_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)
