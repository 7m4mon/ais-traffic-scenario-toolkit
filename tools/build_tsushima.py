"""Build a source-noted, kinematic reconstruction of the opening at Tsushima.

Only standard-library dependencies are needed. No changes to the scenario
compiler/player are required. See docs/tsushima_togo_turn.md for uncertainties.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ais_scenario_toolkit.compiler import compile_scenario
from ais_scenario_toolkit.io import write_timeline_csv, write_timeline_jsonl
from ais_scenario_toolkit.model import Scenario

JP = [
    ("MIKASA", "三笠"), ("SHIKISHIMA", "敷島"), ("FUJI", "富士"),
    ("ASAHI", "朝日"), ("KASUGA", "春日"), ("NISSHIN", "日進"),
    ("IZUMO", "出雲"), ("AZUMA", "吾妻"), ("TOKIWA", "常磐"),
    ("YAKUMO", "八雲"), ("ASAMA", "浅間"), ("IWATE", "磐手"),
]
RU = [
    ("KNYAZ SUVOROV", "クニャージ・スヴォーロフ"),
    ("ALEKSANDR III", "インペラートル・アレクサンドルIII世"),
    ("BORODINO", "ボロジノ"), ("ORYOL", "オリョール"),
    ("OSLYABYA", "オスリャービャ"), ("SISOI VELIKY", "シソイ・ヴェリーキー"),
    ("NAVARIN", "ナヴァリン"), ("ADM NAKHIMOV", "アドミラル・ナヒーモフ"),
    ("NIKOLAI I", "インペラートル・ニコライI世"),
    ("ADM APRAKSIN", "ゲネラル・アドミラル・アプラクシン"),
    ("ADM SENYAVIN", "アドミラル・セニャーヴィン"),
    ("ADM USHAKOV", "アドミラル・ウシャコフ"),
]
SOURCES = [
    {"id": "JACAR", "url": "https://www.jacar.go.jp/exhibition/nichiro2/sensoushi/kaijou_09_detail.html",
     "use": "Japanese reference chronology: 14:05 port turn, 14:10 opening fire. Chart reference C05110096300 identified; original chart not digitised."},
    {"id": "TOGO", "url": "https://losthistory.net/russojapanesewar/togo-aar3.html",
     "use": "English transcription of Togo's report: Japanese sequential column, Russian two-column observation, 14:08 Russian fire, about 6000m Japanese opening range."},
    {"id": "SEMENOFF", "url": "https://www.gutenberg.org/cache/epub/57324/pg57324-images.html",
     "use": "Participant account: successive port turn through a shared point, approximately 15 minutes for the line at 15 knots; Russian clock not spliced into Japanese chronology."},
    {"id": "NHSA", "url": "https://navyhistory.au/the-battle-of-tsushima-1905/",
     "use": "Secondary account: ENE exit course and roughly two-minute Mikasa turn; ranges/times differ from other accounts."},
    {"id": "OOB", "url": "https://en.wikipedia.org/wiki/Battle_of_Tsushima_order_of_battle",
     "use": "Secondary cross-check of participating ships, not evidence for second-by-second positions."},
    {"id": "BATTLE", "url": "https://en.wikipedia.org/wiki/Battle_of_Tsushima",
     "use": "Secondary check of Japanese line order and 15/9-knot modelling speeds. Its conflicting detailed chronology is not adopted."},
]


def vector(heading: float, distance: float) -> tuple[float, float]:
    angle = math.radians(heading)
    return math.sin(angle) * distance, math.cos(angle) * distance


def turn_events(start: float, duration: float, initial: float, delta: float) -> list[dict]:
    """Midpoint piecewise headings approximate a constant-rate turn every 2 s.

    Negative delta is port. The explicit final event restores the exit heading.
    Follower delays may be fractional; the compiler supports these event times.
    """
    steps = int(duration / 2)
    return [
        {"time_sec": start + i * 2, "heading_deg": (initial + delta * (i + 0.5) / steps) % 360}
        for i in range(steps)
    ] + [{"time_sec": start + duration, "heading_deg": (initial + delta) % 360}]


def vessel(mmsi: int, name: str, label: str, x: float, y: float,
           heading: float, speed: float, events: list[dict], **metadata) -> dict:
    return {"mmsi": mmsi, "name": name, "message_type": 18, "ship_type": 35,
            "initial": {"x_nm": x, "y_nm": y, "heading_deg": heading, "speed_kn": speed},
            "events": events, "historical": {"display_name": label, **metadata}}


def build_scenario() -> dict:
    japanese = []
    for i, (name, label) in enumerate(JP):
        # 450 m centre spacing; the inter-division gap is 900 m.
        offset_nm = (i * 450 + (450 if i >= 6 else 0)) / 1852
        delay = offset_nm / 15 * 3600
        x, y = vector(213.75, -(15 * 300 / 3600 + offset_nm))
        japanese.append(vessel(999050101 + i, "JP " + name, label, x, y, 213.75, 15,
            turn_events(300 + delay, 120, 213.75, -146.25),
            side="Japan", division=1 if i < 6 else 2, sequence=i + 1,
            turn_start_sec=300 + delay, turn_end_sec=420 + delay,
            position_status="reconstructed"))
    # The Russian flagship is 8 km south-by-east of the Japanese turn entrance
    # at 14:05. This is an explicit geometric assumption, not a surveyed fix.
    rx, ry = vector(168.75, 8000 / 1852)
    dx, dy = vector(23, 9 * 300 / 3600)
    rx, ry = rx - dx, ry - dy
    russian = []
    for i, (name, label) in enumerate(RU):
        # Togo's observation of two irregular columns is the chosen viewpoint.
        # Exact merging/Oslyabya's stop cannot be reconstructed from these sources.
        column_index = i if i < 4 else i - 4
        along_nm = column_index * 450 / 1852 + (0.25 if i >= 4 else 0)
        ox, oy = vector(23, -along_nm)
        px, py = vector(293, 0 if i < 4 else 0.65)
        delay = along_nm / 9 * 3600
        events = turn_events(480 + delay, 180, 23, 22)
        russian.append(vessel(999050201 + i, "RU " + name, label, rx + ox + px, ry + oy + py,
            23, 9, events, side="Russia", division=1 if i < 4 else 2 if i < 8 else 3,
            column="right" if i < 4 else "left", sequence=column_index + 1,
            position_status="simplified Japanese-observed two columns; merger not reconstructed"))
    return {
        "schema_version": "0.2", "name": "tsushima_togo_turn",
        "description": "1905-05-27 14:00-14:20 Japanese reference time. Source-informed concept reconstruction; tracks and georeferencing are estimated, not historical fixes. See docs/tsushima_togo_turn.md.",
        "origin": {"lat": 34.30, "lon": 130.10},
        "duration_sec": 1200, "time_step_sec": 1,
        "historical": {
            "reference_start": "1905-05-27T14:00:00+09:00",
            "reference_time_note": "Japanese-side chronology; not a synchronization of individual ship clocks.",
            "fidelity": "source-informed conceptual reconstruction, not a digitised historical track",
            "origin_status": "Approximate display anchor north of Okinoshima; exact turn coordinates unverified.",
            "sources": SOURCES,
            "assumptions": {
                "japanese_approach_deg_true": 213.75, "japanese_exit_deg_true": 67.5,
                "japanese_turn_duration_sec": 120, "japanese_speed_kn": 15,
                "japanese_turn_radius_m_derived": 15 * 1852 / 3600 * 120 / math.radians(146.25),
                "centre_spacing_m": 450, "japanese_interdivision_gap_m": 900,
                "russian_speed_kn": 9, "russian_initial_deg_true": 23,
                "russian_exit_deg_true": 45, "russian_column_separation_nm": 0.65,
                "russian_left_column_head_lag_nm": 0.25,
                "range_at_turn_start_m": 8000, "russian_flagship_bearing_at_turn_deg": 168.75,
                "magnetic_variation_applied": False,
            },
            "omissions": ["Russian formation merger and Oslyabya's slowing/stopping",
                          "Individual helm, machinery, current and wind effects",
                          "Gunnery, damage, visibility, scouting and auxiliary vessels",
                          "Original battle-chart georeferencing and ship-log digitisation"],
            "annotations": [
                {"time_sec": 0, "label": "接近：日本側12隻・ロシア側12隻", "status": "model"},
                {"time_sec": 300, "label": "14:05 三笠が左回頭開始", "status": "JACAR / TOGO"},
                {"time_sec": 420, "label": "14:07 三笠の回頭終了（推定）", "status": "NHSA / model"},
                {"time_sec": 480, "label": "14:08 ロシア側砲撃開始（日本側記録）", "status": "TOGO"},
                {"time_sec": 600, "label": "14:10 日本側砲撃開始", "status": "JACAR"},
                {"time_sec": round(japanese[-1]["historical"]["turn_end_sec"], 3),
                 "label": "磐手の回頭終了（モデル計算）", "status": "model"},
                {"time_sec": 1200, "label": "14:20 再現範囲終了", "status": "model"},
            ],
        },
        "own_ship": japanese[0], "targets": japanese[1:] + russian,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visualization-output", type=Path, help="Optional inline HTML fragment destination")
    args = parser.parse_args()
    data = build_scenario()
    scenario_path = ROOT / "scenarios/tsushima_togo_turn.json"
    scenario_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    records = compile_scenario(Scenario.from_dict(data))
    write_timeline_jsonl(records, ROOT / "timeline/tsushima_togo_turn.jsonl")
    write_timeline_csv(records, ROOT / "timeline/tsushima_togo_turn.csv")
    with (ROOT / "timeline/tsushima_togo_turn_events.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["time_sec", "label", "status"])
        writer.writeheader()
        writer.writerows(data["historical"]["annotations"])
    if args.visualization_output:
        vessels = [data["own_ship"], *data["targets"]]
        index = {v["mmsi"]: i for i, v in enumerate(vessels)}
        tracks = [[] for _ in vessels]
        for r in records:
            if r.time_sec % 5 == 0:
                tracks[index[r.mmsi]].append([round(r.x_nm, 5), round(r.y_nm, 5), round(r.heading_deg, 3)])
        payload = {"ships": [{"name": v["historical"]["display_name"], "ais": v["name"],
                              "side": v["historical"]["side"], "track": tracks[i]} for i, v in enumerate(vessels)],
                   "events": data["historical"]["annotations"]}
        template = (ROOT / "tools/tsushima_preview.html").read_text(encoding="utf-8")
        fragment = template.replace("__TSUSHIMA_DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        args.visualization_output.parent.mkdir(parents=True, exist_ok=True)
        args.visualization_output.write_text(fragment, encoding="utf-8")
        print(f"Preview: {args.visualization_output}")
    print(f"Scenario: {scenario_path}\nCompiled {len(records)} records (24 ships, 1201 frames).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
