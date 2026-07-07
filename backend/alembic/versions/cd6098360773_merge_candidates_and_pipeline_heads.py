"""merge candidates and pipeline heads

Revision ID: cd6098360773
Revises: 81e0bcd1606b, a72be9410f33
Create Date: 2026-06-29 20:20:13.875359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cd6098360773'
down_revision: Union[str, None] = ('81e0bcd1606b', 'a72be9410f33')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
