from __future__ import annotations

import abc
import copy
import functools
import os
import sys
import types
import typing

if typing.TYPE_CHECKING:
    from typing_extensions import TypeGuard

    from .config import Config

__all__ = ["Field", "EnvField", "ConfigField", "env", "conf"]

if sys.version_info >= (3, 10):
    UNION_TYPES = {typing.Union, types.UnionType}
else:
    UNION_TYPES = {typing.Union}

NONE_TYPES = {None, type(None)}


T = typing.TypeVar("T")

MISSING = type("MISSING", (), {})


def issubclass_(cls: object, cls_or_tuple: typing.Type[T]) -> TypeGuard[typing.Type[T]]:
    return isinstance(cls, type) and issubclass(cls, cls_or_tuple)


def parse_union(tp: typing.Any) -> typing.Sequence[typing.Any]:
    if not typing.get_origin(tp) in UNION_TYPES:
        return []

    return typing.get_args(tp)


def convert_value(tp: typing.Any, raw: typing.Any) -> typing.Any:
    if args := parse_union(tp):
        if len(args) == 1:
            return convert_value(args[0], raw)

        exceptions: typing.List[Exception] = []
        for arg in args:
            try:
                return convert_value(arg, raw)
            except (TypeError, ValueError) as e:
                exceptions.append(e)

        raise TypeError(f"Could not convert: {', '.join(map(str, exceptions))}")

    if tp == typing.Any:
        return raw

    if tp in NONE_TYPES:
        if raw is not None:
            raise TypeError("Type must be None")

        return raw

    if isinstance(tp, type) and issubclass(tp, (int, str, float, bool)):
        return tp(raw)

    if issubclass_(origin := typing.get_origin(tp), typing.Sequence):
        underlying = typing.Any
        if args := typing.get_args(tp):
            underlying = args[0]

        return origin([convert_value(underlying, i) for i in raw])  # type: ignore  # Sequence ABC does not have __init__

    raise TypeError(f"Could not parse {tp}")


def guess_default(tp: typing.Any) -> typing.Any:
    if args := parse_union(tp):
        if any(arg in NONE_TYPES for arg in args):
            return None

        for arg in args:
            if (default := guess_default(arg)) is not MISSING:
                return default

        return MISSING

    if issubclass_(typing.get_origin(tp), typing.Sequence):
        return typing.get_origin(tp)

    return MISSING


class Field(abc.ABC):
    """A field that can get a value by itself."""

    name: str = typing.cast(str, MISSING)
    type: typing.Any = MISSING
    converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None
    _guessed_default: bool = False

    def __init__(
        self,
        default: typing.Any = MISSING,
        *,
        converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
    ) -> None:
        self.default = default
        self.repr = True
        self.converter = converter

    def __repr__(self) -> str:
        args = {"name": self.name, "type": self.type}
        if self.default is not MISSING:
            args["default"] = self.default

        formatted = ", ".join(f"{k}={v}" for k, v in args.items())
        return f"{self.__class__.__qualname__}({formatted})"

    @property
    def default(self) -> typing.Any:
        if self._default is MISSING and not self._guessed_default:
            self._guessed_default = True
            self.default = guess_default(self.type)

        if self._default is not MISSING:
            if callable(self._default):
                return self._default()

            return self._default

        raise TypeError(f"No default value for {repr(self)}")

    @default.setter
    def default(self, default: typing.Any) -> None:
        if isinstance(default, (list, dict, set)):
            default = typing.cast("typing.Collection[typing.Any]", default)
            if len(default) > 0:
                default = functools.partial(copy.copy, default)
            else:
                default = type(default)

        self._default = default

    @abc.abstractmethod
    def get_raw_value(self, config: typing.Mapping[str, typing.Any]) -> typing.Any:
        ...

    def get_value(self, config: typing.Optional[typing.Mapping[str, typing.Any]] = None) -> typing.Any:
        raw = self.get_raw_value(config or {})

        if raw is MISSING:
            return self.default

        if self.converter:
            return self.converter(raw)

        return convert_value(self.type, raw)


class EnvField(Field):
    """Field which gets values from environment variables."""

    def __init__(
        self,
        key: str,
        *,
        default: typing.Any = MISSING,
        converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
    ) -> None:
        super().__init__(default, converter=converter)
        self.repr = False
        self.key = key

    def get_raw_value(self, config: typing.Mapping[str, typing.Any]) -> typing.Any:
        return os.getenv(self.key, MISSING)


class ConfigField(Field):
    """Standard config field."""

    def __init__(
        self,
        key: str,
        *,
        default: typing.Any = MISSING,
        converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
    ) -> None:
        super().__init__(default, converter=converter)
        self.key = key

    def get_raw_value(self, config: typing.Mapping[str, typing.Any]) -> typing.Any:
        value = config
        for nest in self.key.split("."):
            if nest not in value:
                return MISSING
            value = value[nest]

        return value


class NestedField(Field):
    """Field representing a nested config."""

    def __init__(
        self,
        model: typing.Type[Config],
        *,
        default: typing.Any = MISSING,
    ) -> None:
        super().__init__(default)
        self.model = model
        self.type = model

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}(name={self.name}, model={self.model})"

    def get_value(self, config: typing.Optional[typing.Mapping[str, typing.Any]] = None) -> typing.Any:
        return self.get_raw_value(config or {})

    def get_raw_value(self, config: typing.Mapping[str, typing.Any]) -> typing.Any:
        return self.model.load(config)


def env(
    key: str,
    *,
    default: typing.Any = MISSING,
    converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
) -> typing.Any:
    return EnvField(key, default=default, converter=converter)


def conf(
    key: str,
    *,
    default: typing.Any = MISSING,
    converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
) -> typing.Any:
    return ConfigField(key, default=default, converter=converter)
