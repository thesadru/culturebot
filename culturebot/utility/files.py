import os
import pkgutil
import typing

__all__ = ["search_directory"]


def search_directory(path: str) -> typing.Iterator[str]:
    """Walk through a directory and yield all modules."""
    relpath = os.path.relpath(path)  # relative and normalized

    prefix = relpath.replace(os.sep, ".")

    for finder, name, ispkg in pkgutil.iter_modules([path]):
        if ispkg:
            name = name + "." + "component"

        yield prefix + "." + name
