from datetime import datetime, timedelta, timezone

from ais_scenario_toolkit.exporters import Exporter
from ais_scenario_toolkit.aivdm_decode import aivdm_to_payload_bits
from ais_scenario_toolkit.model import TimelineRecord
from ais_scenario_toolkit.player import play_timeline, records_to_output
from tools.ais_scenario_player import _resolve_serial_baud


def test_serial_baud_resolution():
    assert _resolve_serial_baud(None, None, default=4800) == 4800
    assert _resolve_serial_baud(None, None, default=38400) == 38400
    assert _resolve_serial_baud(None, 9600, default=4800) == 9600
    assert _resolve_serial_baud(38400, 9600, default=4800) == 38400


def test_records_to_output_message_21():
    record = TimelineRecord(
        time_sec=300.0,
        role="target",
        mmsi=995039901,
        name="DEMO VIRTUAL WRECK",
        x_nm=0.38,
        y_nm=1.55,
        lat=-38.0241667,
        lon=144.857,
        sog_kn=0.0,
        cog_deg=0.0,
        heading_deg=0.0,
        message_type=21,
        aton_type=17,
        aton_virtual=True,
    )
    messages, bitstrings = records_to_output(record)
    assert len(messages) == len(bitstrings) == 1
    assert int(bitstrings[0][0:6], 2) == 21
    assert bitstrings[0][269] == "1"
    assert aivdm_to_payload_bits(messages[0]) == bitstrings[0]


def test_play_timeline_echo_output(capsys):
    record = TimelineRecord(
        time_sec=0.0,
        role="target",
        mmsi=999510101,
        name="CROSS STBD",
        x_nm=0.0,
        y_nm=0.0,
        lat=-37.884,
        lon=144.95,
        sog_kn=12.0,
        cog_deg=270.0,
        heading_deg=270.0,
        message_type=18,
    )

    play_timeline([record], replay_speed=1000.0, static_interval=0, echo_output=True)

    output = capsys.readouterr().out
    assert "[     0.0s] target 999510101 TX !AIVDM" in output


class CaptureExporter(Exporter):
    def __init__(self):
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


def test_play_timeline_uses_one_timestamp_base(monkeypatch):
    class AdvancingDateTime(datetime):
        calls = 0

        @classmethod
        def now(cls, tz=None):
            value = datetime(2026, 9, 6, 0, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=cls.calls)
            cls.calls += 1
            return value

    records = [
        TimelineRecord(
            time_sec=time_sec,
            role="own",
            mmsi=999510000,
            name="OWN SHIP",
            x_nm=0.0,
            y_nm=0.0,
            lat=-37.884,
            lon=144.95,
            sog_kn=16.0,
            cog_deg=0.0,
            heading_deg=0.0,
            message_type=1,
        )
        for time_sec in (0.0, 1.0)
    ]
    exporter = CaptureExporter()
    monkeypatch.setattr("ais_scenario_toolkit.player.time.sleep", lambda _delay: None)
    monkeypatch.setattr("ais_scenario_toolkit.player.datetime", AdvancingDateTime)

    play_timeline(records, own_nmea_exporters=[exporter])

    rmc_messages = [message for message in exporter.messages if message.startswith("$GPRMC")]
    assert ",000000.00," in rmc_messages[0]
    assert ",000001.00," in rmc_messages[1]
    assert AdvancingDateTime.calls == 1
