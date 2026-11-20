
"""add native language to users

Revision ID: 761bf301f608
Revises: a1c9e7d4b2f0
Create Date: 2026-11-19 19:02:52.070485

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "761bf301f608"
down_revision: Union[str, Sequence[str], None] = "a1c9e7d4b2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("native_language", sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "native_language")
