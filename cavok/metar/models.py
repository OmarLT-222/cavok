from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Wind:
    direction: int | None
    speed: int
    gust: int | None
    unit: str
    variable: bool


@dataclass
class RVR:
    runway: str
    value: int
    operator: str | None
    value_max: int | None
    operator_max: str | None
    trend: str | None


@dataclass
class Visibility:
    prevailing: int | None
    unit: str
    rvr: list[RVR] = field(default_factory=list)


@dataclass
class WeatherPhenomenon:
    intensity: str | None
    descriptor: str | None
    phenomena: list[str] = field(default_factory=list)


@dataclass
class CloudLayer:
    cover: str
    height: int
    type: str | None


@dataclass
class SkyCondition:
    cavok: bool
    nsc: bool
    layers: list[CloudLayer] = field(default_factory=list)


@dataclass
class Metar:
    station: str
    time: datetime
    auto: bool
    wind: Wind
    visibility: Visibility
    weather: list[WeatherPhenomenon]
    sky: SkyCondition
    temperature: int
    dewpoint: int
    qnh: int
    qnh_unit: str
    rmk: str | None
