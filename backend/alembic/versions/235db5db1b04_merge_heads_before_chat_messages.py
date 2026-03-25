"""merge heads before chat_messages

Revision ID: 235db5db1b04
Revises: c4d5e6f7g8h9, s4t5u6v7w8x9
Create Date: 2026-03-23 15:20:06.921013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '235db5db1b04'
down_revision: Union[str, Sequence[str], None] = ('c4d5e6f7g8h9', 's4t5u6v7w8x9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
