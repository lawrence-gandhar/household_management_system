"""Dashboard analytics service.

Design contract
---------------
- All methods are ``@staticmethod`` — no instance state, no DI on ``__init__``.
- Every public method receives an ``AsyncSession``; it never opens its own session.
- Returns plain stdlib ``dataclass`` objects so callers (admin view, API, tests)
  can serialise/render however they like without a Pydantic dependency.
- Queries are PostgreSQL-specific where noted (``date_trunc``).
- No writes, no side-effects; safe to call from any read-only context.

Bugs fixed vs. original skeleton
---------------------------------
- Was comparing ``User.role == "premium"``  → fixed to ``subscription_tier``
- Was querying ``InventoryItem.expiry_date`` → does not exist; correct table is
  ``ExpiryTracking.expiry_date``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubscriptionTier
from app.models.inventory import ExpiryTracking, InventoryItem
from app.models.recipe import Recipe
from app.models.subscription import Subscription
from app.models.user import User

# ── Business constants ─────────────────────────────────────────────────────────

PREMIUM_MONTHLY_PRICE_USD: float = 9.99


# ── Typed metric containers ────────────────────────────────────────────────────

@dataclass
class UserMetrics:
    total: int
    active: int
    premium: int
    new_7d: int
    growth_30d: list[dict[str, Any]]   # [{"date": "YYYY-MM-DD", "count": N}, ...]


@dataclass
class InventoryMetrics:
    total: int
    expiring_24h: int
    avg_per_user: float
    top_items: list[dict[str, Any]]    # [{"name": "...", "count": N}, ...]


@dataclass
class RecipeMetrics:
    total: int
    premium_count: int
    new_7d: int
    top_cuisines: list[dict[str, Any]] # [{"cuisine": "...", "count": N}, ...]


@dataclass
class BusinessMetrics:
    free_count: int
    premium_count: int
    conversion_rate: float             # percentage — e.g. 15.5 means 15.5 %
    active_premium_subs: int
    estimated_monthly_revenue: float   # USD, based on active premium × price


@dataclass
class DashboardMetrics:
    users: UserMetrics
    inventory: InventoryMetrics
    recipes: RecipeMetrics
    business: BusinessMetrics
    generated_at: datetime = field(default_factory=datetime.utcnow)


# ── Service ────────────────────────────────────────────────────────────────────

class DashboardService:
    """Read-only aggregation service — no writes, no instance state."""

    @staticmethod
    async def get_all_metrics(db: AsyncSession) -> DashboardMetrics:
        """Fetch every dashboard section and return a unified snapshot."""
        users     = await DashboardService._user_metrics(db)
        inventory = await DashboardService._inventory_metrics(db, users.total)
        recipes   = await DashboardService._recipe_metrics(db)
        business  = await DashboardService._business_metrics(db, users.total)
        return DashboardMetrics(
            users=users,
            inventory=inventory,
            recipes=recipes,
            business=business,
        )

    # ── User metrics ──────────────────────────────────────────────────────────

    @staticmethod
    async def _user_metrics(db: AsyncSession) -> UserMetrics:
        week_ago = datetime.utcnow() - timedelta(days=7)

        total = await db.scalar(
            select(func.count()).select_from(User)
        ) or 0

        active = await db.scalar(
            select(func.count()).select_from(User)
            .where(User.is_active.is_(True))
        ) or 0

        # Count via Subscription table — subscription_tier removed from User
        premium = await db.scalar(
            select(func.count()).select_from(Subscription)
            .where(Subscription.tier == SubscriptionTier.premium)
            .where(Subscription.is_active.is_(True))
        ) or 0

        new_7d = await db.scalar(
            select(func.count()).select_from(User)
            .where(User.created_at >= week_ago)
        ) or 0

        growth_30d = await DashboardService._user_growth_series(db)

        return UserMetrics(
            total=total,
            active=active,
            premium=premium,
            new_7d=new_7d,
            growth_30d=growth_30d,
        )

    @staticmethod
    async def _user_growth_series(db: AsyncSession) -> list[dict[str, Any]]:
        """Daily new-user counts for the last 30 days.

        Uses PostgreSQL ``date_trunc`` — produces one row per day that had at
        least one registration.  Days with zero signups are absent from the
        result (the chart will still render correctly via interpolation).
        """
        since = datetime.utcnow() - timedelta(days=30)
        day_bucket = func.date_trunc("day", User.created_at).label("day")
        result = await db.execute(
            select(day_bucket, func.count(User.id).label("count"))
            .where(User.created_at >= since)
            .group_by(day_bucket)
            .order_by(day_bucket)
        )
        return [
            {"date": row.day.strftime("%Y-%m-%d"), "count": int(row.count)}
            for row in result.all()
        ]

    # ── Inventory metrics ─────────────────────────────────────────────────────

    @staticmethod
    async def _inventory_metrics(
        db: AsyncSession,
        total_users: int,
    ) -> InventoryMetrics:
        today: date    = datetime.utcnow().date()
        tomorrow: date = today + timedelta(days=1)

        total = await db.scalar(
            select(func.count()).select_from(InventoryItem)
        ) or 0

        # ExpiryTracking.expiry_date is a DATE column (not datetime).
        # "Expiring within 24 h" means expiry_date is today or tomorrow.
        expiring_24h = await db.scalar(
            select(func.count())
            .select_from(ExpiryTracking)
            .where(ExpiryTracking.expiry_date >= today)
            .where(ExpiryTracking.expiry_date <= tomorrow)
        ) or 0

        avg_per_user = round(total / total_users, 2) if total_users > 0 else 0.0

        # Top 5 item names by frequency across all users
        result = await db.execute(
            select(
                InventoryItem.name,
                func.count(InventoryItem.id).label("count"),
            )
            .group_by(InventoryItem.name)
            .order_by(func.count(InventoryItem.id).desc())
            .limit(5)
        )
        top_items = [
            {"name": row.name, "count": int(row.count)}
            for row in result.all()
        ]

        return InventoryMetrics(
            total=total,
            expiring_24h=expiring_24h,
            avg_per_user=avg_per_user,
            top_items=top_items,
        )

    # ── Recipe metrics ────────────────────────────────────────────────────────

    @staticmethod
    async def _recipe_metrics(db: AsyncSession) -> RecipeMetrics:
        week_ago = datetime.utcnow() - timedelta(days=7)

        total = await db.scalar(
            select(func.count()).select_from(Recipe)
        ) or 0

        premium_count = await db.scalar(
            select(func.count()).select_from(Recipe)
            .where(Recipe.is_premium.is_(True))
        ) or 0

        new_7d = await db.scalar(
            select(func.count()).select_from(Recipe)
            .where(Recipe.created_at >= week_ago)
        ) or 0

        # Top 5 cuisine types — NULLs excluded
        result = await db.execute(
            select(
                Recipe.cuisine_type,
                func.count(Recipe.id).label("count"),
            )
            .where(Recipe.cuisine_type.isnot(None))
            .group_by(Recipe.cuisine_type)
            .order_by(func.count(Recipe.id).desc())
            .limit(5)
        )
        top_cuisines = [
            {"cuisine": row.cuisine_type, "count": int(row.count)}
            for row in result.all()
        ]

        return RecipeMetrics(
            total=total,
            premium_count=premium_count,
            new_7d=new_7d,
            top_cuisines=top_cuisines,
        )

    # ── Business metrics ──────────────────────────────────────────────────────

    @staticmethod
    async def _business_metrics(
        db: AsyncSession,
        total_users: int,
    ) -> BusinessMetrics:
        # Tier distribution from the Subscription table (subscription_tier
        # column was removed from User; Subscription is now the single source).
        result = await db.execute(
            select(
                Subscription.tier,
                func.count(Subscription.id).label("count"),
            )
            .group_by(Subscription.tier)
        )
        tier_map: dict[str, int] = {
            str(row.tier): int(row.count)
            for row in result.all()
        }
        free_count    = tier_map.get(SubscriptionTier.free.value,    0)
        premium_count = tier_map.get(SubscriptionTier.premium.value, 0)

        conversion_rate = (
            round((premium_count / total_users) * 100, 1)
            if total_users > 0 else 0.0
        )

        active_premium_subs = await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.tier == SubscriptionTier.premium)
            .where(Subscription.is_active.is_(True))
        ) or 0

        estimated_monthly_revenue = round(
            active_premium_subs * PREMIUM_MONTHLY_PRICE_USD, 2
        )

        return BusinessMetrics(
            free_count=free_count,
            premium_count=premium_count,
            conversion_rate=conversion_rate,
            active_premium_subs=active_premium_subs,
            estimated_monthly_revenue=estimated_monthly_revenue,
        )
