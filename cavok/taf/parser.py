from datetime import UTC, datetime, timedelta

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
    RE_VALIDITY,
    RE_VIS,
    RE_WIND,
    RE_WIND_VAR,
    parse_time,
    tokenize,
)
from cavok.exceptions import ParseError
from cavok.metar.models import SkyCondition, Visibility
from cavok.metar.parser import (
    _looks_like_weather,
    _parse_cloud,
    _parse_rvr,
    _parse_weather,
    _parse_wind,
)
from cavok.taf.models import ChangeGroup, ForecastGroup, Taf

_CHANGE_KEYWORDS = {"BECMG", "TEMPO", "PROB30", "PROB40", "FM"}


def _parse_validity(
    token: str, ref_year: int, ref_month: int
) -> tuple[datetime, datetime]:
    m = RE_VALIDITY.match(token)
    if not m:
        raise ParseError(f"Invalid validity token: {token!r}", token, -1)
    from_day, from_hour, to_day, to_hour = (
        int(m.group(1)),
        int(m.group(2)),
        int(m.group(3)),
        int(m.group(4)),
    )
    # handle month rollover for to_day < from_day
    valid_from = datetime(ref_year, ref_month, from_day, from_hour, 0, tzinfo=UTC)
    to_month = ref_month
    to_year = ref_year
    if to_day < from_day:
        if ref_month == 12:
            to_month = 1
            to_year += 1
        else:
            to_month += 1
    # hour 24 means midnight next day
    if to_hour == 24:
        valid_to = datetime(to_year, to_month, to_day, 0, 0, tzinfo=UTC) + timedelta(
            days=1
        )
    else:
        valid_to = datetime(to_year, to_month, to_day, to_hour, 0, tzinfo=UTC)
    return valid_from, valid_to


def _parse_fm_time(token: str, ref_year: int, ref_month: int) -> datetime:
    m = RE_FM.match(token)
    if not m:
        raise ParseError(f"Invalid FM token: {token!r}", token, -1)
    day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(ref_year, ref_month, day, hour, minute, tzinfo=UTC)


def _parse_forecast_group(
    tokens: list[str],
    start: int,
    validity_from: datetime,
    validity_to: datetime,
) -> tuple[ForecastGroup, int]:
    pos = start
    wind = None
    visibility = None
    weather = []
    sky = None

    while pos < len(tokens) and tokens[pos] not in _CHANGE_KEYWORDS:
        tok = tokens[pos]

        if RE_WIND.match(tok):
            wind = _parse_wind(tok)
            pos += 1
            if pos < len(tokens) and RE_WIND_VAR.match(tokens[pos]):
                pos += 1
            continue

        if tok == "CAVOK":
            visibility = Visibility(prevailing=None, unit="M", rvr=[])
            sky = SkyCondition(cavok=True, nsc=False, layers=[])
            pos += 1
            continue

        if RE_VIS.match(tok):
            if tok.endswith("SM"):
                visibility = Visibility(prevailing=None, unit="SM", rvr=[])
            else:
                visibility = Visibility(prevailing=int(tok), unit="M", rvr=[])
            pos += 1
            while (
                pos < len(tokens)
                and tokens[pos].startswith("R")
                and RE_RVR.match(tokens[pos])
            ):
                if visibility.rvr is None:
                    visibility.rvr = []
                visibility.rvr.append(_parse_rvr(tokens[pos]))
                pos += 1
            continue

        if _looks_like_weather(tok):
            weather.append(_parse_weather(tok))
            pos += 1
            continue

        if RE_SKY_SPECIAL.match(tok):
            nsc = tok in ("NSC", "NCD")
            sky = SkyCondition(cavok=False, nsc=nsc, layers=[])
            pos += 1
            continue

        if RE_CLOUD.match(tok):
            if sky is None:
                sky = SkyCondition(cavok=False, nsc=False, layers=[])
            sky.layers.append(_parse_cloud(tok))
            pos += 1
            continue

        # QNH, TEMP tokens in TAF are uncommon but skip gracefully
        if RE_QNH_Q.match(tok) or RE_QNH_A.match(tok) or RE_TEMP.match(tok):
            pos += 1
            continue

        # unknown token — stop parsing this group
        break

    return ForecastGroup(
        validity_from=validity_from,
        validity_to=validity_to,
        wind=wind,
        visibility=visibility,
        weather=weather,
        sky=sky,
    ), pos


