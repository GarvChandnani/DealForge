"""Expand CRM profiles and client onboarding records.

Revision ID: 90b63c30d37a
Revises: 65b5740c7a27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "90b63c30d37a"
down_revision: Union[str, None] = "65b5740c7a27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("clients") as batch_op:
        batch_op.add_column(sa.Column("sector", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("location", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("turnover", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(sa.Column("revenue", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(
            sa.Column("funding_requirement", sa.Numeric(18, 2), nullable=True)
        )
        batch_op.add_column(
            sa.Column("currency", sa.String(3), server_default="USD", nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "assigned_originator_id",
                sa.String(36),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_clients_assigned_originator_id_originators",
            "originators",
            ["assigned_originator_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.add_column(
            sa.Column(
                "onboarding_status",
                sa.String(30),
                server_default="not_started",
                nullable=False,
            )
        )

    with op.batch_alter_table("originators") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )
        batch_op.add_column(sa.Column("full_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("email", sa.String(length=254), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("title", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("sectors", sa.String(length=500), nullable=True))
        batch_op.add_column(
            sa.Column("status", sa.String(length=30), server_default="active", nullable=False)
        )

    op.add_column("documents", sa.Column("extracted_fields", sa.JSON(), nullable=True))

    op.create_table(
        "client_interactions",
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("interaction_type", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_client_interactions_client_id"),
        "client_interactions",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_interactions_id"),
        "client_interactions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_interactions_organization_id"),
        "client_interactions",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_client_interactions_organization_id"), table_name="client_interactions")
    op.drop_index(op.f("ix_client_interactions_id"), table_name="client_interactions")
    op.drop_index(op.f("ix_client_interactions_client_id"), table_name="client_interactions")
    op.drop_table("client_interactions")
    op.drop_column("documents", "extracted_fields")

    with op.batch_alter_table("originators") as batch_op:
        batch_op.drop_column("status")
        batch_op.drop_column("sectors")
        batch_op.drop_column("title")
        batch_op.drop_column("phone")
        batch_op.drop_column("email")
        batch_op.drop_column("full_name")
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )

    op.drop_column("clients", "onboarding_status")
    op.drop_column("clients", "assigned_originator_id")
    op.drop_column("clients", "currency")
    op.drop_column("clients", "funding_requirement")
    op.drop_column("clients", "revenue")
    op.drop_column("clients", "turnover")
    op.drop_column("clients", "location")
    op.drop_column("clients", "phone")
    op.drop_column("clients", "sector")
