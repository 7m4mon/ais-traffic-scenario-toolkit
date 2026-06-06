from ais_scenario_toolkit.model import TimelineRecord
from ais_scenario_toolkit.player import play_timeline


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
