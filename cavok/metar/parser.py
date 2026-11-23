from datetime import datetime, timezone

from cavok._tokens import (
    RE_CLOUD,
    RE_FM,
    RE_QNH_A,
    RE_QNH_Q,
    RE_RVR,
    RE_SKY_SPECIAL,
    RE_STATION,
    RE_TEMP,
    RE_TIME,
    RE_TREND_AT,
    RE_TREND_FM,
    RE_TREND_TL,
    RE_VIS,
    RE_WEATHER,
    RE_WIND,
    RE_WIND_VAR,
    _temp_val,
    parse_time,
    tokenize,
)
from cavok.exceptions import ParseError
from cavok.metar.models import (
    CloudLayer,
    Metar,
    RVR,
    SkyCondition,
    TrendForecast,
    Visibility,
    WeatherPhenomenon,
    Wind,
)


def _parse_wind(token: str) -> Wind:
    m = RE_WIND.match(token)
    if not m:
        raise ParseError(f"Invalid wind token: {token!r}", token, -1)
    dir_str, speed_str, _, gust_str, unit = m.groups()
    variable = dir_str == "VRB"
    direction = None if variable else int(dir_str)
    speed = int(speed_str)
    gust = int(gust_str) if gust_str else None
    return Wind(direction=direction, speed=speed, gust=gust, unit=unit, variable=variable)


def _parse_rvr(token: str) -> RVR:
    m = RE_RVR.match(token)
    if not m:
        raise ParseError(f"Invalid RVR token: {token!r}", token, -1)
    runway, op, val, _, op_max, val_max, trend = m.groups()
    return RVR(
        runway=runway,
        value=int(val),
        operator=op,
        value_max=int(val_max) if val_max else None,
        operator_max=op_max if val_max else None,
        trend=trend,
    )


def _parse_visibility(tokens: list[str], pos: int) -> tuple[Visibility, int]:
    token = tokens[pos]
    if token == "CAVOK":
        return Visibility(prevailing=None, unit="M", rvr=[]), pos + 1

    if RE_VIS.match(token):
        if token.endswith("SM"):
            unit = "SM"
            # statute miles: store raw string value as integer (no conversion)
            prevailing = None
        else:
            unit = "M"
            prevailing = int(token)
        pos += 1
    else:
        raise ParseError(f"Expected visibility token, got: {token!r}", token, pos)

    rvr_list: list[RVR] = []
    while pos < len(tokens) and tokens[pos].startswith("R") and RE_RVR.match(tokens[pos]):
        rvr_list.append(_parse_rvr(tokens[pos]))
        pos += 1

    return Visibility(prevailing=prevailing, unit=unit, rvr=rvr_list), pos


def _parse_weather(token: str) -> WeatherPhenomenon:
    m = RE_WEATHER.match(token)
    if not m:
        raise ParseError(f"Invalid weather token: {token!r}", token, -1)
    intensity = m.group(1)
    descriptor = m.group(2)
    # collect all phenomenon codes after descriptor
    rest = token
    if intensity:
        rest = rest[len(intensity):]
    if descriptor:
        rest = rest[len(descriptor):]
    # split rest into 2-char codes
    phenomena = [rest[i:i+2] for i in range(0, len(rest), 2)]
    return WeatherPhenomenon(intensity=intensity, descriptor=descriptor, phenomena=phenomena)


def _parse_cloud(token: str) -> CloudLayer:
    m = RE_CLOUD.match(token)
    if not m:
        raise ParseError(f"Invalid cloud token: {token!r}", token, -1)
    cover, height_str, cloud_type = m.groups()
    return CloudLayer(cover=cover, height=int(height_str), type=cloud_type)


def _parse_sky(tokens: list[str], pos: int) -> tuple[SkyCondition, int]:
    token = tokens[pos]
    m_special = RE_SKY_SPECIAL.match(token)
    if m_special:
        cavok = token == "CAVOK"
        nsc = token in ("NSC", "NCD")
        return SkyCondition(cavok=cavok, nsc=nsc, layers=[]), pos + 1

    layers: list[CloudLayer] = []
    while pos < len(tokens) and RE_CLOUD.match(tokens[pos]):
        layers.append(_parse_cloud(tokens[pos]))
        pos += 1
    return SkyCondition(cavok=False, nsc=False, layers=layers), pos


