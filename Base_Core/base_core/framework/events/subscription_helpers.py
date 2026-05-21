from __future__ import annotations

from typing import Any, Callable, Hashable, Optional

from base_core.framework.events.event_bus import EventBus, Handler
from base_core.framework.concurrency.interfaces import ITaskRunner

def subscribe_on(
    bus: EventBus,
    topic: str,
    runner: ITaskRunner,
    handler: Handler,
    *,
    key: Optional[Hashable] = None,
    cancel_previous: bool = True,
    drop_outdated: bool = True,
) -> Callable[[], None]:
    """
    Subscribe, but ensure the handler runs on the given runner (not on publisher thread).
    """
    task_key = key or f"event:{topic}"

    def wrapped(payload: Any) -> None:
        runner.run(
            lambda: handler(payload),
            key=task_key,
            cancel_previous=cancel_previous,
            drop_outdated=drop_outdated,
        )

    return bus.subscribe(topic, wrapped)
