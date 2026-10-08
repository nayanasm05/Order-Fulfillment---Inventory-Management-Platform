from sqlalchemy.orm import Session

from app.models import Product


def get_product_by_id(
    db: Session,
    product_id: int,
):
    return db.query(Product).filter(
        Product.id == product_id
    ).first()


def get_product_by_sku(
    db: Session,
    sku: str,
):
    return db.query(Product).filter(
        Product.sku == sku
    ).first()


def get_products(
    db: Session,
):
    return db.query(Product).order_by(
        Product.id.desc()
    ).all()


def create_product(
    db: Session,
    product: Product,
):
    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def update_product(
    db: Session,
    product: Product,
):
    db.commit()
    db.refresh(product)

    return product


def delete_product(
    db: Session,
    product: Product,
):
    db.delete(product)
    db.commit()