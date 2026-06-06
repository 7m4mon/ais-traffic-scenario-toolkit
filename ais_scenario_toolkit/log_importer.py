from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from .aiscatcher_import import parse_aiscatcher_line
from .aivdm_decode import AivdmFragmentAssembler
from .cpa import calc_cpa_tcpa, classify_cpa_tcpa
from .geo import lat_lon_to_local_xy
from .model import Thresholds, TimelineRecord


def import_aivdm_log(
    input_path: str | Path,
    *,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
    own_mmsi: int | None = None,
    own_source: str = "none",
    own_heading_deg: float = 0.0,
    own_speed_kn: float = 0.0,
    ignore_checksum: bool = False,
    log_timezone: str = "UTC",
    fixed_step_sec: float = 1.0,
    thresholds: Thresholds | None = None,
) -> list[TimelineRecord]:
    thresholds = thresholds or Thresholds()
    assembler = AivdmFragmentAssembler(ignore_checksum=ignore_checksum)
    parsed_rows = []
    first_ts: datetime | None = None
    synthetic_index = 0
    names: dict[int, str] = {}
    with Path(input_path).open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                parsed = parse_aiscatcher_line(
                    line,
                    ignore_checksum=ignore_checksum,
                    log_timezone=log_timezone,
                    assembler=assembler,
                )
            except ValueError:
                continue
            if parsed is None:
                continue
            if parsed.name and parsed.mmsi is not None:
                names[parsed.mmsi] = parsed.name
            if parsed.message_type not in {1, 2, 3, 18}:
                continue
            if parsed.lat is None or parsed.lon is None:
                continue
            if parsed.timestamp_utc is not None and first_ts is None:
                first_ts = parsed.timestamp_utc
            if parsed.timestamp_utc is not None and first_ts is not None:
                time_sec = (parsed.timestamp_utc - first_ts).total_seconds()
            else:
                time_sec = synthetic_index * fixed_step_sec
                synthetic_index += 1
            x_nm = y_nm = None
            if origin_lat is not None and origin_lon is not None:
                x_nm, y_nm = lat_lon_to_local_xy(parsed.lat, parsed.lon, origin_lat, origin_lon)
            parsed_rows.append((time_sec, parsed, x_nm, y_nm))
    records: list[TimelineRecord] = []
    for time_sec, parsed, x_nm, y_nm in parsed_rows:
        if own_source == "synthetic" and origin_lat is not None and origin_lon is not None and own_mmsi is not None:
            records.append(_synthetic_own_record(time_sec, origin_lat, origin_lon, own_mmsi, own_heading_deg, own_speed_kn))
        cpa_nm = tcpa_sec = None
        computed_level = None
        if own_source == "synthetic" and x_nm is not None and y_nm is not None:
            cpa_nm, tcpa_sec = calc_cpa_tcpa(0.0, 0.0, own_heading_deg, own_speed_kn, x_nm, y_nm, parsed.cog_deg or 0.0, parsed.sog_kn or 0.0)
            computed_level = classify_cpa_tcpa(
                cpa_nm,
                tcpa_sec,
                thresholds.caution_cpa_nm,
                thresholds.caution_tcpa_sec,
                thresholds.danger_cpa_nm,
                thresholds.danger_tcpa_sec,
            )
        records.append(
            TimelineRecord(
                time_sec=time_sec,
                timestamp_utc=parsed.timestamp_utc,
                role="target",
                mmsi=parsed.mmsi,
                name=names.get(parsed.mmsi or -1) or parsed.name,
                x_nm=x_nm,
                y_nm=y_nm,
                lat=parsed.lat,
                lon=parsed.lon,
                sog_kn=parsed.sog_kn,
                cog_deg=parsed.cog_deg,
                heading_deg=parsed.heading_deg if parsed.heading_deg is not None else parsed.cog_deg,
                message_type=parsed.message_type,
                computed_level=computed_level,
                cpa_nm=cpa_nm,
                tcpa_sec=tcpa_sec,
                source="recorded_aivdm",
                raw_aivdm=parsed.raw_aivdm,
                rx_signalpower_db=parsed.rx_signalpower_db,
                rx_ppm=parsed.rx_ppm,
                rx_timestamp_raw=parsed.rx_timestamp_raw,
                repeat=parsed.repeat,
                ship_type=parsed.ship_type,
            )
        )
    return records


def _synthetic_own_record(
    time_sec: float,
    origin_lat: float,
    origin_lon: float,
    own_mmsi: int,
    own_heading_deg: float,
    own_speed_kn: float,
) -> TimelineRecord:
    base = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=time_sec)
    return TimelineRecord(
        time_sec=time_sec,
        timestamp_utc=base,
        role="own",
        mmsi=own_mmsi,
        name="OWN SHIP",
        x_nm=0.0,
        y_nm=0.0,
        lat=origin_lat,
        lon=origin_lon,
        sog_kn=own_speed_kn,
        cog_deg=own_heading_deg,
        heading_deg=own_heading_deg,
        message_type=1,
        source="synthetic",
    )
