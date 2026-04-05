"""Pydantic models for search requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SortField = Literal[
    "relevance",
    "price",
    "rating",
    "review_count",
    "stock",
    "created_at",
    "publication_year",
    "page_count",
    "name",
]

SortOrder = Literal["asc", "desc"]


class SearchFilters(BaseModel):
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    author: str | None = None
    publisher: str | None = None
    publication_year_min: int | None = Field(default=None, ge=0)
    publication_year_max: int | None = Field(default=None, ge=0)
    language: str | None = None
    cover_type: str | None = None
    page_count_min: int | None = Field(default=None, ge=0)
    page_count_max: int | None = Field(default=None, ge=0)
    in_stock: bool | None = None


class SearchSort(BaseModel):
    field: SortField = "relevance"
    order: SortOrder = "desc"


class SearchPagination(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)
    total: int = 0
    total_pages: int = 0


class SearchRequest(BaseModel):
    query: str = Field(default="")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    sort: SearchSort = Field(default_factory=SearchSort)
    pagination: SearchPagination = Field(default_factory=SearchPagination)


class SearchProduct(BaseModel):
    product_id: str
    name: str
    normalized_name: str | None = None
    price: int | None = None
    rating: float | None = None
    review_count: int | None = None
    stock: int | None = None
    category: str | None = None
    content: str | None = None
    author: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    cover_type: str | None = None
    page_count: int | None = None
    created_at: datetime | None = None
    relevance_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    filters: SearchFilters
    sort: SearchSort
    pagination: SearchPagination
    total: int
    items: list[SearchProduct]
    llm_context: str
