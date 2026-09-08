import json
import math
from pathlib import Path

import pytest

from ais_scenario_toolkit.aivdm_decode import aivdm_to_payload_bits
from ais_scenario_toolkit.io import read_timeline_jsonl
from ais_scenario_toolkit.player import records_to_output
from tools.build_helge_ingstad import build_scenario, build_records, interpolate, offset, range_residuals, sec

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def data():
    return build_scenario()


@pytest.fixture(scope='module')
def records(data):
    return build_records(data)


def test_report_distance_constraints(data,records):
    checks=range_residuals(data,records)
    assert len(checks)==5
    assert max(abs(c['residual_m']) for c in checks)<75
    distances=[c['model_bow_range_m'] for c in checks]
    assert all(a>b for a,b in zip(distances,distances[1:]))


def test_navigation_and_engine_orders_do_not_teleport_or_stop(data,records):
    at20=[r for r in records if r.time_sec==sec('04:00:20')][1]
    assert (at20.heading_deg,at20.cog_deg,at20.sog_kn)==(355,345.8,7.2)
    sola=[r for r in records if r.role=='target']
    for a,b in zip(sola,sola[1:]):
        assert 0<math.hypot(b.x_nm-a.x_nm,b.y_nm-a.y_nm)*1852<4
    assert sola[-1].sog_kn==7
    assert sola[-1].heading_deg==0
    # Shortest turn through north, not a sweep back through south.
    mid=interpolate(data['vessels'][1]['controls'],sec('04:01:00'))
    assert 358<mid['heading_deg']<360


def test_assumed_contact_geometry_and_time_bounds(data,records):
    assert len(records)==992
    assert sorted({r.time_sec for r in records})==list(range(496))
    frame=records[-2:]
    for ship,r in zip(data['vessels'],frame):
        dx,dy=offset(r.heading_deg,ship['contact_forward_m'],ship['contact_starboard_m'])
        assert (r.x_nm+dx,r.y_nm+dy)==pytest.approx((0,0),abs=1e-12)
    assert math.dist((frame[0].x_nm,frame[0].y_nm),(frame[1].x_nm,frame[1].y_nm))>0.05
    assert all(r.source=='aibn_source_informed_model' for r in records)


def test_transport_and_reproducibility(data,records):
    assert json.loads((ROOT/'scenarios/helge_ingstad_collision.json').read_text(encoding='utf-8'))==data
    saved=read_timeline_jsonl(ROOT/'timeline/helge_ingstad_collision.jsonl')
    assert [r.to_dict() for r in records]==[r.to_dict() for r in saved]
    for r in records[::71]+records[-2:]:
        assert all(math.isfinite(v) for v in (r.lat,r.lon,r.sog_kn,r.heading_deg,r.cog_deg))
        nmea,bits=records_to_output(r)
        assert nmea
        if r.role=='target':
            assert aivdm_to_payload_bits(nmea[0])==bits[0]
