from datetime import datetime, timezone

from ais_scenario_toolkit.nmea import make_hdt, make_rmc, nmea_checksum_body, validate_nmea_checksum


def test_nmea_checksum():
    assert nmea_checksum_body("GPHDT,123.4,T") == "31"
    assert validate_nmea_checksum(make_hdt(123.4))


def test_rmc_checksum_valid():
    sentence = make_rmc(datetime(2026, 6, 1, 12, 53, 33, tzinfo=timezone.utc), -37.884, 144.95, 9.0, 0.0)
    assert sentence.startswith("$GPRMC,125333.00,A,")
    assert validate_nmea_checksum(sentence)
