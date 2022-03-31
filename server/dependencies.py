import typing

import alluka

__all__ = ["client", "injected"]

CallbackT = typing.TypeVar("CallbackT", bound=alluka.abc.CallbackSig[typing.Any])

client = alluka.Client()
"""The main client used in the server"""


def injected(callback: CallbackT) -> alluka.abc.AsyncSelfInjecting[CallbackT]:
    """Make a callback self-injecting"""
    return client.as_async_self_injecting(callback)
