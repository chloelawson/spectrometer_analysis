from enum import Enum, auto


class ServiceState(Enum):
    STOPPED = auto()
    RUNNING = auto()
    NEW = auto()