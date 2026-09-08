"""Build a source-informed kinematic reconstruction of Helge Ingstad / Sola TS.

This is not recorded AIS. Source controls, assumed geometry and residuals are
published in the scenario and docs/helge_ingstad_collision.md. Standard library only.
"""
from __future__ import annotations

import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ais_scenario_toolkit.cpa import calc_cpa_tcpa
from ais_scenario_toolkit.compiler import classify_with_thresholds
from ais_scenario_toolkit.geo import local_xy_to_lat_lon
from ais_scenario_toolkit.io import write_timeline_csv, write_timeline_jsonl
from ais_scenario_toolkit.model import Thresholds, TimelineRecord

REPORT = 'https://www.aibn.no/Marine/Published-reports/2019-08-eng?attach=1&pid=SHT-Report-ReportFile'
START = '2018-11-08T03:53:00+01:00'
DURATION = 495


def sec(clock):
    h, m, s = map(int, clock.split(':'))
    return h*3600 + m*60 + s - (3*3600+53*60)


def vector(degrees, metres):
    a = math.radians(degrees)
    return math.sin(a)*metres/1852, math.cos(a)*metres/1852


def offset(heading, forward_m, starboard_m):
    a, b = vector(heading, forward_m), vector(heading+90, starboard_m)
    return a[0]+b[0], a[1]+b[1]


def control(clock, heading, cog, speed, status):
    return dict(time_sec=sec(clock),local_time=clock,heading_deg=heading,cog_deg=cog,sog_kn=speed,status=status)


