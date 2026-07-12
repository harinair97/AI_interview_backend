"""Create interview snapshot and event tables.

Revision ID: 20260711_01
Revises: None
"""

from alembic import op
import sqlalchemy as sa

revision = "20260711_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("target_role", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("runtime_state", sa.JSON(), nullable=False),
        sa.Column("interviewer_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interviews_status", "interviews", ["status"])
    op.create_table(
        "interview_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("interview_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "interview_id", "sequence", name="uq_interview_event_sequence"
        ),
    )
    op.create_index("ix_interview_events_interview_id", "interview_events", ["interview_id"])


def downgrade() -> None:
    op.drop_index("ix_interview_events_interview_id", table_name="interview_events")
    op.drop_table("interview_events")
    op.drop_index("ix_interviews_status", table_name="interviews")
    op.drop_table("interviews")
