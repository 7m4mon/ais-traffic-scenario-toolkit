from ais_scenario_toolkit.cpa import calc_cpa_tcpa, classify_cpa_tcpa


def test_calc_cpa_tcpa_known_crossing():
    cpa_nm, tcpa_sec = calc_cpa_tcpa(0, 0, 0, 10, 1, 2, 270, 10)

    assert round(tcpa_sec, 6) == 540.0
    assert round(cpa_nm, 6) == round(2**0.5 / 2, 6)
    assert classify_cpa_tcpa(cpa_nm, tcpa_sec) == "safe"


def test_classify_danger_precedence():
    assert classify_cpa_tcpa(0.1, 100.0) == "danger"
    assert classify_cpa_tcpa(0.3, 400.0) == "caution"
    assert classify_cpa_tcpa(0.1, -1.0) == "safe"
