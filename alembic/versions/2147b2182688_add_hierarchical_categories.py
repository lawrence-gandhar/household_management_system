"""add hierarchical categories

Revision ID: 2147b2182688
Revises: 2b6601049b08
Create Date: 2026-03-02 16:14:40.909776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2147b2182688'
down_revision: Union[str, None] = '2b6601049b08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
