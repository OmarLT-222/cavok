from dataclasses import dataclass, field
from datetime import datetime

from cavok.metar.models import SkyCondition, Visibility, WeatherPhenomenon, Wind


@dataclass
class ForecastGroup:
    validity_from: datetime
    validity_to: datetime
    wind: Wind | None
    visibility: Visibility | None
    weather: list[WeatherPhenomenon] = field(default_factory=list)
    sky: SkyCondition | None = None


@dataclass
class ChangeGroup:
    change_type: str
    forecast: ForecastGroup


@dataclass
class Taf:
    station: str
    issued_at: datetime
    valid_from: datetime
    valid_to: datetime
    amd: bool
    cnl: bool
    cor: bool
    base: ForecastGroup
    changes: list[ChangeGroup] = field(default_factory=list)
