"""create inventory table

Revision ID: cf6458a31ffc
Revises: 35ac351beba5
Create Date: 2026-09-30 13:53:20.676624

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cf6458a31ffc"
down_revision: Union[str, Sequence[str], None] = "35ac351beba5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create inventory table."""

    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reserved_quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_inventory_id"),
        "inventory",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_product_id"),
        "inventory",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_warehouse_id"),
        "inventory",
        ["warehouse_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop inventory table."""

    op.drop_index(
        op.f("ix_inventory_warehouse_id"),
        table_name="inventory",
    )

    op.drop_index(
        op.f("ix_inventory_product_id"),
        table_name="inventory",
    )

    op.drop_index(
        op.f("ix_inventory_id"),
        table_name="inventory",
    )

    op.drop_table("inventory")