import json
import math
from pathlib import Path

import pytest

from ais_scenario_toolkit.aivdm_decode import aivdm_to_payload_bits
from ais_scenario_toolkit.cpa import calc_cpa_tcpa
from ais_scenario_toolkit.io import read_timeline_jsonl
from ais_scenario_toolkit.player import records_to_output
from tools.build_fitzgerald import angle_lerp, build_records, clock_seconds, dms, sample_track

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def data():
    return json.loads((ROOT/'scenarios/fitzgerald_collision.json').read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def records(data):
    return build_records(data)


def test_published_fixes_preserved(data):
    # Original DMS rows remain exact at their own timestamps, including differing COG/HDG.
    for ship in data['vessels']:
        for obs in ship['observations']:
            s, source = sample_track(ship,clock_seconds(obs['local_time']),data['origin'],7)
            assert s['lat'] == dms(obs['lat_dms'])
            assert s['lon'] == dms(obs['lon_dms'])
            assert s['cog_deg'] == obs['cog_deg']
            assert s['sog_kn'] == obs['sog_kn']
            assert s['heading_deg'] == (obs['heading_deg'] if obs['heading_deg'] is not None else obs['cog_deg'])
            assert '_fix' in source
    assert dms('034-31-19.8') == pytest.approx(34.52216666666666)
    assert angle_lerp(359,1,.5) == 0


def test_time_coverage_and_no_invented_early_evora(records):
    assert len(records) == 3065
    assert {r.time_sec for r in records} == set(range(923))
    evora=[r for r in records if r.name=='MAERSK EVORA']
    assert evora[0].time_sec == 627
    assert len(evora) == 296
    assert all(sum(r.role=='own' for r in records if r.time_sec==t)==1 for t in (0,626,627,922))


def test_extrapolation_bounded_and_marked(data,records):
    for ship in data['vessels'][:2]:
        assert ship['observations'][-1]['local_time']=='01:30:27'
        with pytest.raises(ValueError,match='extrapolation'):
            sample_track(ship,clock_seconds('01:30:35'),data['origin'],7)
    extrapolated=[r for r in records if 'extrapolated' in r.source]
    assert len(extrapolated)==14
    assert min(r.time_sec for r in extrapolated)==916
    final=[r for r in records if r.time_sec==922]
    separation=math.hypot(final[0].x_nm-final[1].x_nm,final[0].y_nm-final[1].y_nm)*1852
    assert 300 < separation < 308  # Keep published reference positions; no forced convergence.


def test_cpa_uses_course_not_heading_and_transport(records):
    for t in (0,627,883,915,922):
        frame=[r for r in records if r.time_sec==t]
        own=frame[0]
        for r in frame:
            assert all(math.isfinite(v) for v in (r.lat,r.lon,r.sog_kn,r.cog_deg,r.heading_deg))
            nmea,bits=records_to_output(r)
            assert nmea
            if r.role=='target':
                assert aivdm_to_payload_bits(nmea[0])==bits[0]
                expected=calc_cpa_tcpa(own.x_nm,own.y_nm,own.cog_deg,own.sog_kn,r.x_nm,r.y_nm,r.cog_deg,r.sog_kn)
                assert (r.cpa_nm,r.tcpa_sec)==pytest.approx(expected)
    acx=next(r for r in records if r.time_sec==915 and r.name=='ACX CRYSTAL')
    assert acx.cog_deg==88.2 and acx.heading_deg==112


def test_generated_timeline_matches_source(records):
    saved=read_timeline_jsonl(ROOT/'timeline/fitzgerald_collision.jsonl')
    assert [r.to_dict() for r in saved]==[r.to_dict() for r in records]
