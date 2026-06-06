from __future__ import annotations

import json
from pathlib import Path

from .cpa import calc_cpa_tcpa, classify_cpa_tcpa, velocity_components_nm_s
from .geo import local_xy_to_lat_lon
from .model import Scenario, Thresholds, TimelineRecord, Vessel, VesselState


def load_scenario(path: str | Path) -> Scenario:
    with Path(path).open("r", encoding="utf-8") as f:
        return Scenario.from_dict(json.load(f))


def compile_scenario(scenario: Scenario) -> list[TimelineRecord]:
    records: list[TimelineRecord] = []
    thresholds = scenario.thresholds
    for time_sec in range(0, scenario.duration_sec + 1, scenario.time_step_sec):
        own_state = state_at(scenario.own_ship, time_sec)
        own_lat, own_lon = local_xy_to_lat_lon(
            own_state.x_nm,
            own_state.y_nm,
            scenario.origin.lat,
            scenario.origin.lon,
        )
        records.append(
            TimelineRecord(
                time_sec=float(time_sec),
                role="own",
                mmsi=scenario.own_ship.mmsi,
                name=scenario.own_ship.name,
                x_nm=own_state.x_nm,
                y_nm=own_state.y_nm,
                lat=own_lat,
                lon=own_lon,
                sog_kn=own_state.speed_kn,
                cog_deg=own_state.heading_deg,
                heading_deg=own_state.heading_deg,
                message_type=scenario.own_ship.message_type,
                source="synthetic",
                ship_type=scenario.own_ship.ship_type,
            )
        )
        for target in scenario.targets:
            target_state = state_at(target, time_sec)
            lat, lon = local_xy_to_lat_lon(
                target_state.x_nm,
                target_state.y_nm,
                scenario.origin.lat,
                scenario.origin.lon,
            )
            cpa_nm, tcpa_sec = calc_cpa_tcpa(
                own_state.x_nm,
                own_state.y_nm,
                own_state.heading_deg,
                own_state.speed_kn,
                target_state.x_nm,
                target_state.y_nm,
                target_state.heading_deg,
                target_state.speed_kn,
            )
            computed = classify_with_thresholds(cpa_nm, tcpa_sec, thresholds)
            records.append(
                TimelineRecord(
                    time_sec=float(time_sec),
                    role="target",
                    mmsi=target.mmsi,
                    name=target.name,
                    x_nm=target_state.x_nm,
                    y_nm=target_state.y_nm,
                    lat=lat,
                    lon=lon,
                    sog_kn=target_state.speed_kn,
                    cog_deg=target_state.heading_deg,
                    heading_deg=target_state.heading_deg,
                    message_type=target.message_type,
                    expected_level=target.expected_level,
                    computed_level=computed,
                    cpa_nm=cpa_nm,
                    tcpa_sec=tcpa_sec,
                    source="synthetic",
                    ship_type=target.ship_type,
                )
            )
    return records


def state_at(vessel: Vessel, time_sec: float) -> VesselState:
    x = vessel.initial.x_nm
    y = vessel.initial.y_nm
    heading = vessel.initial.heading_deg
    speed = vessel.initial.speed_kn
    last_t = 0.0
    for event in vessel.events:
        if event.time_sec > time_sec:
            break
        x, y = _advance(x, y, heading, speed, event.time_sec - last_t)
        if event.heading_deg is not None:
            heading = event.heading_deg
        if event.speed_kn is not None:
            speed = event.speed_kn
        last_t = event.time_sec
    x, y = _advance(x, y, heading, speed, time_sec - last_t)
    return VesselState(x_nm=x, y_nm=y, heading_deg=heading, speed_kn=speed)


def classify_with_thresholds(cpa_nm: float, tcpa_sec: float, thresholds: Thresholds) -> str:
    return classify_cpa_tcpa(
        cpa_nm,
        tcpa_sec,
        caution_cpa_nm=thresholds.caution_cpa_nm,
        caution_tcpa_sec=thresholds.caution_tcpa_sec,
        danger_cpa_nm=thresholds.danger_cpa_nm,
        danger_tcpa_sec=thresholds.danger_tcpa_sec,
    )


def _advance(x_nm: float, y_nm: float, heading_deg: float, speed_kn: float, delta_sec: float) -> tuple[float, float]:
    vx, vy = velocity_components_nm_s(heading_deg, speed_kn)
    return x_nm + vx * delta_sec, y_nm + vy * delta_sec
