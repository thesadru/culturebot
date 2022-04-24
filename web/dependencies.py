import asyncio
import typing

import fastapi

import culturebot

__all__ = ["config", "connection", "get_oauth"]

config = culturebot.load_config()

conn: culturebot.Connection = NotImplemented


async def connection():
    global conn

    if conn is NotImplemented:
        conn = culturebot.Connection(config.tokens.postgres)

    if not conn.initialized:
        await conn.connect()

    return conn


async def get_oauth(
    request: fastapi.Request,
    session: culturebot.sql.Connection = fastapi.Depends(connection),
) -> typing.Mapping[str, culturebot.sql.models.OAuth]:
    tasks: typing.Mapping[str, asyncio.Task[typing.Optional[culturebot.sql.models.OAuth]]] = {}

    for cookie_key, cookie_value in request.cookies.items():
        if not cookie_key.endswith("_key"):
            continue

        service = cookie_key.rsplit("_", maxsplit=1)[0]

        coro = session.select(culturebot.sql.models.OAuth, key=cookie_value)
        tasks[service] = asyncio.create_task(coro)

    gathered = await asyncio.gather(*tasks.values())
    return {service: oauth for service, oauth in zip(tasks, gathered) if oauth is not None}
