from __future__ import annotations

import os
import pathlib
import typing

import asyncpg

__all__ = ["Connection", "make_eq", "make_s"]

T = typing.TypeVar("T")


class AttributeRecord(asyncpg.Record):
    def __getattr__(self, key: str) -> typing.Any:
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(*e.args) from e


def make_record(cls: typing.Type[T]) -> typing.Type[T]:
    cls = type(cls.__name__, (AttributeRecord, cls), {})  # type: ignore
    cls.__new__ = object.__new__
    cls.__init__ = object.__init__
    return cls


def make_eq(start: int = 1, **kwargs: typing.Any):
    return [f"{k} = ${n}" for n, k in enumerate(kwargs.keys(), start)]


def make_s(start: int = 1, **kwargs: typing.Any):
    return [f"${n}" for n in range(start, len(kwargs) + start)]


def only_truthy(
    values: typing.Optional[typing.Mapping[str, typing.Any]] = None,
    **kwargs: typing.Any,
) -> typing.Mapping[str, typing.Any]:
    if values:
        kwargs.update(values)

    return {k: v for k, v in kwargs.items() if v}


class Connection:
    pool: asyncpg.Pool[asyncpg.Record]
    schema: pathlib.Path

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = 10,
        max_size: int = 10,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0,
        schema: typing.Optional[typing.Union[os.PathLike[str], str]] = None,
        **connect_kwargs: typing.Any,
    ) -> None:
        self.pool = asyncpg.create_pool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            max_queries=max_queries,
            max_inactive_connection_lifetime=max_inactive_connection_lifetime,
            **connect_kwargs,
        )

        if schema is not None:
            self.schema = pathlib.Path(schema)
        else:
            self.schema = pathlib.Path(__file__).parent / "schema.sql"

    @property
    def initialized(self) -> bool:
        return self.pool._initialized  # type: ignore

    async def create_tables(self) -> None:
        command = self.schema.read_text()
        await self.execute(command)

    async def intialize(self) -> None:
        if self.pool._initializing or self.pool._initialized:  # type: ignore
            return

        await self.pool._async__init__()  # type: ignore

    async def connect(self) -> None:
        await self.intialize()
        await self.create_tables()

    async def close(self, *exc: typing.Any) -> None:
        await self.pool.close()

    # commands

    async def fetchrow(self, query: str, *args: typing.Any, cls: typing.Type[T] = asyncpg.Record) -> typing.Optional[T]:
        if not issubclass(cls, asyncpg.Record):
            cls = make_record(cls)

        async with self.pool.acquire() as con:
            return await con.fetchrow(query, *args, record_class=cls)

    async def select(
        self,
        cls: typing.Type[T] = asyncpg.Record,
        table: typing.Optional[str] = None,
        **kwargs: typing.Any,
    ) -> typing.Optional[T]:
        table = table or getattr(cls, "__tablename__")

        where = " AND ".join(make_eq(**kwargs))
        query = f"SELECT * FROM {table} WHERE {where}"
        return await self.fetchrow(query, *kwargs.values(), cls=cls)

    async def execute(self, query: str, *args: typing.Any) -> str:
        return await self.pool.execute(query, *args)

    async def insert(self, table: str, **kwargs: typing.Any) -> str:
        columns = ", ".join(kwargs.keys())
        values = ", ".join(make_s(**kwargs))
        query = f"INSERT INTO {table} ({columns}) VALUES ({values})"

        return await self.execute(query, *kwargs.values())

    async def update(
        self,
        table: typing.Union[str, type],
        where: typing.Union[str, typing.Mapping[str, typing.Any]],
        **kwargs: typing.Any,
    ) -> str:
        table = table if isinstance(table, str) else getattr(table, "__tablename__")

        values = ", ".join(make_eq(**kwargs))
        if isinstance(where, str):
            where_str = where
        else:
            where_str = " AND ".join(make_eq(**where, start=len(kwargs) + 1))

        query = f"UPDATE {table} SET {values} WHERE {where_str}"

        return await self.execute(query, *kwargs.values(), *(where.values() if not isinstance(where, str) else ()))

    async def upsert(
        self,
        table: typing.Union[str, type],
        keys: typing.Optional[typing.Sequence[str]] = None,
        update: typing.Optional[typing.Mapping[str, typing.Any]] = None,
        **kwargs: typing.Any,
    ) -> str:
        table = table if isinstance(table, str) else getattr(table, "__tablename__")
        keys = (keys,) if isinstance(keys, str) else (keys or tuple(kwargs.keys()))

        columns = ", ".join(kwargs.keys())
        values = ", ".join(make_s(**kwargs))
        conflict_keys = ", ".join(keys)
        conflict_values = ", ".join(make_eq(**(update or kwargs)))
        query = (
            f"INSERT INTO {table} ({columns}) VALUES ({values}) "
            f"ON CONFLICT ({conflict_keys}) DO UPDATE SET {conflict_values}"
        )

        return await self.execute(query, *kwargs.values())

    async def delete(self, table: typing.Union[str, type], **kwargs: typing.Any) -> str:
        table = table if isinstance(table, str) else getattr(table, "__tablename__")

        where = " AND ".join(make_eq(**kwargs))

        query = f"DELETE FROM {table} WHERE {where}"
        return await self.execute(query, *kwargs.values())