def _parse_temp(token: str) -> tuple[int, int]:
    m = RE_TEMP.match(token)
    if not m:
        raise ParseError(f"Invalid temp/dewpoint token: {token!r}", token, -1)
    return _temp_val(m.group(1)), _temp_val(m.group(2))


def _parse_qnh(token: str) -> tuple[int, str]:
    mq = RE_QNH_Q.match(token)
    if mq:
        return int(mq.group(1)), "hPa"
    ma = RE_QNH_A.match(token)
    if ma:
        return int(ma.group(1)), "inHg"
    raise ParseError(f"Invalid QNH token: {token!r}", token, -1)


_CHANGE_INDICATORS = {"BECMG", "TEMPO", "FM", "PROB30", "PROB40"}
_WEATHER_PREFIXES = {"-", "+", "VC"}
_DESCRIPTORS = {"MI", "BC", "PR", "DR", "BL", "SH", "TS", "FZ"}
_PHENOMENA = {"DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP",
              "BR", "FG", "FU", "VA", "DU", "SA", "HZ", "PO", "SQ", "FC", "SS", "DS"}


def _looks_like_weather(token: str) -> bool:
    return RE_WEATHER.match(token) is not None


def _parse_trend_time(token: str, ref_year: int, ref_month: int) -> datetime:
    from datetime import timezone
    m = RE_TREND_TIME.match(token)
    if not m:
        raise ParseError(f"Invalid trend time token: {token!r}", token, -1)
    day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(ref_year, ref_month, day, hour, minute, tzinfo=timezone.utc)


def _parse_trend(tokens: list[str], pos: int, ref_year: int, ref_month: int) -> tuple[TrendForecast | None, int]:
    if pos >= len(tokens):
        return None, pos

    tok = tokens[pos]
    if tok == "NOSIG":
        return TrendForecast(change_type="NOSIG"), pos + 1

    if tok not in ("BECMG", "TEMPO"):
        return None, pos

    change_type = tok
    pos += 1

    validity_from: datetime | None = None
    validity_to: datetime | None = None
    at: datetime | None = None

    # consume optional FM / TL / AT time indicators (single tokens: FM161300, TL161500, AT161400)
    while pos < len(tokens):
        tok = tokens[pos]
        mfm = RE_TREND_FM.match(tok)
        mtl = RE_TREND_TL.match(tok)
        mat = RE_TREND_AT.match(tok)
        if mfm:
            validity_from = datetime(ref_year, ref_month, int(mfm.group(1)), int(mfm.group(2)), int(mfm.group(3)), tzinfo=timezone.utc)
            pos += 1
        elif mtl:
            validity_to = datetime(ref_year, ref_month, int(mtl.group(1)), int(mtl.group(2)), int(mtl.group(3)), tzinfo=timezone.utc)
            pos += 1
        elif mat:
            at = datetime(ref_year, ref_month, int(mat.group(1)), int(mat.group(2)), int(mat.group(3)), tzinfo=timezone.utc)
            pos += 1
        else:
            break

    # parse forecast content (wind, vis, weather, sky) until end of tokens or RMK
    wind: Wind | None = None
    visibility: Visibility | None = None
    weather: list[WeatherPhenomenon] = []
    sky: SkyCondition | None = None

    while pos < len(tokens) and tokens[pos] != "RMK":
        tok = tokens[pos]
        if RE_WIND.match(tok):
            wind = _parse_wind(tok)
            pos += 1
            if pos < len(tokens) and RE_WIND_VAR.match(tokens[pos]):
                pos += 1
        elif tok == "CAVOK":
            visibility = Visibility(prevailing=None, unit="M", rvr=[])
            sky = SkyCondition(cavok=True, nsc=False, layers=[])
            pos += 1
        elif RE_VIS.match(tok):
            visibility, pos = _parse_visibility(tokens, pos)
        elif _looks_like_weather(tok):
            weather.append(_parse_weather(tok))
            pos += 1
        elif RE_SKY_SPECIAL.match(tok):
            nsc = tok in ("NSC", "NCD")
            sky = SkyCondition(cavok=False, nsc=nsc, layers=[])
            pos += 1
        elif RE_CLOUD.match(tok):
            if sky is None:
                sky = SkyCondition(cavok=False, nsc=False, layers=[])
            sky.layers.append(_parse_cloud(tok))
            pos += 1
        else:
            pos += 1  # skip unrecognised token

    return TrendForecast(
        change_type=change_type,
        validity_from=validity_from,
        validity_to=validity_to,
        at=at,
        wind=wind,
        visibility=visibility,
        weather=weather,
        sky=sky,
    ), pos


