from __future__ import annotations

from base_core.framework.concurrency.interfaces import ITaskRunner
from base_core.framework.events import EventBus
from base_core.framework.json.json_endpoint import JsonlSubprocessEndpoint
from base_core.framework.json.device_service import DeviceService


from phase_control_essentials.buffer import FrameBuffer
from phase_control_essentials.events import TOPIC_NEW_SPECTRUM, NewSpectrumEventArgs
from phase_control_essentials.stream import StreamFrame, StreamMeta
from spm_002.config import SpectrometerConfig
from spm_002.enums import CmdName, MsgType


class SpectrometerService(DeviceService):
    def __init__(
        self,
        io: ITaskRunner,
        endpoint: JsonlSubprocessEndpoint,
        bus: EventBus,
        buffer: FrameBuffer,
    ) -> None:
        super().__init__(io, endpoint)
        self._bus = bus
        self._buffer = buffer
        self._config = SpectrometerConfig()

        self.register_handler(MsgType.META, self._on_meta)
        self.register_handler(MsgType.FRAME, self._on_frame)
        

    @property
    def config(self) -> SpectrometerConfig:
        return self._config
    
    def _on_meta(self, msg: dict) -> None:
        meta = StreamMeta(
            device_index=msg["device_index"],
            num_pixels=msg["num_pixels"],
            wavelengths=msg.get("wavelengths"),
        )
        self._buffer.set_meta_data(meta)

    def _on_frame(self, msg: dict) -> None:
        frame = StreamFrame(
            timestamp=msg["timestamp"],
            device_index=msg["device_index"],
            counts=msg["counts"],
        )
        self._buffer.set(frame)
        self._bus.publish(
            TOPIC_NEW_SPECTRUM,
            NewSpectrumEventArgs(timestamp=frame.timestamp, device_index=frame.device_index),
        )

    def set_config_async(self):
        return self.request_async(
            {"type": MsgType.CMD, "name": CmdName.SET_CONFIG, "args": self._config.to_json()},
            key="spectrometer.set_config",
            cancel_previous=True,
        )

    def shutdown_async(self):
        return self.request_async(
            {"type": MsgType.CMD, "name": CmdName.SHUTDOWN},
            key="spectrometer.shutdown",
            cancel_previous=True,
        )
