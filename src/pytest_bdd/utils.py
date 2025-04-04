"""Various utility functions."""

from __future__ import annotations

import base64
import pickle
import re
from inspect import getframeinfo, signature
from sys import _getframe
from typing import TYPE_CHECKING, Callable, TypeVar, cast, overload
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.pytester import RunResult

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

CONFIG_STACK: list[Config] = []


def get_required_args(func: Callable[..., object]) -> list[str]:
    """Get a list of argument that are required for a function.

    :param func: The function to inspect.

    :return: A list of argument names.
    """
    params = signature(func).parameters.values()
    return [
        param.name for param in params if param.kind == param.POSITIONAL_OR_KEYWORD and param.default is param.empty
    ]


def get_caller_module_locals(stacklevel: int = 1) -> dict[str, object]:
    """Get the caller module locals dictionary.

    We use sys._getframe instead of inspect.stack(0) because the latter is way slower, since it iterates over
    all the frames in the stack.
    """
    return _getframe(stacklevel + 1).f_locals


def get_caller_module_path(depth: int = 2) -> str:
    """Get the caller module path.

    We use sys._getframe instead of inspect.stack(0) because the latter is way slower, since it iterates over
    all the frames in the stack.
    """
    frame = _getframe(depth)
    return getframeinfo(frame, context=0).filename


_DUMP_START = "_pytest_bdd_>>>"
_DUMP_END = "<<<_pytest_bdd_"


def dump_obj(*objects: object) -> None:
    """Dump objects to stdout so that they can be inspected by the test suite."""
    for obj in objects:
        dump = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        encoded = base64.b64encode(dump).decode("ascii")
        print(f"{_DUMP_START}{encoded}{_DUMP_END}")


def collect_dumped_objects(result: RunResult) -> list:
    """Parse all the objects dumped with `dump_object` from the result.

    Note: You must run the result with output to stdout enabled.
    For example, using ``pytester.runpytest("-s")``.
    """
    stdout = str(result.stdout)
    payloads = re.findall(rf"{_DUMP_START}(.*?){_DUMP_END}", stdout)
    return [pickle.loads(base64.b64decode(payload)) for payload in payloads]


def setdefault(obj: object, name: str, default: T) -> T:
    """Just like dict.setdefault, but for objects."""
    try:
        return cast(T, getattr(obj, name))
    except AttributeError:
        setattr(obj, name, default)
        return default


def identity(x: T) -> T:
    """Return the argument."""
    return x


@overload
def registry_get_safe(registry: WeakKeyDictionary[K, V], key: object, default: T) -> V | T: ...
@overload
def registry_get_safe(registry: WeakKeyDictionary[K, V], key: object, default: None = None) -> V | None: ...


def registry_get_safe(registry: WeakKeyDictionary[K, V], key: object, default: T | None = None) -> T | V | None:
    """Get a value from a registry, or None if the key is not in the registry.
    It ensures that this works even if the key cannot be weak-referenced (normally this would raise a TypeError).
    """
    try:
        return registry.get(key, default)  # type: ignore[arg-type]
    except TypeError:
        return None
