"""expand submission_status enum with REVISIONS_REQUESTED (SQLite)"""
from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = "expand_submission_status_rev"          # can keep auto-generated one
down_revision = "PUT_YOUR_PREVIOUS_REVISION_ID"    # e.g. "7054151925de"
branch_labels = None
depends_on = None

def upgrade():
    # SQLite stores Enum as CHECK constraint; batch mode recreates the table.
    with op.batch_alter_table("submission") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "PENDING", "UNDER_REVIEW", "ACCEPTED", "REJECTED",
                name="submission_status"
            ),
            type_=sa.Enum(
                "PENDING", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "REVISIONS_REQUESTED",
                name="submission_status"
            ),
            existing_nullable=False,
        )

def downgrade():
    # WARNING: this fails if any rows still use REVISIONS_REQUESTED
    with op.batch_alter_table("submission") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "PENDING", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "REVISIONS_REQUESTED",
                name="submission_status"
            ),
            type_=sa.Enum(
                "PENDING", "UNDER_REVIEW", "ACCEPTED", "REJECTED",
                name="submission_status"
            ),
            existing_nullable=False,
        )
