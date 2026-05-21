from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List
import threading

Handler = Callable[[Any], None]


@dataclass
class EventBus:
    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self._subs: Dict[str, List[Handler]] = {}

    def subscribe(self, topic: str, handler: Handler) -> Callable[[], None]:
        with self._lock:
            self._subs.setdefault(topic, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._subs.get(topic, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def publish(self, topic: str, payload: Any) -> None:
        with self._lock:
            handlers = list(self._subs.get(topic, []))
        for h in handlers:
            try:
                h(payload)
            except Exception:
                pass
