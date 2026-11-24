"""Persist AI document processing and approval records.

Revision ID: 8f32ac518a90
Revises: d4a12c87f901
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f32ac518a90"
down_revision: Union[str, None] = "d4a12c87f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mandate_generations",
        sa.Column("source_document_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("processing_mode", sa.String(length=20), nullable=True),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("financial_analysis", sa.JSON(), nullable=True),
        sa.Column("deal_proposal", sa.JSON(), nullable=True),
        sa.Column("mandate_draft", sa.Text(), nullable=True),
        sa.Column("teaser_draft", sa.Text(), nullable=True),
        sa.Column("quality_review", sa.JSON(), nullable=True),
        sa.Column(
            "agent_history",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("approved_by_id", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["documents.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mandate_generations_id"), "mandate_generations", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_mandate_generations_organization_id"),
        "mandate_generations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mandate_generations_status"),
        "mandate_generations",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_mandate_generations_status"), table_name="mandate_generations"
    )
    op.drop_index(
        op.f("ix_mandate_generations_organization_id"),
        table_name="mandate_generations",
    )
    op.drop_index(op.f("ix_mandate_generations_id"), table_name="mandate_generations")
    op.drop_table("mandate_generations")
