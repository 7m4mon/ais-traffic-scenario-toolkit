"""Replay published JTSB position tables, preserving fixes and separate COG/heading.

Input uses observed_tracks/1, not the synthetic compiler's motion-event schema.
Only the standard library is required. See docs/fitzgerald_collision.md.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ais_scenario_toolkit.cpa import calc_cpa_tcpa, velocity_components_nm_s
from ais_scenario_toolkit.compiler import classify_with_thresholds
from ais_scenario_toolkit.geo import lat_lon_to_local_xy, local_xy_to_lat_lon
from ais_scenario_toolkit.io import write_timeline_csv, write_timeline_jsonl
from ais_scenario_toolkit.model import Thresholds, TimelineRecord


def clock_seconds(value):
    h, m, s = map(int, value.split(':'))
    return h * 3600 + m * 60 + s


def dms(value):
    deg, minute, second = map(float, value.split('-'))
    return deg + minute / 60 + second / 3600


def angle_lerp(a, b, fraction):
    return (a + ((b - a + 180) % 360 - 180) * fraction) % 360


def sample_track(ship, absolute_sec, origin, max_extrapolation):
    rows = ship['observations']
    times = [clock_seconds(r['local_time']) for r in rows]
    if not rows or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('Observation times must be strictly increasing')
    if absolute_sec < times[0]:
        return None
    def fix(row):
        lat, lon = dms(row['lat_dms']), dms(row['lon_dms'])
        x, y = lat_lon_to_local_xy(lat, lon, origin['lat'], origin['lon'])
        return dict(lat=lat, lon=lon, x_nm=x, y_nm=y, sog_kn=row['sog_kn'],
                    cog_deg=row['cog_deg'], heading_deg=row['heading_deg'])
    i = bisect_left(times, absolute_sec)
    if i < len(times) and times[i] == absolute_sec:
        state, status = fix(rows[i]), 'fix'
    elif i == len(times):
        dt = absolute_sec - times[-1]
        if dt > max_extrapolation:
            raise ValueError(f"{ship['name']}: extrapolation exceeds {max_extrapolation}s")
        state = fix(rows[-1])
        vx, vy = velocity_components_nm_s(state['cog_deg'], state['sog_kn'])
        state['x_nm'] += vx * dt
        state['y_nm'] += vy * dt
        state['lat'], state['lon'] = local_xy_to_lat_lon(state['x_nm'], state['y_nm'], origin['lat'], origin['lon'])
        status = 'extrapolated'
    else:
        a, b = fix(rows[i-1]), fix(rows[i])
        f = (absolute_sec-times[i-1]) / (times[i]-times[i-1])
        state = {k: a[k] + (b[k]-a[k])*f for k in ('lat','lon','x_nm','y_nm','sog_kn')}
        state['cog_deg'] = angle_lerp(a['cog_deg'], b['cog_deg'], f)
        state['heading_deg'] = None if a['heading_deg'] is None or b['heading_deg'] is None else angle_lerp(a['heading_deg'], b['heading_deg'], f)
        status = 'interpolated'
    if state['heading_deg'] is None:
        state['heading_deg'] = state['cog_deg']
        status += '_heading_proxy'
    return state, f"jtsb_{ship['source_kind'].lower()}_{status}"


def build_records(data):
    if data['schema_version'] != 'observed_tracks/1':
        raise ValueError('Expected observed_tracks/1')
    start = datetime.fromisoformat(data['reference_start'])
    end = datetime.fromisoformat(data['reference_end'])
    duration = int((end-start).total_seconds())
    base = start.hour*3600 + start.minute*60 + start.second
    ships = sorted(data['vessels'], key=lambda s: s['role'] != 'own')
    if sum(s['role']=='own' for s in ships) != 1:
        raise ValueError('Exactly one own ship required')
    records = []
    for t in range(duration+1):
        frame = []
        for ship in ships:
            sampled = sample_track(ship, base+t, data['origin'], data['max_extrapolation_sec'])
            if sampled is None:
                if ship['role']=='own':
                    raise ValueError('Own ship not available at start')
                continue
            state, source = sampled
            record = TimelineRecord(time_sec=float(t), role=ship['role'], mmsi=ship['mmsi'],
                name=ship['name'], message_type=ship['message_type'], ship_type=ship['ship_type'],
                source=source, **state)
            if record.role == 'target':
                own = frame[0]
                record.cpa_nm, record.tcpa_sec = calc_cpa_tcpa(own.x_nm, own.y_nm, own.cog_deg, own.sog_kn,
                    record.x_nm, record.y_nm, record.cog_deg, record.sog_kn)
                record.computed_level = classify_with_thresholds(record.cpa_nm, record.tcpa_sec, Thresholds())
            frame.append(record)
        records.extend(frame)
    return records


def preview_payload(data, records):
    tracks = []
    for ship in data['vessels']:
        points = [[r.time_sec, r.x_nm, r.y_nm, r.heading_deg, r.cpa_nm, r.tcpa_sec]
                  for r in records if r.mmsi == ship['mmsi']]
        tracks.append(dict(name=ship['name'], points=points))
    return dict(tracks=tracks, events=data['annotations'], start=data['reference_start'][11:19],
                duration=int(records[-1].time_sec))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', type=Path, default=ROOT/'scenarios/fitzgerald_collision.json')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'timeline')
    args = parser.parse_args()
    data = json.loads(args.scenario.read_text(encoding='utf-8'))
    records = build_records(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_dir/'fitzgerald_collision'
    write_timeline_jsonl(records, stem.with_suffix('.jsonl'))
    write_timeline_csv(records, stem.with_suffix('.csv'))
    base = clock_seconds(data['reference_start'][11:19])
    with (args.output_dir/'fitzgerald_collision_events.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=['time_sec','local_time','label','source'])
        writer.writeheader()
        writer.writerows(dict(time_sec=clock_seconds(e['local_time'])-base,**e) for e in data['annotations'])
    template = (ROOT/'tools/fitzgerald_preview.html').read_text(encoding='utf-8')
    html = template.replace('__TRACK_DATA__',json.dumps(preview_payload(data,records),ensure_ascii=False,separators=(',',':')))
    (args.output_dir/'fitzgerald_collision_preview.html').write_text(html,encoding='utf-8')
    final = [r for r in records if r.time_sec == records[-1].time_sec]
    separation = math.hypot(final[0].x_nm-final[1].x_nm,final[0].y_nm-final[1].y_nm)*1852
    print(f'{len(records)} records; {records[-1].time_sec:g} seconds; final recorded-reference separation {separation:.1f} m (not hull clearance).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
