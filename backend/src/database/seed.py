"""Database seeding: create default admin user on startup if not exists."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.db import async_session_maker
from src.models.user import User, UserRole
from src.utils.security import hash_password
from src.config import settings

logger = logging.getLogger(__name__)


async def seed_admin() -> None:
    """Create default admin user if not exists."""
    async with async_session_maker() as db:
        async with db.begin():
            stmt = select(User).where(User.email == settings.ADMIN_EMAIL)
            result = await db.execute(stmt)
            existing = result.scalars().first()

            if existing:
                logger.info(f"Admin user already exists: {settings.ADMIN_EMAIL}")
                return

            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                name=settings.ADMIN_NAME,
            )
            db.add(admin)

        logger.info(f"Default admin user created: {settings.ADMIN_EMAIL}")
