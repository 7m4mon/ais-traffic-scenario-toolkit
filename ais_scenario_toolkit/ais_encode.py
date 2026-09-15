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


def encode_message_21_bits(
    *,
    mmsi: int,
    name: str,
    lat: float,
    lon: float,
    aid_type: int = 0,
    virtual: bool = False,
    off_position: bool = False,
    timestamp: datetime | None = None,
    repeat: int = 0,
) -> str:
    """Encode an AIS Aid-to-Navigation report (ITU-R M.1371 message 21)."""
    return "".join(
        [
            uint_bits(21, 6),
            uint_bits(repeat, 2),
            uint_bits(mmsi, 30),
            uint_bits(aid_type, 5),
            ais_text_bits(name, 20),
            uint_bits(1, 1),
            int_bits(lon_to_ais(lon), 28),
            int_bits(lat_to_ais(lat), 27),
            uint_bits(0, 9),
            uint_bits(0, 9),
            uint_bits(0, 6),
            uint_bits(0, 6),
            uint_bits(0, 4),
            uint_bits(_second(timestamp), 6),
            uint_bits(int(off_position), 1),
            uint_bits(0, 8),
            uint_bits(0, 1),
            uint_bits(int(virtual), 1),
            uint_bits(0, 1),
            uint_bits(0, 1),
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


def encode_safety_message_bits(
    *, message_type: int, mmsi: int, text: str,
    destination_mmsi: int | None = None, sequence_number: int = 0,
) -> str:
    """Encode ITU-R M.1371 safety text (12 addressed, 14 broadcast)."""
    if message_type not in (12, 14):
        raise ValueError("Safety message_type must be 12 or 14")
    if not 1 <= mmsi <= 999999999:
        raise ValueError("Source MMSI must be 1..999999999")
    # Reject unsupported characters rather than silently corrupting safety text.
    if not isinstance(text, str) or not text.isascii():
        raise ValueError("Safety text must use AIS ASCII characters")
    text = text.upper()
    limit = 156 if message_type == 12 else 161
    if not text.strip() or len(text) > limit or any(ch not in AIS_TEXT for ch in text):
        raise ValueError(f"Safety text must contain 1..{limit} AIS ASCII characters")
    header = uint_bits(message_type, 6) + uint_bits(0, 2) + uint_bits(mmsi, 30)
    if message_type == 12:
        if destination_mmsi is None or not 1 <= destination_mmsi <= 999999999:
            raise ValueError("Message 12 requires destination_mmsi in 1..999999999")
        header += uint_bits(sequence_number, 2) + uint_bits(destination_mmsi, 30) + "00"
    else:
        if destination_mmsi is not None or sequence_number != 0:
            raise ValueError("Message 14 has no destination or sequence number")
        header += "00"
    bits = header + ais_text_bits(text, len(text))
    # ITU-R M.1371 Annex 2, message structure: unused bits in the final
    # octet are zero. This is separate from NMEA's six-bit armoring fill.
    return bits + "0" * ((-len(bits)) % 8)


def payload_bits_to_aivdm_sentences(bits: str, channel: str = "A") -> list[str]:
    """Fragment long payloads; each sentence stays within the NMEA length limit.

    Fragments must be sent consecutively (the player does this); sequence ID 0
    may therefore be reused for each complete multipart message.
    """
    fill = (-len(bits)) % 6
    padded = bits + "0" * fill
    payload = "".join(sixbit_to_payload_char(int(padded[i:i + 6], 2)) for i in range(0, len(padded), 6))
    chunks = [payload[i:i + 60] for i in range(0, len(payload), 60)]
    total = len(chunks)
    sequence = "0" if total > 1 else ""
    return [
        nmea_sentence(f"AIVDM,{total},{i},{sequence},{channel},{chunk},{fill if i == total else 0}", prefix="!")
        for i, chunk in enumerate(chunks, 1)
    ]


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
