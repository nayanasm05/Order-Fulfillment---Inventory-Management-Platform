from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Product
from app.repositories.product_repository import (
    create_product,
    get_product_by_id,
    get_product_by_sku,
    update_product,
)


def create_new_product(
    db: Session,
    sku: str,
    name: str,
    description: str | None,
    category: str | None,
    price: float,
):
    existing_product = get_product_by_sku(db, sku)

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product SKU already exists",
        )

    product = Product(
        sku=sku,
        name=name,
        description=description,
        category=category,
        price=price,
    )

    return create_product(db, product)


def get_product(
    db: Session,
    product_id: int,
):
    product = get_product_by_id(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


def update_existing_product(
    db: Session,
    product_id: int,
    name: str | None = None,
    description: str | None = None,
    category: str | None = None,
    price: float | None = None,
    is_active: bool | None = None,
):
    product = get_product_by_id(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if name is not None:
        product.name = name

    if description is not None:
        product.description = description

    if category is not None:
        product.category = category

    if price is not None:
        product.price = price

    if is_active is not None:
        product.is_active = is_active

    return update_product(db, product)