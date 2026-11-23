import re
from datetime import UTC, datetime

from cavok.exceptions import ParseError

RE_STATION = re.compile(r"^[A-Z]{4}$")
RE_TIME = re.compile(r"^(\d{2})(\d{2})(\d{2})Z$")
RE_WIND = re.compile(r"^(VRB|\d{3})(\d{2,3})(G(\d{2,3}))?(KT|MPS)$")
RE_WIND_VAR = re.compile(r"^(\d{3})V(\d{3})$")
RE_VIS = re.compile(r"^(\d{4}|CAVOK|9999|M?(\d+\s)?\d+/\d+SM|\d+SM)$")
RE_RVR = re.compile(r"^R(\w+)/(M|P)?(\d{3,4})(V(M|P)?(\d{3,4}))?([UDN])?$")
RE_WEATHER = re.compile(
    r"^(-|\+|VC)?"
    r"(MI|BC|PR|DR|BL|SH|TS|FZ)?"
    r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)"
    r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)*$"
)
RE_CLOUD = re.compile(r"^(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?$")
RE_SKY_SPECIAL = re.compile(r"^(CAVOK|NSC|SKC|CLR|NCD)$")
RE_TEMP = re.compile(r"^(M?\d{2})/(M?\d{2})$")
RE_QNH_Q = re.compile(r"^Q(\d{4})$")
RE_QNH_A = re.compile(r"^A(\d{4})$")
RE_VALIDITY = re.compile(r"^(\d{2})(\d{2})/(\d{2})(\d{2})$")
RE_FM = re.compile(r"^FM(\d{2})(\d{2})(\d{2})$")
RE_TREND_TIME = re.compile(
    r"^(\d{2})(\d{2})(\d{2})$"
)  # DDHHmm, no Z — trend FM/TL/AT indicator
RE_TREND_FM = re.compile(r"^FM(\d{2})(\d{2})(\d{2})$")
RE_TREND_TL = re.compile(r"^TL(\d{2})(\d{2})(\d{2})$")
RE_TREND_AT = re.compile(r"^AT(\d{2})(\d{2})(\d{2})$")


def tokenize(raw: str) -> list[str]:
    return raw.strip().rstrip("=").split()


def parse_time(token: str, ref_year: int, ref_month: int) -> datetime:
    m = RE_TIME.match(token)
    if not m:
        raise ParseError(f"Invalid time token: {token!r}", token, -1)
    day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(ref_year, ref_month, day, hour, minute, tzinfo=UTC)


def _temp_val(s: str) -> int:
    if s.startswith("M"):
        return -int(s[1:])
    return int(s)
