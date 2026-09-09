from FILES.utils import get_date, get_time
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.time")
def handle_time() -> str:
    """Returns formatted current time."""
    logger.info("Get current time requested")
    return get_time()

@track_latency("commands.process_command.date")
def handle_date() -> str:
    """Returns formatted current date."""
    logger.info("Get current date requested")
    return get_date()
