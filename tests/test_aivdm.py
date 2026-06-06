from ais_scenario_toolkit.ais_encode import encode_message_18_bits, payload_bits_to_aivdm
from ais_scenario_toolkit.aivdm_decode import AivdmFragmentAssembler, aivdm_to_payload_bits, decode_position_report


SAMPLE = "!AIVDM,1,1,,A,1>pf?UQP01:Gdtsb?:V9>WHd0000,0*06"


def test_aivdm_to_payload_bits():
    bits = aivdm_to_payload_bits(SAMPLE)
    assert bits.startswith("000001")
    assert len(bits) == len("1>pf?UQP01:Gdtsb?:V9>WHd0000") * 6


def test_fragment_assembler_single_sentence():
    assembler = AivdmFragmentAssembler()
    bits = assembler.add(SAMPLE)
    assert bits == aivdm_to_payload_bits(SAMPLE)


def test_encode_decode_message_18_roundtrip():
    bits = encode_message_18_bits(
        mmsi=999510101,
        lat=-37.884,
        lon=144.95,
        sog_kn=12.3,
        cog_deg=270.0,
        heading_deg=270.0,
    )
    sentence = payload_bits_to_aivdm(bits)
    decoded = decode_position_report(aivdm_to_payload_bits(sentence))

    assert decoded["message_type"] == 18
    assert decoded["mmsi"] == 999510101
    assert abs(decoded["lat"] - -37.884) < 1e-5
    assert abs(decoded["lon"] - 144.95) < 1e-5
    assert decoded["sog_kn"] == 12.3