def build_scenario():
    return dict(schema_version='kinematic_reconstruction/1',name='helge_ingstad_collision',
        reference_start=START,reference_end='2018-11-08T04:01:15+01:00',duration_sec=DURATION,
        description='Source-informed model, not AIS fixes. Use tools/build_helge_ingstad.py.',
        origin=dict(lat=60+38.5/60,lon=4+51.9/60),
        source=dict(url=REPORT,title='AIBN Marine 2019/08, Part One, November 2019',
                    pages='17, 20, 22-28, 87-88, 153'),
        assumptions=[
          'Coordinates are derived by backward integration from assumed first-contact geometry at the published approximate accident location, not measured fixes.',
          'Helge Ingstad COG is approximated by heading; small oscillations are omitted. Controls interpolate linearly in time.',
          'Sola TS COG before 04:00:20 is assumed 345.8 degrees. That COG is explicitly reported only at 04:00:20. Earlier heading is 350 degrees.',
          'Sola TS terminal heading 000 degrees, COG 355 degrees and speed 7.0 kn are assumptions, not achieved values inferred from helm/engine commands.',
          'Both replay reference points are geometric ship centres, not actual GPS antenna positions.',
          'Contact geometry is assumed: Sola starboard anchor at 120m forward/12m starboard; Helge starboard side at 20m aft/8.4m starboard.',
          'Hull polygons are illustrative; no hydrodynamics, swept-volume collision detection, damage, flooding or post-impact trajectory.',
          'Only the two involved ships are modelled; Tenax, Ajax, Dr. No, Silver Firda, Vestbris and Seigrunn are not reconstructed.',
          'Synthetic MMSIs and Class B transport are for display; Helge is own NMEA, not a claim of historical AIS transmission.'
        ],
        vessels=[dict(name='HELGE INGSTAD',display_name='HNoMS Helge Ingstad',role='own',mmsi=999181101,
            message_type=18,ship_type=35,length_m=133.25,beam_m=16.8,
            dimension_status='Length: report p.153; beam is illustrative model value.',
            contact_forward_m=-20,contact_starboard_m=8.4,
            controls=[
                control('03:53:00',158,158,16.9,'p.17 heading/speed; COG=heading proxy'),
                control('03:59:26',157,157,17.0,'p.24 heading/speed; COG=heading proxy'),
                control('03:59:30',157,157,17.0,'p.24 turn onset; retained heading/speed'),
                control('04:00:00',155,155,16.9,'p.26 speed; heading interpolated model'),
                control('04:00:26',152.5,152.5,16.9,'p.26 heading; speed held'),
                control('04:00:36',149.7,149.7,16.9,'p.26 heading; speed held'),
                control('04:00:46',147,147,16.9,'p.24 heading; speed held'),
                control('04:01:06',147.2,147.2,16.9,'p.27 pre-final heading; exact time assumed'),
                control('04:01:15',145.7,145.7,16.9,'p.27 terminal heading; exact timing and speed held model'),
            ]),
            dict(name='SOLA TS',display_name='Sola TS',role='target',mmsi=999181102,
            message_type=18,ship_type=80,length_m=249.9,beam_m=44,
            dimension_status='Length: report p.153; beam is illustrative model value.',
            contact_forward_m=120,contact_starboard_m=12,
            controls=[
                control('03:53:00',350,345.8,3.7353846154,'Heading after p.20 order assumed steady; speed interpolated from 3.2kn at03:52 to6.1kn at03:57:25; COG assumed'),
                control('03:57:25',350,345.8,6.1,'p.22 speed; heading held, COG assumed'),
                control('03:59:00',350,345.8,6.7,'p.24 speed and set course; COG assumed'),
                control('03:59:21',350,345.8,6.83125,'p.24 starboard course order; response begins model'),
                control('04:00:20',355,345.8,7.2,'p.26 heading, COG and SOG'),
                control('04:00:30',356,347.5,7.2,'p.27 SOG; heading/COG interpolated model; engine stop is an annotation'),
                control('04:00:50',358,351,7.1,'p.27 full astern order; achieved heading/COG/speed assumed'),
                control('04:01:15',0,355,7.0,'Terminal heading/COG/SOG assumed, not recorded'),
            ])],
        range_checks=[dict(time_sec=sec(t),local_time=t,bow_range_m=r,source=f'figure {fig}',
                          note='Figure timestamp adopted; nearby prose timestamps sometimes differ by 2-5s.')
                      for t,r,fig in [('03:57:27',2720,13),('03:59:07',1510,15),('03:59:57',875,16),('04:00:27',500,17),('04:00:47',250,18)]],
        annotations=[dict(time_sec=sec(t),local_time=t,label=label,source=source) for t,label,source in [
          ('03:53:00','再生開始：Helge南下、Sola出港後の増速','p.17 / model'),
          ('03:57:27','報告書：船首間距離 約2,720m','figure 13'),
          ('03:58:03','SolaがVTSに接近船の識別を問い合わせ','p.22'),
          ('03:58:54','VTSがAISのないレーダー目標を追跡','p.23'),
          ('03:59:02','Solaが信号灯で注意喚起','p.23'),
          ('03:59:21','Sola：000°への変針指令','p.24'),
          ('03:59:30','Helge：左への変針開始','p.24'),
          ('03:59:47','VTS：接近船はHelge Ingstadの可能性と伝達','p.25'),
          ('03:59:56','SolaがHelgeを船名で呼び出す','p.25'),
          ('04:00:08','Sola：直ちに右転するよう要求','p.25'),
          ('04:00:11','Helge：照明のある物体へ近づくと考え右転を拒む','pp.25-26'),
          ('04:00:27','Helge：右舷のプラットフォーム通過後に右転すると応答','p.26'),
          ('04:00:30','Sola：機関停止の指令（船は直ちには停止しない）','p.27'),
          ('04:00:44','VTS：接近への対処を要求','p.27'),
          ('04:00:50','Sola：全速後進の指令','p.27'),
          ('04:01:03','VTS：衝突するとの警告','p.27'),
          ('04:01:15','衝突時刻・再生終了。接触位置はモデルの仮定','p.28 / model'),
        ]])


def interpolate(controls,t):
    if t<=controls[0]['time_sec']:
        return {k:controls[0][k] for k in ('heading_deg','cog_deg','sog_kn')}
    for a,b in zip(controls,controls[1:]):
        if t<=b['time_sec']:
            f=(t-a['time_sec'])/(b['time_sec']-a['time_sec'])
            return {k: ((a[k]+((b[k]-a[k]+180)%360-180)*f)%360 if k.endswith('deg')
                        else a[k]+(b[k]-a[k])*f) for k in ('heading_deg','cog_deg','sog_kn')}
    return {k:controls[-1][k] for k in ('heading_deg','cog_deg','sog_kn')}