def _parse_change_groups(
    tokens: list[str],
    pos: int,
    ref_year: int,
    ref_month: int,
    taf_valid_to: datetime,
) -> tuple[list[ChangeGroup], int]:
    groups: list[ChangeGroup] = []

    while pos < len(tokens):
        tok = tokens[pos]

        if tok == "FM":
            pos += 1
            continue

        if RE_FM.match(tok):
            fm_from = _parse_fm_time(tok, ref_year, ref_month)
            pos += 1
            # validity_to = next change group start or taf end
            next_start = taf_valid_to
            for i in range(pos, len(tokens)):
                if RE_FM.match(tokens[i]) or tokens[i] in (
                    "BECMG",
                    "TEMPO",
                    "PROB30",
                    "PROB40",
                ):
                    t = tokens[i]
                    if RE_FM.match(t):
                        next_start = _parse_fm_time(t, ref_year, ref_month)
                    else:
                        # for BECMG/TEMPO we don't know the exact time, use taf end
                        next_start = taf_valid_to
                    break
            fg, pos = _parse_forecast_group(tokens, pos, fm_from, next_start)
            groups.append(ChangeGroup(change_type="FM", forecast=fg))
            continue

        if tok in ("BECMG", "TEMPO"):
            change_type = tok
            pos += 1
            if pos >= len(tokens) or not RE_VALIDITY.match(tokens[pos]):
                raise ParseError(
                    f"Expected validity after {change_type}",
                    tokens[pos] if pos < len(tokens) else "",
                    pos,
                )
            valid_from, valid_to = _parse_validity(tokens[pos], ref_year, ref_month)
            pos += 1
            fg, pos = _parse_forecast_group(tokens, pos, valid_from, valid_to)
            groups.append(ChangeGroup(change_type=change_type, forecast=fg))
            continue

        if tok in ("PROB30", "PROB40"):
            prob_type = tok
            pos += 1
            # optionally followed by TEMPO
            if pos < len(tokens) and tokens[pos] == "TEMPO":
                prob_type = f"{prob_type} TEMPO"
                pos += 1
            if pos >= len(tokens) or not RE_VALIDITY.match(tokens[pos]):
                raise ParseError(
                    f"Expected validity after {prob_type}",
                    tokens[pos] if pos < len(tokens) else "",
                    pos,
                )
            valid_from, valid_to = _parse_validity(tokens[pos], ref_year, ref_month)
            pos += 1
            fg, pos = _parse_forecast_group(tokens, pos, valid_from, valid_to)
            groups.append(ChangeGroup(change_type=prob_type, forecast=fg))
            continue

        pos += 1  # skip unrecognised token

    return groups, pos


def parse_taf(raw: str) -> Taf:
    tokens = tokenize(raw)
    if not tokens:
        raise ParseError("Empty TAF string", "", 0)

    pos = 0
    now = datetime.now(tz=UTC)
    ref_year, ref_month = now.year, now.month

    if tokens[pos] == "TAF":
        pos += 1

    # optional AMD/CNL/COR flags (may appear before or after TAF keyword)
    amd = cor = cnl = False
    while pos < len(tokens) and tokens[pos] in ("AMD", "COR", "CNL"):
        if tokens[pos] == "AMD":
            amd = True
        elif tokens[pos] == "COR":
            cor = True
        elif tokens[pos] == "CNL":
            cnl = True
        pos += 1

    # station
    if pos >= len(tokens) or not RE_STATION.match(tokens[pos]):
        raise ParseError(
            f"Expected ICAO station, got: {tokens[pos]!r}", tokens[pos], pos
        )
    station = tokens[pos]
    pos += 1

    # issue time
    if pos >= len(tokens) or not RE_TIME.match(tokens[pos]):
        raise ParseError(f"Expected issue time, got: {tokens[pos]!r}", tokens[pos], pos)
    issued_at = parse_time(tokens[pos], ref_year, ref_month)
    pos += 1

    # validity window
    if pos >= len(tokens) or not RE_VALIDITY.match(tokens[pos]):
        raise ParseError(
            f"Expected validity window, got: {tokens[pos] if pos < len(tokens) else 'EOF'!r}",
            tokens[pos] if pos < len(tokens) else "",
            pos,
        )
    valid_from, valid_to = _parse_validity(tokens[pos], ref_year, ref_month)
    pos += 1

    # CNL — no forecast groups follow
    if cnl:
        return Taf(
            station=station,
            issued_at=issued_at,
            valid_from=valid_from,
            valid_to=valid_to,
            amd=amd,
            cnl=True,
            cor=cor,
            base=ForecastGroup(valid_from, valid_to, None, None),
            changes=[],
        )

    # base forecast group
    base, pos = _parse_forecast_group(tokens, pos, valid_from, valid_to)

    # change groups
    changes, pos = _parse_change_groups(tokens, pos, ref_year, ref_month, valid_to)

    return Taf(
        station=station,
        issued_at=issued_at,
        valid_from=valid_from,
        valid_to=valid_to,
        amd=amd,
        cnl=cnl,
        cor=cor,
        base=base,
        changes=changes,
    )
