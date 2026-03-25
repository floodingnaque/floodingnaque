"""create resident_profiles table

Revision ID: a8b9c0d1e2f3
Revises: 2f36c366c2dc
Create Date: 2025-07-14 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a8b9c0d1e2f3"
down_revision = "2f36c366c2dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resident_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # Personal information
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("sex", sa.String(30), nullable=True),
        sa.Column("civil_status", sa.String(30), nullable=True),
        sa.Column("contact_number", sa.String(50), nullable=True),
        sa.Column("alt_contact_number", sa.String(50), nullable=True),
        sa.Column("alt_contact_name", sa.String(255), nullable=True),
        sa.Column("alt_contact_relationship", sa.String(100), nullable=True),
        sa.Column("is_pwd", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_senior_citizen", sa.Boolean(), server_default=sa.text("false")),
        # Household information
        sa.Column("household_members", sa.Integer(), nullable=True),
        sa.Column("children_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("senior_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("pwd_count", sa.Integer(), server_default=sa.text("0")),
        # Address & location
        sa.Column("barangay", sa.String(100), nullable=True),
        sa.Column("purok", sa.String(100), nullable=True),
        sa.Column("street_address", sa.String(500), nullable=True),
        sa.Column("nearest_landmark", sa.String(255), nullable=True),
        sa.Column("home_type", sa.String(50), nullable=True),
        sa.Column("floor_level", sa.String(50), nullable=True),
        # Flood history
        sa.Column("has_flood_experience", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("most_recent_flood_year", sa.Integer(), nullable=True),
        # Notification preferences
        sa.Column("sms_alerts", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("email_alerts", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("push_notifications", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("preferred_language", sa.String(30), server_default=sa.text("'Filipino'")),
        # Consent
        sa.Column("data_privacy_consent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint("sex IN ('Male', 'Female', 'Prefer not to say')", name="valid_sex"),
        sa.CheckConstraint("civil_status IN ('Single', 'Married', 'Widowed', 'Separated')", name="valid_civil_status"),
        sa.CheckConstraint("home_type IN ('Concrete', 'Semi-Concrete', 'Wood', 'Makeshift')", name="valid_home_type"),
        sa.CheckConstraint(
            "floor_level IN ('Ground Floor', '2nd Floor', '3rd Floor or higher')", name="valid_floor_level"
        ),
        sa.CheckConstraint("preferred_language IN ('Filipino', 'English')", name="valid_language"),
        comment="Extended profile data for registered residents",
    )
    op.create_index("ix_resident_profiles_user_id", "resident_profiles", ["user_id"])
    op.create_index("idx_resident_barangay", "resident_profiles", ["barangay"])


def downgrade() -> None:
    op.drop_index("idx_resident_barangay", table_name="resident_profiles")
    op.drop_index("ix_resident_profiles_user_id", table_name="resident_profiles")
    op.drop_table("resident_profiles")
