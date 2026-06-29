"""merge pipeline and auth migrations

Revision ID: 81e0bcd1606b
Revises: a9a976b696d9, e96146985bac
Create Date: 2026-06-22 19:50:07.396511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '81e0bcd1606b'
down_revision: Union[str, None] = ('a9a976b696d9', 'e96146985bac')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
