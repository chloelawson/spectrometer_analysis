from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Type, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Guard:
    """Static guard methods for parameter validation."""

    @staticmethod
    def not_none(value: Optional[T], name: str = "value") -> T:
        """Raise ValueError if value is None; otherwise return value."""
        if value is None:
            raise ValueError(f"'{name}' must not be None")
        return value

    @staticmethod
    def not_blank(value: Optional[str], name: str = "value") -> str:
        """Raise ValueError if value is None, empty, or only whitespace."""
        value = Guard.not_none(value, name)
        if value.strip() == "":
            raise ValueError(f"'{name}' must not be blank")
        return value

    @staticmethod
    def not_empty(value: Any, name: str = "value") -> Any:
        """For containers (list/dict/set/tuple/str/...): must not be empty."""
        value = Guard.not_none(value, name)
        try:
            if len(value) == 0:
                raise ValueError(f"'{name}' must not be empty")
        except TypeError as e:
            raise TypeError(f"'{name}' must be a sized object (supports len())") from e
        return value

    @staticmethod
    def is_instance(value: Any, expected_type: Type[T], name: str = "value") -> T:
        """Type check like isinstance; returns a typed value."""
        if not isinstance(value, expected_type):
            raise TypeError(f"'{name}' must be of type {expected_type.__name__}")
        return value

    @staticmethod
    def check(condition: bool, message: str = "Condition failed") -> None:
        """General-purpose guard for arbitrary conditions."""
        if not condition:
            raise ValueError(message)
