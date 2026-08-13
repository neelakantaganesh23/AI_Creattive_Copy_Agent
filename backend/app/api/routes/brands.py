"""Brand and product management (§11). Mutations are admin-only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Pagination, RequireAdmin, paginate_response
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.taxonomy_repository import BrandRepository, ProductRepository
from app.schemas.common import MessageResponse, Page
from app.schemas.taxonomy import (
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

brands_router = APIRouter(prefix="/brands", tags=["Brands"])
products_router = APIRouter(prefix="/products", tags=["Products"])


@brands_router.get("", response_model=Page[BrandResponse], summary="List brands")
def list_brands(
    session: DbSession,
    _user: CurrentUser,
    pagination: Pagination,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[BrandResponse]:
    items, total = BrandRepository(session).list(
        offset=pagination.offset,
        limit=pagination.page_size,
        is_active=is_active,
        order_by="name",
    )
    return Page[BrandResponse].model_validate(
        paginate_response([BrandResponse.model_validate(item) for item in items], total, pagination)
    )


@brands_router.post(
    "", response_model=BrandResponse, status_code=status.HTTP_201_CREATED, summary="Create a brand"
)
def create_brand(payload: BrandCreate, session: DbSession, _user: RequireAdmin) -> BrandResponse:
    repo = BrandRepository(session)
    if repo.get_by_name(payload.name):
        raise ConflictError("A brand with this name already exists.")
    brand = repo.create(**payload.model_dump())
    session.commit()
    return BrandResponse.model_validate(brand)


@brands_router.get("/{brand_id}", response_model=BrandResponse, summary="Brand detail")
def get_brand(brand_id: int, session: DbSession, _user: CurrentUser) -> BrandResponse:
    brand = BrandRepository(session).get(brand_id)
    if brand is None:
        raise NotFoundError("Brand not found.")
    return BrandResponse.model_validate(brand)


@brands_router.put("/{brand_id}", response_model=BrandResponse, summary="Update a brand")
def update_brand(
    brand_id: int, payload: BrandUpdate, session: DbSession, _user: RequireAdmin
) -> BrandResponse:
    repo = BrandRepository(session)
    brand = repo.get(brand_id)
    if brand is None:
        raise NotFoundError("Brand not found.")
    values = payload.model_dump(exclude_unset=True)
    if "name" in values:
        existing = repo.get_by_name(values["name"])
        if existing and existing.id != brand_id:
            raise ConflictError("A brand with this name already exists.")
    repo.update(brand, **values)
    session.commit()
    return BrandResponse.model_validate(brand)


@brands_router.delete("/{brand_id}", response_model=MessageResponse, summary="Delete a brand")
def delete_brand(brand_id: int, session: DbSession, _user: RequireAdmin) -> MessageResponse:
    repo = BrandRepository(session)
    brand = repo.get(brand_id)
    if brand is None:
        raise NotFoundError("Brand not found.")
    repo.delete(brand)
    session.commit()
    return MessageResponse(message="Brand deleted.")


def _to_product_response(product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        brand_id=product.brand_id,
        name=product.name,
        sku=product.sku,
        description=product.description,
        features=product.features,
        is_active=product.is_active,
        brand_name=product.brand.name if product.brand else None,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@products_router.get("", response_model=Page[ProductResponse], summary="List products")
def list_products(
    session: DbSession,
    _user: CurrentUser,
    pagination: Pagination,
    brand_id: Annotated[int | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[ProductResponse]:
    items, total = ProductRepository(session).list(
        offset=pagination.offset,
        limit=pagination.page_size,
        is_active=is_active,
        order_by="name",
        filters={"brand_id": brand_id},
    )
    return Page[ProductResponse].model_validate(
        paginate_response([_to_product_response(item) for item in items], total, pagination)
    )


@products_router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
def create_product(
    payload: ProductCreate, session: DbSession, _user: RequireAdmin
) -> ProductResponse:
    if BrandRepository(session).get(payload.brand_id) is None:
        raise ValidationError("The selected brand does not exist.")
    product = ProductRepository(session).create(**payload.model_dump())
    session.commit()
    return _to_product_response(product)


@products_router.get("/{product_id}", response_model=ProductResponse, summary="Product detail")
def get_product(product_id: int, session: DbSession, _user: CurrentUser) -> ProductResponse:
    product = ProductRepository(session).get(product_id)
    if product is None:
        raise NotFoundError("Product not found.")
    return _to_product_response(product)


@products_router.put("/{product_id}", response_model=ProductResponse, summary="Update a product")
def update_product(
    product_id: int, payload: ProductUpdate, session: DbSession, _user: RequireAdmin
) -> ProductResponse:
    repo = ProductRepository(session)
    product = repo.get(product_id)
    if product is None:
        raise NotFoundError("Product not found.")
    values = payload.model_dump(exclude_unset=True)
    if values.get("brand_id") and BrandRepository(session).get(values["brand_id"]) is None:
        raise ValidationError("The selected brand does not exist.")
    repo.update(product, **values)
    session.commit()
    return _to_product_response(product)


@products_router.delete(
    "/{product_id}", response_model=MessageResponse, summary="Delete a product"
)
def delete_product(product_id: int, session: DbSession, _user: RequireAdmin) -> MessageResponse:
    repo = ProductRepository(session)
    product = repo.get(product_id)
    if product is None:
        raise NotFoundError("Product not found.")
    repo.delete(product)
    session.commit()
    return MessageResponse(message="Product deleted.")
