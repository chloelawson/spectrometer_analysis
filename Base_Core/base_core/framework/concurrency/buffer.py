from __future__ import annotations

from dataclasses import dataclass
from threading import Condition, Lock
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class NoValueError(RuntimeError):
    pass


class Buffer(Generic[T]):
    """
    Thread-safe 'latest item' buffer.
    - Multiple readers can read the same latest value (no consumption).
    - Each set() increments a version counter (useful for triggers).
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._cond = Condition(self._lock)
        self._value: Optional[T] = None
        self._version: int = 0

    def set(self, value: T) -> int:
        with self._lock:
            self._value = value
            self._version += 1
            self._cond.notify_all()
            return self._version

    def get(self) -> Optional[T]:
        with self._lock:
            return self._value

    def version(self) -> int:
        with self._lock:
            return self._version
