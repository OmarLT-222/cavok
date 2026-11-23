import pytest

from cavok import ParseError, parse_taf

# ── basic / flags ─────────────────────────────────────────────────────────────


def test_parse_taf_basic():
    t = parse_taf("TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025")
    assert t.station == "LEMD"
    assert t.amd is False
    assert t.cnl is False
    assert t.cor is False
    assert t.valid_from.hour == 12
    assert t.valid_to.hour == 12


def test_taf_amd_flag():
    t = parse_taf("TAF AMD LEMD 161100Z 1612/1712 23010KT 9999 FEW025")
    assert t.amd is True


def test_taf_cnl_flag():
    t = parse_taf("TAF CNL LEMD 161100Z 1612/1712")
    assert t.cnl is True


def test_taf_cor_flag():
    t = parse_taf("TAF COR LEMD 161100Z 1612/1712 23010KT 9999 FEW025")
    assert t.cor is True


# ── base forecast ─────────────────────────────────────────────────────────────


def test_taf_base_forecast():
    t = parse_taf("TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025")
    assert t.base.wind.speed == 10
    assert t.base.wind.direction == 230
    assert t.base.visibility.prevailing == 9999
    assert t.base.sky.layers[0].cover == "FEW"
    assert t.base.sky.layers[0].height == 25


def test_taf_base_cavok():
    t = parse_taf("TAF LEMD 161100Z 1612/1712 23010KT CAVOK")
    assert t.base.visibility.prevailing is None
    assert t.base.sky.cavok is True


# ── change groups ─────────────────────────────────────────────────────────────


def test_taf_becmg_group():
    t = parse_taf(
        "TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025 BECMG 1618/1620 VRB03KT"
    )
    assert len(t.changes) == 1
    cg = t.changes[0]
    assert cg.change_type == "BECMG"
    assert cg.forecast.wind.variable is True
    assert cg.forecast.validity_from.hour == 18
    assert cg.forecast.validity_to.hour == 20


def test_taf_tempo_group():
    t = parse_taf(
        "TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025 "
        "TEMPO 1614/1616 23020KT 2000 TSRA BKN015CB"
    )
    assert len(t.changes) == 1
    cg = t.changes[0]
    assert cg.change_type == "TEMPO"
    assert cg.forecast.wind.speed == 20
    assert len(cg.forecast.weather) == 1
    assert cg.forecast.weather[0].descriptor == "TS"
    assert cg.forecast.sky.layers[0].type == "CB"


def test_taf_prob30():
    t = parse_taf(
        "TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025 PROB30 1616/1618 23030KT"
    )
    cg = t.changes[0]
    assert cg.change_type == "PROB30"
    assert cg.forecast.wind.speed == 30


def test_taf_prob40_tempo():
    t = parse_taf(
        "TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025 PROB40 TEMPO 1616/1618 2000 -RA"
    )
    cg = t.changes[0]
    assert cg.change_type == "PROB40 TEMPO"
    assert cg.forecast.visibility.prevailing == 2000
    assert cg.forecast.weather[0].intensity == "-"


def test_taf_fm_group():
    t = parse_taf(
        "TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025 FM161800 09005KT 9999 SCT030"
    )
    cg = t.changes[0]
    assert cg.change_type == "FM"
    assert cg.forecast.validity_from.hour == 18
    assert cg.forecast.wind.direction == 90
    assert cg.forecast.wind.speed == 5


def test_taf_multiple_change_groups():
    t = parse_taf(
        "TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025 "
        "BECMG 1618/1620 VRB03KT "
        "TEMPO 1620/1622 2000 TSRA"
    )
    assert len(t.changes) == 2
    assert t.changes[0].change_type == "BECMG"
    assert t.changes[1].change_type == "TEMPO"


def test_taf_cavok_in_change_group():
    t = parse_taf(
        "TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025 TEMPO 1614/1616 CAVOK"
    )
    cg = t.changes[0]
    assert cg.forecast.sky.cavok is True
    assert cg.forecast.visibility.prevailing is None


# ── errors ────────────────────────────────────────────────────────────────────


def test_parse_error_missing_validity():
    with pytest.raises(ParseError):
        parse_taf("TAF LEMD 161100Z")


def test_parse_error_has_token_and_position():
    with pytest.raises(ParseError) as exc_info:
        parse_taf("TAF LEMD BADTIME 1612/1712 23010KT 9999 FEW025")
    err = exc_info.value
    assert hasattr(err, "token")
    assert hasattr(err, "position")
