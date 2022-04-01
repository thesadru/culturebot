import typing

import sqlmodel
from sqlalchemy.ext import asyncio as asqlalchemy

from .patch.sqlmodel import AsyncSession

__all__ = ["create_engine", "create_session", "create_tables"]


def create_engine(url: str, **kwargs: typing.Any) -> asqlalchemy.AsyncEngine:
    """Create a standard engine from a config."""
    return asqlalchemy.create_async_engine(url, **kwargs)


def create_session(engine: asqlalchemy.AsyncEngine, **kwargs: typing.Any) -> asqlalchemy.AsyncSession:
    """Create a session."""
    return AsyncSession(engine, **kwargs)


async def create_tables(engine: asqlalchemy.AsyncEngine) -> None:
    """Create all tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(sqlmodel.SQLModel.metadata.create_all)
