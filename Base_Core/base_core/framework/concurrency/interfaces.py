from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Optional, Protocol, TypeVar
from concurrent.futures import Future

T = TypeVar("T")


@dataclass(frozen=True)
class StreamHandle:
    stop_event: threading.Event
    future: Future[None]

    def stop(self) -> None:
        self.stop_event.set()


class ITaskRunner(Protocol):
    def run(
        self,
        fn: Callable[[], T],
        *,
        on_success: Optional[Callable[[T], None]] = None,
        on_error: Optional[Callable[[BaseException], None]] = None,
        key: Hashable | None = None,
        cancel_previous: bool = False,
        drop_outdated: bool = True,
    ) -> Future[T]:
        ...

    def stream(
        self,
        producer: Callable[[threading.Event], Iterable[T]],
        *,
        on_item: Callable[[T], None],
        on_error: Optional[Callable[[BaseException], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
        key: Hashable | None = None,
        cancel_previous: bool = False,
        drop_outdated: bool = True,
    ) -> StreamHandle:
        ...

    def cancel(self, key: Hashable) -> bool: ...
    def cancel_all(self) -> None: ...
