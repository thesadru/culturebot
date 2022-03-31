"""Modifies sqlmodel to actually be type-safe"""
from __future__ import annotations

import typing

import sqlmodel
import sqlmodel.engine.result
import sqlmodel.ext.asyncio.session
import sqlmodel.sql.base
import sqlmodel.sql.expression

__all__ = ["AsyncSession"]

T = typing.TypeVar("T")

Params = typing.Union[typing.Mapping[str, typing.Any], typing.Sequence[typing.Mapping[str, typing.Any]]]

# https://github.com/tiangolo/sqlmodel/pull/58
class AsyncSession(sqlmodel.ext.asyncio.session.AsyncSession):
    if typing.TYPE_CHECKING:

        def add(self, instance: typing.Any) -> None:
            ...

        @typing.overload
        async def exec(
            self,
            statement: sqlmodel.sql.expression.Select[T],
            *,
            params: typing.Optional[Params] = None,
            execution_options: typing.Mapping[str, typing.Any] = ...,
            bind_arguments: typing.Optional[typing.Mapping[str, typing.Any]] = None,
            **kw: typing.Any,
        ) -> sqlmodel.engine.result.Result[T]:
            ...

        @typing.overload
        async def exec(
            self,
            statement: sqlmodel.sql.expression.SelectOfScalar[T],
            *,
            params: typing.Optional[Params] = None,
            execution_options: typing.Mapping[str, typing.Any] = ...,
            bind_arguments: typing.Optional[typing.Mapping[str, typing.Any]] = None,
            **kw: typing.Any,
        ) -> sqlmodel.engine.result.ScalarResult[T]:
            ...

        async def exec(
            self,
            statement: typing.Union[
                sqlmodel.sql.expression.Select[T],
                sqlmodel.sql.expression.SelectOfScalar[T],
                sqlmodel.sql.base.Executable[T],
            ],
            params: typing.Optional[Params] = None,
            execution_options: typing.Mapping[typing.Any, typing.Any] = ...,
            bind_arguments: typing.Optional[typing.Mapping[str, typing.Any]] = None,
            **kw: typing.Any,
        ) -> sqlmodel.engine.result.ScalarResult[T]:
            ...

        async def __aenter__(self) -> AsyncSession:
            ...


# https://sqlalche.me/e/14/cprf
setattr(sqlmodel.sql.expression.SelectOfScalar, "inherit_cache", 1)
