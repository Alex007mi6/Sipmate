"""initial sipmate schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # create_type=False: create enums once below. Avoid DuplicateObject when
    # create_table would otherwise emit CREATE TYPE again (common after a
    # partial failed migrate on Render Postgres).
    user_role = postgresql.ENUM("user", "admin", name="user_role", create_type=False)
    model_status = postgresql.ENUM(
        "active", "stale", "archived", "failed", name="model_status", create_type=False
    )
    redemption_status = postgresql.ENUM(
        "pending", "redeemed", "cancelled", name="redemption_status", create_type=False
    )
    user_role.create(op.get_bind(), checkfirst=True)
    model_status.create(op.get_bind(), checkfirst=True)
    redemption_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("research_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=512), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("abv", sa.Float(), nullable=False),
        sa.Column("serving_ml", sa.Float(), nullable=True),
        sa.Column("alcohol_ml", sa.Float(), nullable=True),
        sa.Column("alcohol_grams", sa.Float(), nullable=True),
        sa.Column("taste_features", JSONType, nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("image_key", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("abv_suspicious", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("missing_taste_profile", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recommendable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("full_name", name="uq_products_full_name"),
    )
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_category", "products", ["category"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("algorithm", sa.String(length=120), nullable=False),
        sa.Column("feature_names", JSONType, nullable=False),
        sa.Column("dataset_version", sa.String(length=120), nullable=False),
        sa.Column("model_path", sa.String(length=512), nullable=False),
        sa.Column("scaler_path", sa.String(length=512), nullable=False),
        sa.Column("metadata_path", sa.String(length=512), nullable=False),
        sa.Column("status", model_status, nullable=False),
        sa.Column("product_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "gamification_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata", JSONType, nullable=False),
        sa.UniqueConstraint("event_type"),
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("icon", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("condition_type", sa.String(length=64), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("image_key", sa.String(length=512), nullable=True),
        sa.Column("points_cost", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "points_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", JSONType, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "event_type", "reference_id", name="uq_points_user_event_ref"),
    )
    op.create_index("ix_points_transactions_user_id", "points_transactions", ["user_id"])
    op.create_index("ix_points_transactions_event_type", "points_transactions", ["event_type"])

    op.create_table(
        "user_badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("badge_id", sa.Integer(), sa.ForeignKey("badges.id"), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
    op.create_index("ix_user_badges_badge_id", "user_badges", ["badge_id"])

    op.create_table(
        "redemptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reward_id", sa.Integer(), sa.ForeignKey("rewards.id"), nullable=False),
        sa.Column("points_spent", sa.Integer(), nullable=False),
        sa.Column("redemption_code", sa.String(length=32), nullable=False),
        sa.Column("status", redemption_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("redemption_code", name="uq_redemption_code"),
    )
    op.create_index("ix_redemptions_user_id", "redemptions", ["user_id"])
    op.create_index("ix_redemptions_reward_id", "redemptions", ["reward_id"])
    op.create_index("ix_redemptions_redemption_code", "redemptions", ["redemption_code"])

    op.create_table(
        "recommendation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("anonymous_session_id", sa.String(length=64), nullable=True),
        sa.Column("selected_product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("recommended_product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("alcohol_reduction", sa.Float(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_recommendation_events_user_id", "recommendation_events", ["user_id"])
    op.create_index(
        "ix_recommendation_events_anonymous_session_id",
        "recommendation_events",
        ["anonymous_session_id"],
    )
    op.create_index(
        "ix_recommendation_events_selected_product_id",
        "recommendation_events",
        ["selected_product_id"],
    )
    op.create_index(
        "ix_recommendation_events_recommended_product_id",
        "recommendation_events",
        ["recommended_product_id"],
    )
    op.create_index("ix_recommendation_events_event_type", "recommendation_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("recommendation_events")
    op.drop_table("redemptions")
    op.drop_table("user_badges")
    op.drop_table("points_transactions")
    op.drop_table("rewards")
    op.drop_table("badges")
    op.drop_table("gamification_rules")
    op.drop_table("model_versions")
    op.drop_table("products")
    op.drop_table("users")
    sa.Enum(name="redemption_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="model_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
