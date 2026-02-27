"""Abstract base class for all database seeders.

Usage
-----
Subclass :class:`BaseSeeder` and implement :meth:`seed`.  Then run via::

    python -m app.db.seeders.your_seeder
"""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class BaseSeeder(ABC):
    """Abstract seeder that operates within a caller-supplied session.

    The caller is responsible for committing or rolling back the transaction.
    Seeders should be idempotent — running them multiple times must not
    produce duplicates or raise errors.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @abstractmethod
    async def seed(self) -> None:
        """Insert seed data.  Must be idempotent."""
