from __future__ import annotations

from dataclasses import dataclass

from .ais_encode import AIS_TEXT
from .nmea import validate_nmea_checksum


def ais_payload_char_to_sixbit(ch: str) -> int:
    v = ord(ch) - 48
    if v > 40:
        v -= 8
    if not 0 <= v <= 63:
        raise ValueError(f"Invalid AIS payload character: {ch!r}")
    return v


def aivdm_to_payload_bits(sentence: str) -> str:
    body = sentence.strip()
    if body.startswith(("!", "$")):
        body = body[1:]
    body = body.split("*", 1)[0]
    fields = body.split(",")
    if len(fields) < 7:
        raise ValueError("AIVDM sentence has too few fields")
    payload = fields[5]
    fill_bits = int(fields[6])
    bits = "".join(f"{ais_payload_char_to_sixbit(ch):06b}" for ch in payload)
    if fill_bits:
        bits = bits[:-fill_bits]
    return bits


@dataclass
class AivdmSentence:
    total: int
    number: int
    sequential_id: str
    channel: str
    payload: str
    fill_bits: int


class AivdmFragmentAssembler:
    def __init__(self, *, ignore_checksum: bool = False) -> None:
        self.ignore_checksum = ignore_checksum
        self._fragments: dict[tuple[str, str], dict[int, AivdmSentence]] = {}

    def add(self, sentence: str) -> str | None:
        parsed = parse_aivdm_sentence(sentence, ignore_checksum=self.ignore_checksum)
        if parsed.total == 1:
            return aivdm_to_payload_bits(sentence)
        key = (parsed.sequential_id, parsed.channel)
        fragments = self._fragments.setdefault(key, {})
        fragments[parsed.number] = parsed
        if len(fragments) < parsed.total:
            return None
        payload = "".join(fragments[index].payload for index in range(1, parsed.total + 1))
        fill_bits = fragments[parsed.total].fill_bits
        del self._fragments[key]
        bits = "".join(f"{ais_payload_char_to_sixbit(ch):06b}" for ch in payload)
        if fill_bits:
            bits = bits[:-fill_bits]
        return bits


def parse_aivdm_sentence(sentence: str, *, ignore_checksum: bool = False) -> AivdmSentence:
    text = sentence.strip()
    if not ignore_checksum and not validate_nmea_checksum(text):
        raise ValueError(f"Invalid NMEA checksum: {sentence!r}")
    body = text[1:] if text.startswith(("!", "$")) else text
    body = body.split("*", 1)[0]
    fields = body.split(",")
    if fields[0] not in {"AIVDM", "AIVDO"}:
        raise ValueError(f"Not an AIVDM/AIVDO sentence: {sentence!r}")
    return AivdmSentence(
        total=int(fields[1]),
        number=int(fields[2]),
        sequential_id=fields[3],
        channel=fields[4],
        payload=fields[5],
        fill_bits=int(fields[6]),
    )


def decode_position_report(bits: str) -> dict:
    message_type = uint(bits, 0, 6)
    if message_type in {1, 2, 3}:
        return {
            "message_type": message_type,
            "repeat": uint(bits, 6, 8),
            "mmsi": uint(bits, 8, 38),
            "sog_kn": _decode_sog(uint(bits, 50, 60)),
            "lon": _decode_lon(sint(bits, 61, 89)),
            "lat": _decode_lat(sint(bits, 89, 116)),
            "cog_deg": _decode_cog(uint(bits, 116, 128)),
            "heading_deg": _decode_heading(uint(bits, 128, 137)),
        }
    if message_type == 18:
        return {
            "message_type": message_type,
            "repeat": uint(bits, 6, 8),
            "mmsi": uint(bits, 8, 38),
            "sog_kn": _decode_sog(uint(bits, 46, 56)),
            "lon": _decode_lon(sint(bits, 57, 85)),
            "lat": _decode_lat(sint(bits, 85, 112)),
            "cog_deg": _decode_cog(uint(bits, 112, 124)),
            "heading_deg": _decode_heading(uint(bits, 124, 133)),
        }
    if message_type == 24:
        part = uint(bits, 38, 40)
        result = {"message_type": 24, "repeat": uint(bits, 6, 8), "mmsi": uint(bits, 8, 38), "part": part}
        if part == 0 and len(bits) >= 160:
            result["name"] = ais_text(bits[40:160])
        elif part == 1 and len(bits) >= 88:
            result["ship_type"] = uint(bits, 40, 48)
            result["callsign"] = ais_text(bits[90:132]) if len(bits) >= 132 else None
        return result
    return {"message_type": message_type, "mmsi": uint(bits, 8, 38) if len(bits) >= 38 else None}


def uint(bits: str, start: int, end: int) -> int:
    return int(bits[start:end], 2)


def sint(bits: str, start: int, end: int) -> int:
    value = uint(bits, start, end)
    width = end - start
    if value & (1 << (width - 1)):
        value -= 1 << width
    return value


def ais_text(bits: str) -> str:
    chars = []
    for i in range(0, len(bits), 6):
        value = int(bits[i : i + 6], 2)
        chars.append(AIS_TEXT[value] if value < len(AIS_TEXT) else " ")
    return "".join(chars).rstrip("@ ").strip()


def _decode_sog(value: int) -> float | None:
    if value >= 1023:
        return None
    return value / 10.0


def _decode_cog(value: int) -> float | None:
    if value >= 3600:
        return None
    return value / 10.0


def _decode_heading(value: int) -> float | None:
    if value >= 511:
        return None
    return float(value)


def _decode_lon(value: int) -> float | None:
    if value == 0x6791AC0:
        return None
    return value / 600000.0


def _decode_lat(value: int) -> float | None:
    if value == 0x3412140:
        return None
    return value / 600000.0
