from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EntryType = Literal["bag", "cafe_cup"]
CoFermentStatus = Literal["yes", "no", "unknown"]
BrewStyle = Literal["Pour Over", "Espresso", "French Press", "Cafe-made", "Other"]
Repurchase = Literal["yes", "no", "maybe"]


class RatingFields(BaseModel):
    score: float = Field(ge=0, le=10)
    narrative_notes: Optional[str] = None
    acidity_score: Optional[float] = Field(default=None, ge=0, le=10)
    body_score: Optional[float] = Field(default=None, ge=0, le=10)
    sweetness_score: Optional[float] = Field(default=None, ge=0, le=10)
    brew_style: Optional[BrewStyle] = None
    repurchase: Optional[Repurchase] = None


class EntryCreate(RatingFields):
    entry_type: EntryType
    roaster: str
    bean_name: str
    cafe_name: Optional[str] = None
    entry_date: Optional[date] = None
    price_paid: Optional[float] = None
    currency: str = "CAD"

    origin_country: Optional[str] = None
    region: Optional[str] = None
    farm_producer: Optional[str] = None
    altitude_m: Optional[int] = None
    variety: Optional[str] = None
    process: Optional[str] = None
    co_ferment_status: CoFermentStatus = "unknown"
    co_ferment_ingredient: Optional[str] = None
    certifications: Optional[str] = None
    roast_level: Optional[str] = None
    printed_tasting_notes: Optional[str] = None
    roast_date: Optional[date] = None
    bag_weight_g: Optional[int] = None
    batch_number: Optional[str] = None
    roast_location: Optional[str] = None


class RatingCreate(RatingFields):
    pass


class BeanProfileOut(BaseModel):
    id: int
    roaster: str
    bean_name: str


class FarmOut(BaseModel):
    farm_name: str
    location: Optional[str] = None


class RatingOut(RatingFields):
    id: int
    entry_id: int
    date_entered: datetime


class EntryOut(BaseModel):
    id: int
    bean_profile: BeanProfileOut
    entry_type: EntryType
    cafe_name: Optional[str]
    entry_date: Optional[date]
    date_entered: datetime
    price_paid: Optional[float]
    currency: str
    extraction_status: str
    extraction_source: Optional[str]
    origin_country: Optional[str]
    region: Optional[str]
    farm_producer: Optional[str]
    altitude_m: Optional[int]
    variety: Optional[str]
    process: Optional[str]
    co_ferment_status: str
    co_ferment_ingredient: Optional[str]
    certifications: Optional[str]
    roast_level: Optional[str]
    printed_tasting_notes: Optional[str]
    roast_date: Optional[date]
    bag_weight_g: Optional[int]
    batch_number: Optional[str]
    roast_location: Optional[str]
    farms: list[FarmOut]
    ratings: list[RatingOut]


class EntrySummary(BaseModel):
    id: int
    roaster: str
    bean_name: str
    entry_type: EntryType
    entry_date: Optional[date]
    date_entered: datetime
    extraction_status: str
    latest_score: Optional[float]


class ProcessStat(BaseModel):
    process: str
    avg_score: float
    count: int


class MonthlyStat(BaseModel):
    month: str
    avg_score: float
    count: int


class OriginCountryStat(BaseModel):
    origin_country: str
    avg_score: float
    count: int


class TastingNoteStat(BaseModel):
    note: str
    avg_score: float
    count: int


class RepurchasedItem(BaseModel):
    roaster: str
    bean_name: str
    entry_count: int
    avg_score: float
    trend: Literal["up", "down", "flat"]


class RecentWindow(BaseModel):
    applicable: bool
    cutoff_date: Optional[date]


class ByProcess(BaseModel):
    all_time: list[ProcessStat]
    recent: list[ProcessStat]


class ByOriginCountry(BaseModel):
    all_time: list[OriginCountryStat]
    recent: list[OriginCountryStat]


class ByTastingNote(BaseModel):
    all_time: list[TastingNoteStat]
    recent: list[TastingNoteStat]


class MostRepurchased(BaseModel):
    all_time: list[RepurchasedItem]
    recent: list[RepurchasedItem]


class InsightsOut(BaseModel):
    monthly_trend: list[MonthlyStat]
    by_process: ByProcess
    by_origin_country: ByOriginCountry
    by_tasting_note: ByTastingNote
    most_repurchased: MostRepurchased
    recent_window: RecentWindow
