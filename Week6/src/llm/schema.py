from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EnrichRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=4000)
    price_gbp: float = Field(ge=0)
    rating_text: str = Field(min_length=1, max_length=20)
    availability_text: str = Field(min_length=1, max_length=200)


class Category(str, Enum):
    fiction = "fiction"
    nonfiction = "nonfiction"
    poetry = "poetry"
    biography = "biography"
    childrens = "childrens"
    other = "other"


class QualityFlag(str, Enum):
    missing_description = "missing_description"
    very_short_description = "very_short_description"
    price_looks_off = "price_looks_off"
    rating_unclear = "rating_unclear"
    llm_disabled = "llm_disabled"
    none_ = "none"


class EnrichResponse(BaseModel):
    category: Category
    summary: str = Field(min_length=1, max_length=240)
    quality_flags: List[QualityFlag]
    confidence: float = Field(ge=0.0, le=1.0)
