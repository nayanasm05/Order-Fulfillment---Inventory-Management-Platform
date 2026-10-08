from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Product, User

from app.schemas import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

from app.services.product_service import (
    create_new_product,
    get_product,
    update_existing_product,
)

from app.repositories.product_repository import get_products


router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_new_product(
        db=db,
        sku=product_data.sku,
        name=product_data.name,
        description=product_data.description,
        category=product_data.category,
        price=product_data.price,
    )


@router.get(
    "",
    response_model=list[ProductResponse],
)
def list_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_products(db)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_product(
        db=db,
        product_id=product_id,
    )


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_existing_product(
        db=db,
        product_id=product_id,
        name=product_data.name,
        description=product_data.description,
        category=product_data.category,
        price=product_data.price,
        is_active=product_data.is_active,
    )


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
)
def deactivate_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = get_product(
        db=db,
        product_id=product_id,
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is already inactive",
        )

    product.is_active = False

    db.commit()
    db.refresh(product)

    return product


@router.patch(
    "/{product_id}/activate",
)
def activate_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is already active",
        )

    product.is_active = True

    db.commit()
    db.refresh(product)

    return {
        "message": "Product activated successfully",
        "product_id": product.id,
        "is_active": product.is_active,
    }