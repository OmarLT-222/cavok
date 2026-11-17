import pytest
from cavok import parse_metar, ParseError


# ── wind ──────────────────────────────────────────────────────────────────────

def test_wind_basic():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013")
    assert m.wind.direction == 230
    assert m.wind.speed == 10
    assert m.wind.gust is None
    assert m.wind.unit == "KT"
    assert m.wind.variable is False


def test_wind_gust():
    m = parse_metar("METAR LEMD 161230Z 23010G18KT 9999 FEW020 15/08 Q1013")
    assert m.wind.gust == 18


def test_wind_vrb():
    m = parse_metar("METAR LEMD 161230Z VRB05KT 9999 FEW020 15/08 Q1013")
    assert m.wind.direction is None
    assert m.wind.variable is True
    assert m.wind.speed == 5


def test_wind_mps():
    m = parse_metar("METAR UUEE 161230Z 09005MPS 9999 FEW020 15/08 Q1013")
    assert m.wind.unit == "MPS"
    assert m.wind.speed == 5


def test_wind_variable_direction_suffix():
    # variable direction suffix (e.g. 180V240) is consumed without error
    m = parse_metar("METAR LEMD 161230Z 20015KT 180V240 9999 FEW020 15/08 Q1013")
    assert m.wind.direction == 200


# ── visibility + RVR ──────────────────────────────────────────────────────────

def test_visibility_basic():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013")
    assert m.visibility.prevailing == 9999
    assert m.visibility.unit == "M"


def test_visibility_cavok():
    m = parse_metar("METAR LEMD 161230Z 23010KT CAVOK 15/08 Q1013")
    assert m.visibility.prevailing is None
    assert m.sky.cavok is True


def test_rvr_fixed():
    m = parse_metar("METAR LEMD 161230Z 23010KT 0600 R28L/0600U FEW020 15/08 Q1013")
    assert len(m.visibility.rvr) == 1
    r = m.visibility.rvr[0]
    assert r.runway == "28L"
    assert r.value == 600
    assert r.operator is None
    assert r.value_max is None
    assert r.trend == "U"


def test_rvr_variable():
    m = parse_metar("METAR LEMD 161230Z 23010KT 0600 R28L/0400V0800U FEW020 15/08 Q1013")
    r = m.visibility.rvr[0]
    assert r.value == 400
    assert r.value_max == 800
    assert r.operator is None
    assert r.operator_max is None
    assert r.trend == "U"


def test_rvr_operator_m():
    m = parse_metar("METAR LEMD 161230Z 23010KT 0050 R28L/M0050 FEW020 15/08 Q1013")
    r = m.visibility.rvr[0]
    assert r.operator == "M"
    assert r.value == 50
    assert r.value_max is None


def test_rvr_operator_p():
    m = parse_metar("METAR LEMD 161230Z 23010KT 2000 R28L/P2000 FEW020 15/08 Q1013")
    r = m.visibility.rvr[0]
    assert r.operator == "P"
    assert r.value == 2000


def test_rvr_operator_on_variable_ends():
    m = parse_metar("METAR LEMD 161230Z 23010KT 0050 R28L/M0050V0800U FEW020 15/08 Q1013")
    r = m.visibility.rvr[0]
    assert r.operator == "M"
    assert r.value == 50
    assert r.operator_max is None
    assert r.value_max == 800
    assert r.trend == "U"


# ── weather phenomena ─────────────────────────────────────────────────────────

def test_weather_light_rain():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 -RA FEW020 15/08 Q1013")
    assert len(m.weather) == 1
    w = m.weather[0]
    assert w.intensity == "-"
    assert w.descriptor is None
    assert "RA" in w.phenomena


def test_weather_thunderstorm_rain():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 TSRA FEW020 15/08 Q1013")
    w = m.weather[0]
    assert w.descriptor == "TS"
    assert "RA" in w.phenomena


def test_weather_fog():
    m = parse_metar("METAR LEMD 161230Z 23010KT 0200 FG FEW020 15/08 Q1013")
    w = m.weather[0]
    assert w.intensity is None
    assert w.descriptor is None
    assert "FG" in w.phenomena


# ── sky condition ─────────────────────────────────────────────────────────────

def test_sky_cloud_layers():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 BKN080 15/08 Q1013")
    assert len(m.sky.layers) == 2
    assert m.sky.layers[0].cover == "FEW"
    assert m.sky.layers[0].height == 20
    assert m.sky.layers[1].cover == "BKN"


def test_cloud_cb():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020CB 15/08 Q1013")
    assert m.sky.layers[0].type == "CB"


def test_cloud_tcu():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020TCU 15/08 Q1013")
    assert m.sky.layers[0].type == "TCU"


def test_visibility_nsc():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 NSC 15/08 Q1013")
    assert m.sky.nsc is True
    assert m.sky.cavok is False


# ── temperature / QNH ─────────────────────────────────────────────────────────

def test_temperature_positive():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013")
    assert m.temperature == 15
    assert m.dewpoint == 8


def test_temperature_negative():
    m = parse_metar("METAR UUEE 161230Z 23010KT 9999 FEW020 M05/M10 Q1013")
    assert m.temperature == -5
    assert m.dewpoint == -10


def test_qnh_hpa():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013")
    assert m.qnh == 1013
    assert m.qnh_unit == "hPa"


def test_qnh_inhg():
    m = parse_metar("METAR KJFK 161230Z 23010KT 9999 FEW020 15/08 A2992")
    assert m.qnh == 2992
    assert m.qnh_unit == "inHg"


# ── flags + RMK ───────────────────────────────────────────────────────────────

def test_auto_flag():
    m = parse_metar("METAR LEMD 161230Z AUTO 23010KT 9999 FEW020 15/08 Q1013")
    assert m.auto is True


def test_cor_flag():
    m = parse_metar("METAR LEMD 161230Z COR 23010KT 9999 FEW020 15/08 Q1013")
    assert m.auto is False


def test_rmk_preserved():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013 RMK AO2 SLP045")
    assert m.rmk == "AO2 SLP045"


def test_parse_speci():
    m = parse_metar("SPECI LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013")
    assert m.station == "LEMD"


# ── full roundtrip ────────────────────────────────────────────────────────────

def test_parse_metar_basic():
    m = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013")
    assert m.station == "LEMD"
    assert m.wind.speed == 10
    assert m.visibility.prevailing == 9999
    assert m.temperature == 15
    assert m.dewpoint == 8
    assert m.qnh == 1013
    assert m.qnh_unit == "hPa"
    assert m.auto is False
    assert m.rmk is None


# ── errors ────────────────────────────────────────────────────────────────────

def test_parse_error_bad_token():
    with pytest.raises(ParseError):
        parse_metar("METAR LEMD 161230Z BADTOKEN 9999 FEW020 15/08 Q1013")


def test_parse_error_has_token_and_position():
    with pytest.raises(ParseError) as exc_info:
        parse_metar("METAR LEMD BADTIME 23010KT 9999 FEW020 15/08 Q1013")
    err = exc_info.value
    assert hasattr(err, "token")
    assert hasattr(err, "position")
