
from base_core.framework.domain.interfaces import IRunnable
from base_core.framework.services.enums import ServiceState


class RunnableServiceBase(IRunnable):
    def __init__(self) -> None:
        self._state = ServiceState.NEW

    @property
    def is_running(self) -> bool:
        return self._state == ServiceState.RUNNING

    def start(self) -> None:
        if self.is_running:
            return
        self._state = ServiceState.RUNNING

    def stop(self) -> None:
        if not self.is_running:
            return
        self._state = ServiceState.STOPPED

    def reset(self) -> None:
        if self.is_running:
            self.stop()
        self._state = ServiceState.NEW