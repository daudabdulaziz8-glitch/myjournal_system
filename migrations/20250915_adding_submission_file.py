"""create submission_file table"""
from alembic import op
import sqlalchemy as sa

# Set these correctly:
revision = "add_submission_file"
down_revision = "7054151925de"  # <-- your last revision id for Issue; adjust if different
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "submission_file",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("submission_id", "version", name="uq_submission_file_sub_ver"),
    )
    op.create_index("ix_submission_file_submission_id", "submission_file", ["submission_id"], unique=False)


def downgrade():
    op.drop_index("ix_submission_file_submission_id", table_name="submission_file")
    op.drop_table("submission_file")
