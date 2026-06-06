from ais_scenario_toolkit.aiscatcher_import import parse_aiscatcher_line


SAMPLE_LINE = "!AIVDM,1,1,,A,1>pf?UQP01:Gdtsb?:V9>WHd0000,0*17 ( MSG: 1, REPEAT: 0, MMSI: 999002005, signalpower: -3.4104, ppm: -0.289352, timestamp: 20260601125333)"


def test_parse_aiscatcher_line_with_metadata():
    parsed = parse_aiscatcher_line(SAMPLE_LINE)

    assert parsed is not None
    assert parsed.raw_aivdm == "!AIVDM,1,1,,A,1>pf?UQP01:Gdtsb?:V9>WHd0000,0*17"
    assert parsed.mmsi == 999002005
    assert parsed.message_type == 1
    assert parsed.rx_signalpower_db == -3.4104
    assert parsed.rx_ppm == -0.289352
    assert parsed.rx_timestamp_raw == "20260601125333"
    assert parsed.timestamp_utc.strftime("%Y-%m-%dT%H:%M:%SZ") == "2026-06-01T12:53:33Z"
