"""add hierarchical categories modified

Revision ID: 72c7ec9b5ea8
Revises: 2147b2182688
Create Date: 2026-03-02 16:19:37.801884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72c7ec9b5ea8'
down_revision: Union[str, None] = '2147b2182688'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
