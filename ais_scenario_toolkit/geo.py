from __future__ import annotations

import math

NM_PER_DEG_LAT = 60.0


def local_xy_to_lat_lon(x_nm: float, y_nm: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    lat = origin_lat + y_nm / NM_PER_DEG_LAT
    cos_lat = math.cos(math.radians(origin_lat))
    if abs(cos_lat) < 1e-12:
        raise ValueError("Origin latitude is too close to the pole for local lon conversion")
    lon = origin_lon + x_nm / (NM_PER_DEG_LAT * cos_lat)
    return lat, lon


def lat_lon_to_local_xy(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    y_nm = (lat - origin_lat) * NM_PER_DEG_LAT
    x_nm = (lon - origin_lon) * NM_PER_DEG_LAT * math.cos(math.radians(origin_lat))
    return x_nm, y_nm
