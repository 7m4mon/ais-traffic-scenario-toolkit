from __future__ import annotations

import math


def velocity_components_nm_s(heading_deg: float, speed_kn: float) -> tuple[float, float]:
    speed_nm_per_sec = speed_kn / 3600.0
    heading_rad = math.radians(heading_deg)
    return speed_nm_per_sec * math.sin(heading_rad), speed_nm_per_sec * math.cos(heading_rad)


def calc_cpa_tcpa(
    own_x_nm: float,
    own_y_nm: float,
    own_heading_deg: float,
    own_speed_kn: float,
    tgt_x_nm: float,
    tgt_y_nm: float,
    tgt_heading_deg: float,
    tgt_speed_kn: float,
) -> tuple[float, float]:
    """Return (cpa_nm, tcpa_sec)."""
    own_vx, own_vy = velocity_components_nm_s(own_heading_deg, own_speed_kn)
    tgt_vx, tgt_vy = velocity_components_nm_s(tgt_heading_deg, tgt_speed_kn)
    rx = tgt_x_nm - own_x_nm
    ry = tgt_y_nm - own_y_nm
    vx = tgt_vx - own_vx
    vy = tgt_vy - own_vy
    v2 = vx * vx + vy * vy
    if v2 < 1e-18:
        return math.hypot(rx, ry), math.inf
    tcpa_sec = -((rx * vx) + (ry * vy)) / v2
    cpa_x = rx + vx * tcpa_sec
    cpa_y = ry + vy * tcpa_sec
    return math.hypot(cpa_x, cpa_y), tcpa_sec


def classify_cpa_tcpa(
    cpa_nm: float,
    tcpa_sec: float,
    caution_cpa_nm: float = 0.5,
    caution_tcpa_sec: float = 600.0,
    danger_cpa_nm: float = 0.2,
    danger_tcpa_sec: float = 300.0,
) -> str:
    if 0 < tcpa_sec < danger_tcpa_sec and cpa_nm < danger_cpa_nm:
        return "danger"
    if 0 < tcpa_sec < caution_tcpa_sec and cpa_nm < caution_cpa_nm:
        return "caution"
    return "safe"
