from FILES.utils import get_date, get_time
from FILES.resource_monitor import format_stats_string, get_system_stats
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.time")
def handle_time() -> str:
    logger.info("Get current time requested")
    return get_time()

@track_latency("commands.process_command.date")
def handle_date() -> str:
    logger.info("Get current date requested")
    return get_date()

@track_latency("commands.process_command.system_status")
def handle_system_status() -> str:
    logger.info("System status stats requested")
    return format_stats_string()

@track_latency("commands.process_command.cpu_usage")
def handle_cpu_usage() -> str:
    logger.info("System CPU usage requested")
    stats = get_system_stats()
    return f"Sir, CPU usage is currently at {stats['cpu_percent']} percent."

@track_latency("commands.process_command.memory_usage")
def handle_memory_usage() -> str:
    logger.info("System RAM usage requested")
    stats = get_system_stats()
    return f"Sir, RAM usage is currently at {stats['ram_percent']} percent, with {stats['ram_used_gb']} gigabytes used out of {stats['ram_total_gb']} gigabytes."
