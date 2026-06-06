from __future__ import annotations

import math
from datetime import datetime, timezone

from .nmea import nmea_sentence

AIS_TEXT = "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./0123456789:;<=>?"


def uint_bits(value: int, width: int) -> str:
    if value < 0 or value >= (1 << width):
        raise ValueError(f"{value} does not fit in {width} unsigned bits")
    return f"{value:0{width}b}"


def int_bits(value: int, width: int) -> str:
    if value < 0:
        value = (1 << width) + value
    if value < 0 or value >= (1 << width):
        raise ValueError(f"signed value does not fit in {width} bits")
    return f"{value:0{width}b}"


def ais_text_bits(text: str, width_chars: int) -> str:
    padded = text.upper()[:width_chars].ljust(width_chars, "@")
    return "".join(uint_bits(AIS_TEXT.find(ch) if ch in AIS_TEXT else 32, 6) for ch in padded)


def lon_to_ais(lon: float | None) -> int:
    if lon is None:
        return 0x6791AC0
    return int(round(lon * 600000.0))


def lat_to_ais(lat: float | None) -> int:
    if lat is None:
        return 0x3412140
    return int(round(lat * 600000.0))


def speed_to_ais(speed_kn: float | None) -> int:
    if speed_kn is None or math.isnan(speed_kn):
        return 1023
    return max(0, min(1022, int(round(speed_kn * 10.0))))


def cog_to_ais(cog_deg: float | None) -> int:
    if cog_deg is None or math.isnan(cog_deg):
        return 3600
    return max(0, min(3599, int(round((cog_deg % 360.0) * 10.0))))


def heading_to_ais(heading_deg: float | None) -> int:
    if heading_deg is None or math.isnan(heading_deg):
        return 511
    return max(0, min(359, int(round(heading_deg % 360.0))))


def encode_message_1_bits(
    *,
    mmsi: int,
    lat: float,
    lon: float,
    sog_kn: float,
    cog_deg: float,
    heading_deg: float | None = None,
    timestamp: datetime | None = None,
    repeat: int = 0,
) -> str:
    second = _second(timestamp)
    return "".join(
        [
            uint_bits(1, 6),
            uint_bits(repeat, 2),
            uint_bits(mmsi, 30),
            uint_bits(0, 4),
            uint_bits(128, 8),
            uint_bits(speed_to_ais(sog_kn), 10),
            uint_bits(0, 1),
            int_bits(lon_to_ais(lon), 28),
            int_bits(lat_to_ais(lat), 27),
            uint_bits(cog_to_ais(cog_deg), 12),
            uint_bits(heading_to_ais(heading_deg), 9),
            uint_bits(second, 6),
            uint_bits(0, 2),
            uint_bits(0, 3),
            uint_bits(0, 1),
            uint_bits(0, 19),
        ]
    )


def encode_message_18_bits(
    *,
    mmsi: int,
    lat: float,
    lon: float,
    sog_kn: float,
    cog_deg: float,
    heading_deg: float | None = None,
    timestamp: datetime | None = None,
    repeat: int = 0,
) -> str:
    second = _second(timestamp)
    return "".join(
        [
            uint_bits(18, 6),
            uint_bits(repeat, 2),
            uint_bits(mmsi, 30),
            uint_bits(0, 8),
            uint_bits(speed_to_ais(sog_kn), 10),
            uint_bits(0, 1),
            int_bits(lon_to_ais(lon), 28),
            int_bits(lat_to_ais(lat), 27),
            uint_bits(cog_to_ais(cog_deg), 12),
            uint_bits(heading_to_ais(heading_deg), 9),
            uint_bits(second, 6),
            uint_bits(0, 2),
            uint_bits(1, 1),
            uint_bits(0, 1),
            uint_bits(0, 1),
            uint_bits(1, 1),
            uint_bits(0, 1),
            uint_bits(0, 1),
            uint_bits(0, 1),
            uint_bits(0, 20),
        ]
    )


def encode_message_24a_bits(*, mmsi: int, name: str, repeat: int = 0) -> str:
    return "".join([uint_bits(24, 6), uint_bits(repeat, 2), uint_bits(mmsi, 30), uint_bits(0, 2), ais_text_bits(name, 20)])


def encode_message_24b_bits(*, mmsi: int, ship_type: int = 60, callsign: str = "", repeat: int = 0) -> str:
    return "".join(
        [
            uint_bits(24, 6),
            uint_bits(repeat, 2),
            uint_bits(mmsi, 30),
            uint_bits(1, 2),
            uint_bits(ship_type, 8),
            ais_text_bits("", 7),
            ais_text_bits(callsign, 7),
            uint_bits(0, 9),
            uint_bits(0, 9),
            uint_bits(0, 6),
            uint_bits(0, 6),
            uint_bits(0, 6),
        ]
    )


def encode_position_bits(message_type: int, **kwargs) -> str:
    if message_type == 1:
        return encode_message_1_bits(**kwargs)
    if message_type == 18:
        return encode_message_18_bits(**kwargs)
    raise ValueError(f"Unsupported synthetic AIS position message type: {message_type}")


def payload_bits_to_aivdm(bits: str, channel: str = "A", talker: str = "AIVDM") -> str:
    fill_bits = (6 - (len(bits) % 6)) % 6
    padded = bits + ("0" * fill_bits)
    payload = "".join(sixbit_to_payload_char(int(padded[i : i + 6], 2)) for i in range(0, len(padded), 6))
    return nmea_sentence(f"{talker},1,1,,{channel},{payload},{fill_bits}", prefix="!")


def sixbit_to_payload_char(value: int) -> str:
    if not 0 <= value <= 63:
        raise ValueError("AIS sixbit value must be 0..63")
    return chr(value + 48 if value < 40 else value + 56)


def _second(timestamp: datetime | None) -> int:
    if timestamp is None:
        return 60
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc)
    return timestamp.second
