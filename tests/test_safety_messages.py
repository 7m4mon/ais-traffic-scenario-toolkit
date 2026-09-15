import json
from pathlib import Path

import pytest

from ais_scenario_toolkit.ais_encode import AIS_TEXT, encode_safety_message_bits
from ais_scenario_toolkit.aivdm_decode import AivdmFragmentAssembler
from ais_scenario_toolkit.compiler import compile_scenario
from ais_scenario_toolkit.io import read_timeline_jsonl, write_timeline_jsonl, write_timeline_csv
from ais_scenario_toolkit.model import Scenario
from ais_scenario_toolkit.player import records_to_output, play_timeline


def scenario(messages):
    data = json.loads(Path("scenarios/crossing_starboard_danger.json").read_text())
    data.update(duration_sec=10, time_step_sec=5, messages=messages)
    return Scenario.from_dict(data)


@pytest.mark.parametrize("kind,length,offset", [(12,156,72), (14,161,40)] + [
    (kind, length, offset) for kind, offset in [(12,72), (14,40)] for length in range(9,17)
])
def test_safety_roundtrip(kind, length, offset, tmp_path):
    text = ("TEST MESSAGE " * 20)[:length]
    event = dict(time_sec=2.5, mmsi=999510101, message_type=kind, text=text.lower())
    if kind == 12:
        event.update(destination_mmsi=999510000, sequence_number=3)
    records = compile_scenario(scenario([event]))
    path = tmp_path / "timeline.jsonl"
    write_timeline_jsonl(records, path)
    write_timeline_csv(records, tmp_path / "timeline.csv")
    messages = [r for r in read_timeline_jsonl(path) if r.role == "message"]
    assert len(messages) == 1 and messages[0].time_sec == 2.5
    assert [r.time_sec for r in records] == sorted(r.time_sec for r in records)
    sentences, payloads = records_to_output(messages[0])
    assembler = AivdmFragmentAssembler()
    assembled = [assembler.add(s) for s in sentences]
    assert assembled[-1] == payloads[0]
    assert all(value is None for value in assembled[:-1])
    assert all(len(s.rstrip()) + 2 <= 82 for s in sentences)
    bits = payloads[0]
    assert int(bits[:6], 2) == kind
    assert int(bits[8:38], 2) == 999510101
    if kind == 12:
        assert int(bits[38:40], 2) == 3
        assert int(bits[40:70], 2) == 999510000
        assert bits[70:72] == "00"
    text_end = offset + 6 * len(text)
    assert "".join(AIS_TEXT[int(bits[i:i+6], 2)] for i in range(offset, text_end, 6)) == text
    assert len(bits) % 8 == 0
    assert bits[text_end:] == "0" * ((-text_end) % 8)


def test_exhibition_messages_octet_aligned():
    from ais_scenario_toolkit.compiler import load_scenario
    scenario_data = load_scenario("scenarios/exhibition_gauntlet.json")
    assert scenario_data.own_ship.mmsi == 999510000
    records = [r for r in compile_scenario(scenario_data) if r.role == "message"]
    assert [r.time_sec for r in records] == [30, 240, 305, 415]
    expected_lengths = [232, 288, 248, 96]
    for record, expected_length in zip(records, expected_lengths):
        sentences, payloads = records_to_output(record)
        assert len(sentences) == 1  # Bluepill firmware accepts single-fragment input.
        assert len(payloads[0]) == expected_length
        assert AivdmFragmentAssembler().add(sentences[0]) == payloads[0]
        if record.message_type == 12:
            assert int(payloads[0][40:70], 2) == 999510000
    assert records_to_output(records[0])[0] == [
        "!AIVDM,1,1,,A,>>q=@fA@E=B2n0<5E@Ttr0=8u=<TpN1A84HHT<0,2*48"
    ]


@pytest.mark.parametrize("changes", [
    {"text":"日本語"}, {"text":""}, {"text":"A"*162},
    {"message_type":12}, {"message_type":5}, {"mmsi":0},
    {"message_type":12,"destination_mmsi":123,"text":"A"*157},
    {"destination_mmsi":123}, {"text":"TEST\nMESSAGE"},
])
def test_invalid_safety_text(changes):
    args = dict(message_type=14, mmsi=999510101, text="TEST")
    args.update(changes)
    with pytest.raises(ValueError):
        encode_safety_message_bits(**args)


@pytest.mark.parametrize("time_sec", [-1, 11, float("nan"), float("inf")])
def test_invalid_event_time(time_sec):
    with pytest.raises(ValueError):
        compile_scenario(scenario([dict(time_sec=time_sec, mmsi=999510101, text="TEST")]))


def test_replay_safety_routing(monkeypatch):
    class Capture:
        def __init__(self):
            self.messages = []
        def send(self, message):
            self.messages.append(message)
    mixed, ais, own, bits = [Capture() for _ in range(4)]
    events = [dict(time_sec=t, mmsi=999510101, text="TEST "*25) for t in (0,2.5)]
    records = [r for r in compile_scenario(scenario(events)) if r.role == "message"]
    delays = []
    monkeypatch.setattr("ais_scenario_toolkit.player.time.sleep", delays.append)
    play_timeline(records, nmea_exporters=[mixed], aivdm_exporters=[ais],
                  own_nmea_exporters=[own], bitstring_exporters=[bits])
    assert delays == [2.5]
    assert mixed.messages == ais.messages
    assert len(ais.messages) == 6
    assert not own.messages
    assert len(bits.messages) == 2
