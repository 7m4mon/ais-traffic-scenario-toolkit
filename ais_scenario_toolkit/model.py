from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any


@dataclass(frozen=True)
class Origin:
    lat: float
    lon: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Origin":
        return cls(lat=float(data["lat"]), lon=float(data["lon"]))


@dataclass(frozen=True)
class Event:
    time_sec: float
    heading_deg: float | None = None
    speed_kn: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            time_sec=float(data["time_sec"]),
            heading_deg=_optional_float(data.get("heading_deg")),
            speed_kn=_optional_float(data.get("speed_kn")),
        )


@dataclass(frozen=True)
class VesselInitial:
    x_nm: float
    y_nm: float
    heading_deg: float
    speed_kn: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VesselInitial":
        return cls(
            x_nm=float(data["x_nm"]),
            y_nm=float(data["y_nm"]),
            heading_deg=float(data["heading_deg"]),
            speed_kn=float(data["speed_kn"]),
        )


@dataclass(frozen=True)
class Vessel:
    mmsi: int
    name: str
    initial: VesselInitial
    events: list[Event] = field(default_factory=list)
    message_type: int = 18
    ship_type: int = 60
    expected_level: str | None = None
    active_from_sec: float = 0.0
    active_until_sec: float | None = None
    aton_type: int = 0
    aton_virtual: bool = False
    aton_off_position: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, is_own: bool = False) -> "Vessel":
        return cls(
            mmsi=int(data["mmsi"]),
            name=str(data.get("name", "")),
            initial=VesselInitial.from_dict(data["initial"]),
            events=sorted(
                [Event.from_dict(item) for item in data.get("events", [])],
                key=lambda item: item.time_sec,
            ),
            message_type=int(data.get("message_type", 1 if is_own else 18)),
            ship_type=int(data.get("ship_type", 60)),
            expected_level=data.get("expected_level"),
            active_from_sec=float(data.get("active_from_sec", 0.0)),
            active_until_sec=_optional_float(data.get("active_until_sec")),
            aton_type=int(data.get("aton_type", 0)),
            aton_virtual=bool(data.get("aton_virtual", False)),
            aton_off_position=bool(data.get("aton_off_position", False)),
        )


@dataclass(frozen=True)
class Thresholds:
    caution_cpa_nm: float = 0.5
    caution_tcpa_sec: float = 600.0
    danger_cpa_nm: float = 0.2
    danger_tcpa_sec: float = 300.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Thresholds":
        data = data or {}
        return cls(
            caution_cpa_nm=float(data.get("caution_cpa_nm", 0.5)),
            caution_tcpa_sec=float(data.get("caution_tcpa_sec", 600.0)),
            danger_cpa_nm=float(data.get("danger_cpa_nm", 0.2)),
            danger_tcpa_sec=float(data.get("danger_tcpa_sec", 300.0)),
        )


@dataclass(frozen=True)
class Scenario:
    schema_version: str
    name: str
    description: str
    origin: Origin
    duration_sec: int
    time_step_sec: int
    thresholds: Thresholds
    own_ship: Vessel
    targets: list[Vessel]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        return cls(
            schema_version=str(data.get("schema_version", "0.2")),
            name=str(data.get("name", "scenario")),
            description=str(data.get("description", "")),
            origin=Origin.from_dict(data["origin"]),
            duration_sec=int(data.get("duration_sec", 600)),
            time_step_sec=int(data.get("time_step_sec", 1)),
            thresholds=Thresholds.from_dict(data.get("thresholds")),
            own_ship=Vessel.from_dict(data["own_ship"], is_own=True),
            targets=[Vessel.from_dict(item) for item in data.get("targets", [])],
        )


@dataclass
class VesselState:
    x_nm: float
    y_nm: float
    heading_deg: float
    speed_kn: float


@dataclass
class TimelineRecord:
    time_sec: float
    role: str
    mmsi: int | None
    name: str | None
    x_nm: float | None
    y_nm: float | None
    lat: float | None
    lon: float | None
    sog_kn: float | None
    cog_deg: float | None
    heading_deg: float | None
    message_type: int | None = None
    expected_level: str | None = None
    computed_level: str | None = None
    cpa_nm: float | None = None
    tcpa_sec: float | None = None
    source: str = "synthetic"
    raw_aivdm: str | None = None
    timestamp_utc: datetime | str | None = None
    rx_signalpower_db: float | None = None
    rx_ppm: float | None = None
    rx_timestamp_raw: str | None = None
    repeat: int | None = None
    ship_type: int | None = None
    aton_type: int | None = None
    aton_virtual: bool = False
    aton_off_position: bool = False

    def to_dict(self) -> dict[str, Any]:
        result = self.__dict__.copy()
        ts = result.get("timestamp_utc")
        if isinstance(ts, datetime):
            result["timestamp_utc"] = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        for key, value in list(result.items()):
            if isinstance(value, float) and not math.isfinite(value):
                result[key] = None
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimelineRecord":
        parsed = data.copy()
        return cls(**parsed)


CSV_FIELDS = [
    "time_sec",
    "timestamp_utc",
    "role",
    "mmsi",
    "name",
    "x_nm",
    "y_nm",
    "lat",
    "lon",
    "sog_kn",
    "cog_deg",
    "heading_deg",
    "message_type",
    "expected_level",
    "computed_level",
    "cpa_nm",
    "tcpa_sec",
    "source",
    "raw_aivdm",
    "rx_signalpower_db",
    "rx_ppm",
    "rx_timestamp_raw",
    "ship_type",
    "aton_type",
    "aton_virtual",
    "aton_off_position",
]


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
