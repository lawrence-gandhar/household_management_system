"""Admin user seeder.

Creates an initial admin account in the ``users`` table.  Safe to run
multiple times — if a user with the given email already exists the row is
left completely untouched (``ON CONFLICT (email) DO NOTHING``).

CLI usage
---------
Run from the project root::

    python -m app.db.seeders.admin_seeder \\
        --email admin@example.com \\
        --password "s3cr3t!" \\
        --full-name "Admin User"      # optional

``--full-name`` defaults to "Admin" when omitted.

Environment-variable alternative
---------------------------------
Instead of CLI flags you can export the three variables and run without flags::

    ADMIN_EMAIL=admin@example.com \\
    ADMIN_PASSWORD=s3cr3t! \\
    ADMIN_FULL_NAME="Admin User" \\
    python -m app.db.seeders.admin_seeder

CLI flags take precedence over environment variables when both are supplied.
"""

import asyncio
import logging
import os
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.seeders.base import BaseSeeder
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


class AdminSeeder(BaseSeeder):
    """Insert a single admin user if the email does not already exist.

    Parameters
    ----------
    db:
        Active async session.  The caller must commit (or roll back) after
        :meth:`seed` returns.
    email:
        Email address for the admin account.
    password:
        Plain-text password.  Hashed with bcrypt before storage.
    full_name:
        Display name shown in the admin panel (default: ``"Admin"``).
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        full_name: str = "Admin",
    ) -> None:
        super().__init__(db)
        self._email     = email.strip().lower()
        self._password  = password
        self._full_name = full_name.strip() or "Admin"

    async def seed(self) -> None:
        stmt = text(
            """
            INSERT INTO users
                (id, email, hashed_password, full_name, role, is_active, is_verified)
            VALUES
                (:id, :email, :hashed_password, :full_name, 'admin', true, true)
            ON CONFLICT (email) DO NOTHING
            """
        )

        result = await self._db.execute(
            stmt,
            {
                "id":              uuid.uuid4(),
                "email":           self._email,
                "hashed_password": hash_password(self._password),
                "full_name":       self._full_name,
            },
        )

        if result.rowcount == 1:
            logger.info("AdminSeeder: created admin user <%s>.", self._email)
        else:
            logger.info(
                "AdminSeeder: user <%s> already exists — skipped.", self._email
            )


# ── Standalone helper ──────────────────────────────────────────────────────────


async def run_admin_seeder(
    *,
    email: str,
    password: str,
    full_name: str = "Admin",
) -> None:
    """Open a fresh session, run the seeder, and commit.

    Safe to call from scripts or async entry-points.
    Rolls back automatically on error.
    """
    async with AsyncSessionFactory() as session:
        try:
            await AdminSeeder(
                session,
                email=email,
                password=password,
                full_name=full_name,
            ).seed()
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("AdminSeeder failed — transaction rolled back.")
            raise


# ── CLI entry-point ────────────────────────────────────────────────────────────


def _parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed the initial admin user.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Credentials can also be supplied via environment variables:\n"
            "  ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_FULL_NAME"
        ),
    )
    parser.add_argument(
        "--email",
        default=os.getenv("ADMIN_EMAIL", ""),
        metavar="EMAIL",
        help="Admin email address (env: ADMIN_EMAIL)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD", ""),
        metavar="PASSWORD",
        help="Admin plain-text password (env: ADMIN_PASSWORD)",
    )
    parser.add_argument(
        "--full-name",
        default=os.getenv("ADMIN_FULL_NAME", "Admin"),
        metavar="NAME",
        help='Display name (env: ADMIN_FULL_NAME, default: "Admin")',
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    args = _parse_args()

    if not args.email:
        raise SystemExit("Error: --email (or ADMIN_EMAIL) is required.")
    if not args.password:
        raise SystemExit("Error: --password (or ADMIN_PASSWORD) is required.")

    asyncio.run(
        run_admin_seeder(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
        )
    )
    logger.info("Done.")
