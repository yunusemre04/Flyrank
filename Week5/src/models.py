from typing import Optional

from pydantic import BaseModel, field_validator


class RawBookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str


class BookRecord(RawBookRecord):
    price_gbp: float

    @field_validator("product_url")
    @classmethod
    def require_https_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("product_url must start with https://")
        return value


class ValidationErrorRecord(BaseModel):
    record: dict
    error: str
    timestamp: str
