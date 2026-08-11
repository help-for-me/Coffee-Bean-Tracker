from datetime import date, datetime
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

EntryType = Literal["bag", "cafe_cup"]
CoFermentStatus = Literal["yes", "no", "unknown"]
BrewStyle = Literal["Pour Over", "Espresso", "French Press", "Cafe-made", "Other"]
Repurchase = Literal["yes", "no", "maybe"]
WindowType = Literal["all_time", "recent"]
EntrySort = Literal["date_desc", "date_asc", "score_desc", "score_asc"]


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
    # Required for cafe cups (nothing else identifies them) and for bags
    # with no photo. A bag entry with at least one photo and no typed
    # identity gets a provisional bean profile instead - enforced at the
    # router, not here, since photos aren't part of this JSON body.
    roaster: Optional[str] = None
    bean_name: Optional[str] = None
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


class EntryUpdate(BaseModel):
    # Manual correction UI (0.7.0) - every field optional, and unlike
    # apply_extraction_result's COALESCE-skip-nulls merge, an explicit null
    # here means "clear this field" (see crud.update_entry / exclude_unset).
    # Identity (roaster/bean_name) isn't editable here - that's bean_profile
    # resolution logic, out of scope for this milestone.
    cafe_name: Optional[str] = None
    entry_date: Optional[date] = None
    price_paid: Optional[float] = None
    currency: Optional[str] = None
    origin_country: Optional[str] = None
    region: Optional[str] = None
    farm_producer: Optional[str] = None
    altitude_m: Optional[int] = None
    variety: Optional[str] = None
    process: Optional[str] = None
    co_ferment_status: Optional[CoFermentStatus] = None
    co_ferment_ingredient: Optional[str] = None
    certifications: Optional[str] = None
    roast_level: Optional[str] = None
    printed_tasting_notes: Optional[str] = None
    roast_date: Optional[date] = None
    bag_weight_g: Optional[int] = None
    batch_number: Optional[str] = None
    roast_location: Optional[str] = None


class RatingUpdate(BaseModel):
    score: Optional[float] = Field(default=None, ge=0, le=10)
    narrative_notes: Optional[str] = None
    acidity_score: Optional[float] = Field(default=None, ge=0, le=10)
    body_score: Optional[float] = Field(default=None, ge=0, le=10)
    sweetness_score: Optional[float] = Field(default=None, ge=0, le=10)
    brew_style: Optional[BrewStyle] = None
    repurchase: Optional[Repurchase] = None


class BeanProfileOut(BaseModel):
    id: int
    roaster: str
    bean_name: str
    is_provisional: bool


class FarmOut(BaseModel):
    farm_name: str
    location: Optional[str] = None


class PhotoOut(BaseModel):
    id: int
    entry_id: int
    upload_order: Optional[int]
    date_entered: datetime


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
    photos: list[PhotoOut]
    related_photos: list[PhotoOut]
    ratings: list[RatingOut]


class EntrySummary(BaseModel):
    id: int
    roaster: str
    bean_name: str
    is_provisional: bool
    entry_type: EntryType
    entry_date: Optional[date]
    date_entered: datetime
    extraction_status: str
    latest_score: Optional[float]


class ProcessStat(BaseModel):
    process: str
    avg_score: float
    count: int
    adjusted_score: float


class MonthlyStat(BaseModel):
    month: str
    avg_score: float
    count: int


class OriginCountryStat(BaseModel):
    origin_country: str
    avg_score: float
    count: int
    adjusted_score: float


class TastingNoteStat(BaseModel):
    note: str
    avg_score: float
    count: int
    adjusted_score: float


class BrewStyleStat(BaseModel):
    brew_style: str
    avg_score: float
    count: int
    adjusted_score: float


class SignificanceResult(BaseModel):
    # Welch's t-test between the top two items in a ranking (see
    # backend/insights/stats.py) - comparable=False means there wasn't
    # even enough data to run the test (fewer than 2 groups, or fewer than
    # 2 ratings on one side); significant=False means the gap between the
    # top two could plausibly just be noise, not a real preference.
    comparable: bool
    p_value: Optional[float]
    significant: Optional[bool]
    message: str


T = TypeVar("T")


class Ranking(BaseModel, Generic[T]):
    items: list[T]
    significance: SignificanceResult


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
    all_time: Ranking[ProcessStat]
    recent: Ranking[ProcessStat]


class ByOriginCountry(BaseModel):
    all_time: Ranking[OriginCountryStat]
    recent: Ranking[OriginCountryStat]


class ByTastingNote(BaseModel):
    all_time: Ranking[TastingNoteStat]
    recent: Ranking[TastingNoteStat]


class ByBrewStyle(BaseModel):
    all_time: Ranking[BrewStyleStat]
    recent: Ranking[BrewStyleStat]


class MostRepurchased(BaseModel):
    all_time: list[RepurchasedItem]
    recent: list[RepurchasedItem]


class InsightsOut(BaseModel):
    monthly_trend: list[MonthlyStat]
    by_process: ByProcess
    by_origin_country: ByOriginCountry
    by_tasting_note: ByTastingNote
    by_brew_style: ByBrewStyle
    most_repurchased: MostRepurchased
    recent_window: RecentWindow


class InsightNarrativeOut(BaseModel):
    id: int
    window_type: WindowType
    summary_text: str
    generated_at: datetime
