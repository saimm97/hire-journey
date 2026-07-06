"""merge cv-parsing and job-pipeline heads

Revision ID: 44db610f1cc8
Revises: 81e0bcd1606b, a72be9410f33
Create Date: 2026-06-30 13:59:29.201439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '44db610f1cc8'
down_revision: Union[str, None] = ('81e0bcd1606b', 'a72be9410f33')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
