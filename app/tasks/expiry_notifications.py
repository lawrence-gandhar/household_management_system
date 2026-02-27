"""
Background task: scan for items expiring tomorrow and send notifications.

Called from the app lifespan via asyncio.create_task(), or via a scheduler
(APScheduler / Celery beat) in a production deployment.
"""

import asyncio
import logging

from app.db.session import AsyncSessionFactory
from app.services.expiry import ExpiryService

logger = logging.getLogger("pantry_mate.tasks.expiry")


async def run_expiry_notifications() -> None:
    """One-shot coroutine: process all pending expiry notifications."""
    async with AsyncSessionFactory() as session:
        try:
            service = ExpiryService(session)
            count = await service.process_notifications()
            await session.commit()
            logger.info("Expiry notification task: %d notifications sent.", count)
        except Exception:
            await session.rollback()
            logger.exception("Expiry notification task failed")


async def schedule_daily(interval_seconds: int = 3600) -> None:
    """
    Lightweight in-process loop that runs the notification job every
    `interval_seconds`.  Replace with Celery beat or APScheduler for
    distributed / persistent scheduling.
    """
    while True:
        await run_expiry_notifications()
        await asyncio.sleep(interval_seconds)
