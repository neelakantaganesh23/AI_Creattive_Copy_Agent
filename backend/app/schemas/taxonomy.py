"""Schemas for brands, products, audience segments, CTA rules and templates."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Channel


class BrandBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    guidelines: str | None = Field(default=None, max_length=4000)
    is_active: bool = True


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    guidelines: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None


class BrandResponse(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProductBase(BaseModel):
    brand_id: int
    name: str = Field(min_length=2, max_length=160)
    sku: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=2000)
    features: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    brand_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=160)
    sku: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=2000)
    features: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_name: str | None = None
    created_at: datetime
    updated_at: datetime


class AudienceSegmentBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    tone_guidance: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class AudienceSegmentCreate(AudienceSegmentBase):
    pass


class AudienceSegmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    tone_guidance: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class AudienceSegmentResponse(AudienceSegmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CTARuleBase(BaseModel):
    brand_id: int | None = None
    product_id: int | None = None
    channel: Channel | None = None
    template: str = Field(min_length=2, max_length=160)
    priority: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True


class CTARuleCreate(CTARuleBase):
    pass


class CTARuleUpdate(BaseModel):
    brand_id: int | None = None
    product_id: int | None = None
    channel: Channel | None = None
    template: str | None = Field(default=None, min_length=2, max_length=160)
    priority: int | None = Field(default=None, ge=0, le=1000)
    is_active: bool | None = None


class CTARuleResponse(CTARuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class TemplateBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    channel: Channel
    description: str | None = Field(default=None, max_length=2000)
    prompt_template: str = Field(min_length=10, max_length=8000)
    is_active: bool = True


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    channel: Channel | None = None
    description: str | None = Field(default=None, max_length=2000)
    prompt_template: str | None = Field(default=None, min_length=10, max_length=8000)
    is_active: bool | None = None


class TemplateResponse(TemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
