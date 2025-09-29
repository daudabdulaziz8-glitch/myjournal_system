"""normalize roles to lowercase values

Revision ID: 20250929_normalize_roles
Revises: 
Create Date: 2025-09-29
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250929_normalize_roles'
down_revision = 'abc23ef82dc7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE user SET role = LOWER(role) WHERE role IS NOT NULL"))


def downgrade():
    # impossible to reliably reverse case changes; leave as no-op
    pass
