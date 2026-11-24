"""Expand deals for the full DealForge pipeline.

Revision ID: d4a12c87f901
Revises: 90b63c30d37a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4a12c87f901"
down_revision: Union[str, None] = "90b63c30d37a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("deals") as batch_op:
        batch_op.add_column(sa.Column("company_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("industry", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("sector", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("deal_type", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("transaction_size", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(sa.Column("revenue", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(sa.Column("ebitda", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(sa.Column("funding_requirement", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(sa.Column("target_valuation", sa.Numeric(18, 2), nullable=True))
        batch_op.create_index("ix_deals_company_name", ["company_name"], unique=False)

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE deals SET stage = CASE stage "
            "WHEN 'prospecting' THEN 'lead_identified' "
            "WHEN 'qualification' THEN 'initial_screening' "
            "WHEN 'proposal' THEN 'mandate_drafting' "
            "ELSE stage END"
        )
    )
    connection.execute(
        sa.text("UPDATE deals SET transaction_size = value WHERE transaction_size IS NULL")
    )


def downgrade() -> None:
    with op.batch_alter_table("deals") as batch_op:
        batch_op.drop_index("ix_deals_company_name")
        batch_op.drop_column("target_valuation")
        batch_op.drop_column("funding_requirement")
        batch_op.drop_column("ebitda")
        batch_op.drop_column("revenue")
        batch_op.drop_column("transaction_size")
        batch_op.drop_column("deal_type")
        batch_op.drop_column("sector")
        batch_op.drop_column("industry")
        batch_op.drop_column("company_name")
