"""Camera status: last_seen_at (online badge) and snapshot_path (zone drawing).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cameras", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cameras", sa.Column("snapshot_path", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("cameras", "snapshot_path")
    op.drop_column("cameras", "last_seen_at")
