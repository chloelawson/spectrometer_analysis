from dataclasses import dataclass


TOPIC_NEW_SPECTRUM = "io.new_spectrum"
TOPIC_NEW_CONFIG = "io.new_config"
TOPIC_ACQ_ERROR = "io.acquisition_error"


@dataclass(frozen=True)
class NewSpectrumEventArgs:
    timestamp: float
    device_index: int
