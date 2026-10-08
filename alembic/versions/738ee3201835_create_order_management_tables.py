"""create order management tables

Revision ID: 738ee3201835
Revises: 40aaccaf906b
Create Date: 2026-10-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision: str = "738ee3201835"
down_revision: Union[str, Sequence[str], None] = "40aaccaf906b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade() -> None:

    # ========================================================
    # FIX EXISTING INVENTORY TABLE
    # ========================================================
    # Existing inventory records may already exist.
    # Therefore reorder_level is temporarily given
    # a server default of 0 before removing the default.

    op.add_column(
        "inventory",
        sa.Column(
            "reorder_level",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.alter_column(
        "inventory",
        "reorder_level",
        server_default=None,
    )

    # ========================================================
    # ORDERS
    # ========================================================

    op.create_table(
        "orders",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "order_number",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "customer_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "warehouse_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "subtotal",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "discount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "tax",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "total_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="Pending",
        ),

        sa.Column(
            "payment_status",
            sa.String(length=50),
            nullable=False,
            server_default="Pending",
        ),

        sa.Column(
            "expected_delivery",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
        ),

        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "order_number",
            name="uq_orders_order_number",
        ),
    )

    # ========================================================
    # ORDERS INDEXES
    # ========================================================

    op.create_index(
        "ix_orders_id",
        "orders",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_orders_order_number",
        "orders",
        ["order_number"],
        unique=True,
    )

    op.create_index(
        "ix_orders_customer_id",
        "orders",
        ["customer_id"],
        unique=False,
    )

    op.create_index(
        "ix_orders_warehouse_id",
        "orders",
        ["warehouse_id"],
        unique=False,
    )

    op.create_index(
        "ix_orders_status",
        "orders",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_orders_payment_status",
        "orders",
        ["payment_status"],
        unique=False,
    )

    op.create_index(
        "ix_orders_created_at",
        "orders",
        ["created_at"],
        unique=False,
    )

    # ========================================================
    # ORDER ITEMS
    # ========================================================

    op.create_table(
        "order_items",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "order_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "unit_price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),

        sa.Column(
            "discount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "tax",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "total_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "order_id",
            "product_id",
            name="uq_order_product",
        ),
    )

    # ========================================================
    # ORDER ITEM INDEXES
    # ========================================================

    op.create_index(
        "ix_order_items_id",
        "order_items",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_order_items_order_id",
        "order_items",
        ["order_id"],
        unique=False,
    )

    op.create_index(
        "ix_order_items_product_id",
        "order_items",
        ["product_id"],
        unique=False,
    )

    # ========================================================
    # ORDER STATUS HISTORY
    # ========================================================

    op.create_table(
        "order_status_history",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "order_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "old_status",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "new_status",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "changed_by",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "reason",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    # ========================================================
    # ORDER STATUS HISTORY INDEXES
    # ========================================================

    op.create_index(
        "ix_order_status_history_id",
        "order_status_history",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_order_status_history_order_id",
        "order_status_history",
        ["order_id"],
        unique=False,
    )

    op.create_index(
        "ix_order_status_history_changed_by",
        "order_status_history",
        ["changed_by"],
        unique=False,
    )

    op.create_index(
        "ix_order_status_history_new_status",
        "order_status_history",
        ["new_status"],
        unique=False,
    )

    op.create_index(
        "ix_order_status_history_created_at",
        "order_status_history",
        ["created_at"],
        unique=False,
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade() -> None:

    # Remove order status history
    op.drop_index(
        "ix_order_status_history_created_at",
        table_name="order_status_history",
    )

    op.drop_index(
        "ix_order_status_history_new_status",
        table_name="order_status_history",
    )

    op.drop_index(
        "ix_order_status_history_changed_by",
        table_name="order_status_history",
    )

    op.drop_index(
        "ix_order_status_history_order_id",
        table_name="order_status_history",
    )

    op.drop_index(
        "ix_order_status_history_id",
        table_name="order_status_history",
    )

    op.drop_table("order_status_history")

    # Remove order items
    op.drop_index(
        "ix_order_items_product_id",
        table_name="order_items",
    )

    op.drop_index(
        "ix_order_items_order_id",
        table_name="order_items",
    )

    op.drop_index(
        "ix_order_items_id",
        table_name="order_items",
    )

    op.drop_table("order_items")

    # Remove orders
    op.drop_index(
        "ix_orders_created_at",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_payment_status",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_status",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_warehouse_id",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_customer_id",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_order_number",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_id",
        table_name="orders",
    )

    op.drop_table("orders")

    # Remove reorder_level from inventory
    op.drop_column(
        "inventory",
        "reorder_level",
    )