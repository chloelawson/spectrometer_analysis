from abc import ABC, abstractmethod

from base_core.framework.app.context import AppContext
from base_core.framework.di.container import Container


class BaseModule(ABC):
    name: str = ""
    requires: tuple[type["BaseModule"], ...] = ()

    @abstractmethod
    def register(self, c: Container, ctx: AppContext) -> None:
        raise NotImplementedError

    def on_startup(self, c: Container, ctx: AppContext) -> None:
        return None

    def on_shutdown(self, c: Container, ctx: AppContext) -> None:
        return None
