from pathlib import Path

from ais_scenario_toolkit.compiler import compile_scenario, load_scenario
from ais_scenario_toolkit.io import write_timeline_csv, write_timeline_jsonl


ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_scenario_compile(tmp_path):
    scenario = load_scenario(ROOT / "scenarios" / "crossing_starboard_danger.json")
    records = compile_scenario(scenario)

    assert len(records) == (scenario.duration_sec + 1) * 2
    assert records[0].role == "own"
    target_records = [record for record in records if record.role == "target"]
    assert any(record.computed_level == "danger" for record in target_records)

    jsonl = tmp_path / "timeline.jsonl"
    csv = tmp_path / "timeline.csv"
    write_timeline_jsonl(records, jsonl)
    write_timeline_csv(records, csv)
    assert jsonl.exists()
    assert csv.exists()


def test_target_activation_window():
    scenario = load_scenario(ROOT / "scenarios" / "exhibition_gauntlet.json")
    records = compile_scenario(scenario)
    sart_times = [record.time_sec for record in records if record.mmsi == 970990001 and record.role == "target"]
    assert sart_times[0] == 415.0
    assert sart_times[-1] == 600.0
    assert len(sart_times) == 186
