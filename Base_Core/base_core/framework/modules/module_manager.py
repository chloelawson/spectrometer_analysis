# base_lib/framework/modules/module_manager.py
from __future__ import annotations

from typing import Dict, Iterable, List, Type

from base_core.framework.modules import ModuleError

from .base_module import BaseModule



class ModuleManager:
    def __init__(self, modules: Iterable[BaseModule]) -> None:
        self._modules: List[BaseModule] = list(modules)
        self._by_type: Dict[Type[BaseModule], BaseModule] = {}

        # Ensure one instance per module class
        for m in self._modules:
            t = type(m)
            if t in self._by_type:
                raise ModuleError(
                    f"Duplicate module instance for type {t.__name__}. "
                    f"Provide only one instance per module class."
                )
            self._by_type[t] = m

        self._sorted: List[BaseModule] = []

    # ---------- public API ----------

    def bootstrap(self, c, ctx) -> None:
        """
        Boot sequence:
        1) topologically sort modules by requires
        2) call register() in order
        3) call on_startup() in order
        """
        self._sorted = self._toposort()

        for m in self._sorted:
            m.register(c, ctx)

        for m in self._sorted:
            m.on_startup(c, ctx)

    def shutdown(self, c, ctx) -> None:
        """
        Shutdown in reverse order.
        Safe to call even if bootstrap wasn't called (no-op).
        """
        if not self._sorted:
            return

        for m in reversed(self._sorted):
            try:
                m.on_shutdown(c, ctx)
            except Exception:
                # Never crash shutdown; log if available
                if hasattr(ctx, "log"):
                    ctx.log.exception("Error while shutting down module %s", self._mod_label(m))

    # ---------- internals ----------

    def _toposort(self) -> List[BaseModule]:
        """
        DFS topological sort with cycle detection.
        """
        UNVISITED, VISITING, VISITED = 0, 1, 2
        state: Dict[Type[BaseModule], int] = {}
        stack: List[Type[BaseModule]] = []
        out: List[BaseModule] = []

        def visit(t: Type[BaseModule]) -> None:
            st = state.get(t, UNVISITED)
            if st == VISITING:
                # cycle -> show nice chain
                cycle = " -> ".join([x.__name__ for x in stack + [t]])
                raise ModuleError(f"Module dependency cycle detected: {cycle}")
            if st == VISITED:
                return

            mod = self._by_type.get(t)
            if mod is None:
                raise ModuleError(
                    f"Missing required module: {t.__name__}. "
                    f"Add an instance of {t.__name__} to ModuleManager(modules=[...])."
                )

            state[t] = VISITING
            stack.append(t)

            for dep_t in getattr(mod, "requires", ()):
                visit(dep_t)

            stack.pop()
            state[t] = VISITED
            out.append(mod)

        # Visit in the order the user provided (stable-ish)
        for m in self._modules:
            visit(type(m))

        # out already in dependency-first order (because DFS appends after deps)
        return out

    def _mod_label(self, m: BaseModule) -> str:
        return m.name or type(m).__name__
