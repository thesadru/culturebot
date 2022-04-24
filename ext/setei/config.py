from __future__ import annotations

import os
import pathlib
import typing

from . import fields
from .fields import issubclass_

__all__ = ["ConfigMeta", "Config"]

ConfigT = typing.TypeVar("ConfigT", bound="Config")


class ConfigMeta(type):
    __config_fields__: typing.Dict[str, fields.Field]

    def _update_dataclass_fields(self) -> typing.Mapping[str, fields.Field]:
        self.__config_fields__ = {}
        type_hints = typing.get_type_hints(self)

        for name, annotation in type_hints.items():
            default = getattr(self, name, fields.MISSING)

            if issubclass_(annotation, Config):
                field = fields.NestedField(annotation, default=default)
            elif not isinstance(default, fields.Field):
                raise TypeError(f"Config requires field type to be specified for {name}")
            else:
                field = default

            field.name = name
            field.type = type_hints[name]

            self.__config_fields__[name] = field

        return self.__config_fields__

    def __new__(cls, name: str, bases: typing.Tuple[type, ...], ns: typing.Dict[str, typing.Any]):
        self: typing.Any = super().__new__(cls, name, bases, ns)
        self._update_dataclass_fields()
        return self


class Config(metaclass=ConfigMeta):
    def __init__(self, **kwargs: typing.Any) -> None:
        for name, value in kwargs.items():
            if name in type(self).__config_fields__:
                setattr(self, name, value)

    @classmethod
    def load(
        cls: typing.Type[ConfigT],
        configuration: typing.Union[typing.Mapping[str, typing.Any], os.PathLike[str], str],
    ) -> ConfigT:
        """Load the config from a yaml file and env vars."""
        if isinstance(configuration, (str, os.PathLike)):
            import yaml

            file = pathlib.Path(configuration)
            config = yaml.safe_load(file.read_text("utf-8"))
        else:
            config = configuration

        kwargs: typing.Dict[str, typing.Any] = {}
        for field in cls.__config_fields__.values():
            value = field.get_value(config)
            if value is not fields.MISSING:
                kwargs[field.name] = value

        return cls(**kwargs)

    def __pretty__(self, fmt: typing.Callable[[typing.Any], str], **kwargs: typing.Any):
        """Devtools pretty formatting."""
        yield type(self).__name__
        yield "("
        yield 1

        for name, field in type(self).__config_fields__.items():
            value = getattr(self, name)
            yield name
            yield "="
            if isinstance(field, fields.EnvField) and isinstance(value, str):
                yield f"<ENV ${field.key}>"
            else:
                yield fmt(value)

            yield 0

        yield -1
        yield ")"