def parse_metar(raw: str) -> Metar:
    tokens = tokenize(raw)
    if not tokens:
        raise ParseError("Empty METAR string", "", 0)

    pos = 0
    now = datetime.now(tz=timezone.utc)
    ref_year, ref_month = now.year, now.month

    # message type
    msg_type = "METAR"
    if tokens[pos] in ("METAR", "SPECI"):
        msg_type = tokens[pos]
        pos += 1

    # station
    if pos >= len(tokens) or not RE_STATION.match(tokens[pos]):
        raise ParseError(f"Expected ICAO station, got: {tokens[pos]!r}", tokens[pos], pos)
    station = tokens[pos]
    pos += 1

    # time
    if pos >= len(tokens) or not RE_TIME.match(tokens[pos]):
        raise ParseError(f"Expected time token, got: {tokens[pos]!r}", tokens[pos], pos)
    obs_time = parse_time(tokens[pos], ref_year, ref_month)
    pos += 1

    # optional flags before wind
    auto = False
    cor = False
    while pos < len(tokens) and tokens[pos] in ("AUTO", "COR", "NIL"):
        if tokens[pos] == "AUTO":
            auto = True
        elif tokens[pos] == "COR":
            cor = True
        pos += 1

    # wind
    if pos >= len(tokens) or not RE_WIND.match(tokens[pos]):
        raise ParseError(f"Expected wind token, got: {tokens[pos]!r}", tokens[pos], pos)
    wind = _parse_wind(tokens[pos])
    pos += 1

    # optional variable wind direction (e.g. 180V240)
    if pos < len(tokens) and RE_WIND_VAR.match(tokens[pos]):
        pos += 1  # consume, not stored separately per spec

    # visibility
    if pos >= len(tokens):
        raise ParseError("Unexpected end of METAR after wind", "", pos)

    cavok_vis = tokens[pos] == "CAVOK"
    visibility, pos = _parse_visibility(tokens, pos)

    # weather phenomena (zero or more)
    weather: list[WeatherPhenomenon] = []
    while pos < len(tokens) and _looks_like_weather(tokens[pos]):
        weather.append(_parse_weather(tokens[pos]))
        pos += 1

    # sky condition (or CAVOK already consumed)
    if cavok_vis:
        sky = SkyCondition(cavok=True, nsc=False, layers=[])
    elif pos < len(tokens) and (RE_SKY_SPECIAL.match(tokens[pos]) or RE_CLOUD.match(tokens[pos])):
        sky, pos = _parse_sky(tokens, pos)
    else:
        sky = SkyCondition(cavok=False, nsc=False, layers=[])

    # temperature / dewpoint
    if pos >= len(tokens) or not RE_TEMP.match(tokens[pos]):
        raise ParseError(f"Expected temp/dewpoint token, got: {tokens[pos] if pos < len(tokens) else 'EOF'!r}", tokens[pos] if pos < len(tokens) else "", pos)
    temperature, dewpoint = _parse_temp(tokens[pos])
    pos += 1

    # QNH
    if pos >= len(tokens) or not (RE_QNH_Q.match(tokens[pos]) or RE_QNH_A.match(tokens[pos])):
        raise ParseError(f"Expected QNH token, got: {tokens[pos] if pos < len(tokens) else 'EOF'!r}", tokens[pos] if pos < len(tokens) else "", pos)
    qnh, qnh_unit = _parse_qnh(tokens[pos])
    pos += 1

    # trend forecast (NOSIG / BECMG / TEMPO) — appears before RMK
    trend, pos = _parse_trend(tokens, pos, ref_year, ref_month)

    # RMK
    rmk: str | None = None
    if pos < len(tokens) and tokens[pos] == "RMK":
        rmk = " ".join(tokens[pos + 1:])
        pos = len(tokens)

    return Metar(
        station=station,
        type=msg_type,
        time=obs_time,
        auto=auto,
        wind=wind,
        visibility=visibility,
        weather=weather,
        sky=sky,
        temperature=temperature,
        dewpoint=dewpoint,
        qnh=qnh,
        qnh_unit=qnh_unit,
        rmk=rmk,
        trend=trend,
    )