def build_records(data):
    duration=data['duration_sec']
    paths=[]
    for ship in data['vessels']:
        states=[interpolate(ship['controls'],t) for t in range(duration+1)]
        final=states[-1]
        # Both assumed contact points meet at origin; centre points stay distinct.
        ox,oy=offset(final['heading_deg'],ship['contact_forward_m'],ship['contact_starboard_m'])
        positions=[None]*(duration+1)
        positions[-1]=(-ox,-oy)
        for t in range(duration-1,-1,-1):
            mid=interpolate(ship['controls'],t+.5)
            dx,dy=vector(mid['cog_deg'],mid['sog_kn']*1852/3600)
            positions[t]=(positions[t+1][0]-dx,positions[t+1][1]-dy)
        paths.append((ship,states,positions))
    records=[]
    for t in range(duration+1):
        frame=[]
        for ship,states,positions in paths:
            x,y=positions[t]
            lat,lon=local_xy_to_lat_lon(x,y,data['origin']['lat'],data['origin']['lon'])
            r=TimelineRecord(time_sec=float(t),role=ship['role'],mmsi=ship['mmsi'],name=ship['name'],
                x_nm=x,y_nm=y,lat=lat,lon=lon,source='aibn_source_informed_model',
                message_type=ship['message_type'],ship_type=ship['ship_type'],**states[t])
            if frame:
                a=frame[0]
                r.cpa_nm,r.tcpa_sec=calc_cpa_tcpa(a.x_nm,a.y_nm,a.cog_deg,a.sog_kn,x,y,r.cog_deg,r.sog_kn)
                r.computed_level=classify_with_thresholds(r.cpa_nm,r.tcpa_sec,Thresholds())
            frame.append(r)
        records.extend(frame)
    return records


def range_residuals(data,records):
    result=[]
    for check in data['range_checks']:
        frame=[r for r in records if r.time_sec==check['time_sec']]
        bows=[]
        for ship,r in zip(data['vessels'],frame):
            dx,dy=vector(r.heading_deg,ship['length_m']/2)
            bows.append((r.x_nm+dx,r.y_nm+dy))
        distance=math.dist(*bows)*1852
        result.append(dict(**check,model_bow_range_m=round(distance,2),residual_m=round(distance-check['bow_range_m'],2)))
    return result


def main():
    data=build_scenario()
    records=build_records(data)
    checks=range_residuals(data,records)
    (ROOT/'scenarios/helge_ingstad_collision.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_timeline_jsonl(records,ROOT/'timeline/helge_ingstad_collision.jsonl')
    write_timeline_csv(records,ROOT/'timeline/helge_ingstad_collision.csv')
    for suffix,rows in [('events',data['annotations']),('range_checks',checks)]:
        with (ROOT/f'timeline/helge_ingstad_collision_{suffix}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    payload=dict(start='03:53:00',duration=DURATION,events=data['annotations'],checks=checks,tracks=[])
    for ship in data['vessels']:
        points=[[r.time_sec,r.x_nm,r.y_nm,r.heading_deg,r.cpa_nm,r.tcpa_sec] for r in records if r.mmsi==ship['mmsi']]
        payload['tracks'].append(dict(name=ship['name'],length_m=ship['length_m'],beam_m=ship['beam_m'],points=points))
    template=(ROOT/'tools/helge_ingstad_preview.html').read_text(encoding='utf-8')
    html=template.replace('__TRACK_DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')))
    (ROOT/'timeline/helge_ingstad_collision_preview.html').write_text(html,encoding='utf-8')
    print(f'{len(records)} records, {DURATION}s. Bow-range checks:')
    for c in checks:
        print(c['local_time'],c['bow_range_m'],c['model_bow_range_m'],c['residual_m'])


if __name__=='__main__':
    main()
