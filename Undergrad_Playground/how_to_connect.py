from concurrent.futures import ThreadPoolExecutor

from base_core.framework.concurrency import task_runner
from base_core.framework.events import EventBus
from base_core.framework.json.json_endpoint import JsonlSubprocessEndpoint
from phase_control_essentials.buffer import FrameBuffer
from phase_control_essentials.service import SpectrometerService
from spm_002.config import PYTHON32_PATH
from spm_002.spectrometer_server import SpectrometerServer


io_spectrometer_exec = ThreadPoolExecutor(max_workers=2, thread_name_prefix="io.spectrometer")
runner =  task_runner.TaskRunner(io_spectrometer_exec)
endpoint = JsonlSubprocessEndpoint(argv=[PYTHON32_PATH, "-u", "-m", "spm_002.spectrometer_server"],)
bus = EventBus()
frame_buffer = FrameBuffer()
server = SpectrometerService(
                io=runner,
                endpoint=endpoint,
                bus=bus,                 
                buffer=frame_buffer)