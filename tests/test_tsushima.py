"""Physical/transport checks, not a claim of historical verification."""
import json
import math
from pathlib import Path

import pytest

from ais_scenario_toolkit.compiler import compile_scenario, load_scenario, state_at
from ais_scenario_toolkit.player import records_to_output
from ais_scenario_toolkit.aivdm_decode import aivdm_to_payload_bits
from tools.build_tsushima import build_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_tsushima_delayed_ships_follow_same_spatial_turn():
    data = build_scenario()
    scenario = load_scenario(ROOT / "scenarios/tsushima_togo_turn.json")
    for raw, ship in zip(data["targets"][:11], scenario.targets[:11]):
        start = raw["historical"]["turn_start_sec"]
        for elapsed in [0, 30, 60, 90, 120]:
            lead = state_at(scenario.own_ship, 300 + elapsed)
            follower = state_at(ship, start + elapsed)
            assert math.hypot(lead.x_nm - follower.x_nm, lead.y_nm - follower.y_nm) < 1e-9
    assert state_at(scenario.own_ship, 420).heading_deg == 67.5
    assert state_at(scenario.own_ship, 360).heading_deg < 213.75


def test_tsushima_geometry_and_wire_output():
    scenario = load_scenario(ROOT / "scenarios/tsushima_togo_turn.json")
    records = compile_scenario(scenario)
    assert len(records) == 1201 * 24
    assert len({r.mmsi for r in records}) == 24
    for t in [0, 300, 420, 600, 1200]:
        frame = [r for r in records if r.time_sec == t]
        for r in frame:
            assert all(math.isfinite(v) for v in [r.lat, r.lon, r.heading_deg, r.sog_kn])
            nmea, bits = records_to_output(r)
            assert nmea
            if r.role == "target":
                assert aivdm_to_payload_bits(nmea[0]) == bits[0]
        if t == 300:
            assert math.hypot(frame[0].x_nm-frame[12].x_nm, frame[0].y_nm-frame[12].y_nm)*1852 == pytest.approx(8000)
        if t == 600:
            assert 6000 < math.hypot(frame[0].x_nm-frame[12].x_nm, frame[0].y_nm-frame[12].y_nm)*1852 < 7000


def test_committed_scenario_matches_builder():
    raw = json.loads((ROOT / "scenarios/tsushima_togo_turn.json").read_text(encoding="utf-8"))
    assert raw == build_scenario()
