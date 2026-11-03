from dataclasses import replace
from datetime import datetime, timezone
import zlib

import pytest

from ais_scenario_toolkit.ais_encode import encode_message_24a_bits, encode_message_24b_bits
from ais_scenario_toolkit.model import TimelineRecord
from ais_scenario_toolkit.sd_demo import HEADER, RECORD, compile_sd_demo


def target(time=0, **kwargs):
    return TimelineRecord(time_sec=time, role="target", mmsi=999510201, name="SD TEST",
                          x_nm=0, y_nm=0, lat=-38.05, lon=144.85, sog_kn=12,
                          cog_deg=90, heading_deg=90,
                          message_type=kwargs.pop("message_type", 18), **kwargs)


def unpack(data):
    magic, period, count, size, crc, name = HEADER.unpack_from(data)
    body = data[HEADER.size:]
    assert magic == b"AISDEMO2" and size == len(body) and crc == zlib.crc32(body)
    result = []
    offset = HEADER.size
    for _ in range(count):
        at, bits, channel, flags = RECORD.unpack_from(data, offset)
        offset += RECORD.size
        payload = data[offset:offset + bits // 8]
        offset += bits // 8
        result.append((at, "".join(f"{x:08b}" for x in payload), chr(channel), flags))
    assert offset == len(data)
    return period, result


def test_static_order_channel_timing_and_own_exclusion():
    own = replace(target(4), role="own")
    data = compile_sd_demo([target(2), own, target(0)], replay_speed=2, channel="B", include_own=False)
    period, frames = unpack(data)
    assert period == 2500
    assert [r[0] for r in frames] == [0, 0, 0, 1000]
    assert [int(r[1][:6], 2) for r in frames] == [18, 24, 24, 18]
    assert frames[1][1] == encode_message_24a_bits(mmsi=999510201, name="SD TEST")
    assert frames[2][1] == encode_message_24b_bits(mmsi=999510201)
    assert all(r[2:] == ("B", 0) for r in frames)
    assert data == compile_sd_demo([target(2), own, target(0)], replay_speed=2, channel="B", include_own=False)


def test_own_nmea_synchronized_and_prioritized_before_rf():
    from ais_scenario_toolkit.nmea import validate_nmea_checksum
    epoch = datetime(2026, 10, 25, 1, 2, 3, tzinfo=timezone.utc)
    own = replace(target(2), role="own")
    period, frames = unpack(compile_sd_demo([target(2), own], start_timestamp=epoch))
    assert period == 3000 and len(frames) == 4
    assert [f[0] for f in frames] == [2000] * 4
    assert [f[3] for f in frames] == [1, 1, 1, 0]
    sentences = [int(f[1], 2).to_bytes(len(f[1]) // 8, "big").decode("ascii") for f in frames[:3]]
    assert [s[:6] for s in sentences] == ["$GPRMC", "$GPGGA", "$GPHDT"]
    assert "010205.00" in sentences[0] and "251026" in sentences[0]
    assert all(validate_nmea_checksum(s) and len(s) <= 80 for s in sentences)
    assert all(f[2] == "-" for f in frames[:3])


def test_own_only_and_missing_own_position():
    _, frames = unpack(compile_sd_demo([replace(target(), role="own")]))
    assert len(frames) == 3 and all(f[3] == 1 for f in frames)
    with pytest.raises(ValueError, match="no playable"):
        compile_sd_demo([replace(target(), role="own", lat=None)])


def test_safety_payload_octet_padding_and_size_rejection():
    _, frames = unpack(compile_sd_demo([target(message_type=14, safety_text="A")]))
    assert len(frames[0][1]) == 48  # 40 header bits + 6 text bits + 2 spare bits.
    with pytest.raises(ValueError, match="600 bits"):
        compile_sd_demo([target(message_type=14, safety_text="A" * 100)])


@pytest.mark.parametrize("speed", [0, -1, float("inf"), float("nan"), 1e-300])
def test_invalid_speed_or_duration(speed):
    with pytest.raises(ValueError):
        compile_sd_demo([target()], replay_speed=speed)


@pytest.mark.parametrize("records", [[], [replace(target(), role="own", lat=None)], [target(-1)], [target(float("nan"))]])
def test_empty_or_bad_timeline(records):
    with pytest.raises(ValueError):
        compile_sd_demo(records)


def test_raw_multipart_is_explicit_error():
    with pytest.raises(ValueError, match="multipart/invalid"):
        compile_sd_demo([target(raw_aivdm="!AIVDM,2,1,0,A,123,0*00")])


def test_cli_writes_card_file_and_reports_failure(tmp_path, monkeypatch, capsys):
    from ais_scenario_toolkit.io import write_timeline_jsonl
    from tools.ais_scenario_sd_export import main
    timeline = tmp_path / "timeline.jsonl"
    output = tmp_path / "card" / "demo.bin"
    write_timeline_jsonl([target()], timeline)
    monkeypatch.setattr("sys.argv", ["export", "--timeline", str(timeline), "--output", str(output)])
    assert main() == 0
    assert unpack(output.read_bytes())[1]
    write_timeline_jsonl([target(message_type=14, safety_text="A" * 100)], timeline)
    before = output.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2 and "SD export failed" in capsys.readouterr().err
    assert output.read_bytes() == before  # Failed export must not destroy the usable demo.
