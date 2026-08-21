import psutil
import os
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("resource_monitor.get_system_stats")
def get_system_stats() -> dict:
    """Returns CPU % and RAM details."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        virtual_mem = psutil.virtual_memory()
        
        ram_total_gb = round(virtual_mem.total / (1024 ** 3), 2)
        ram_used_gb = round(virtual_mem.used / (1024 ** 3), 2)
        ram_percent = virtual_mem.percent
        
        logger.debug(f"Retrieved system stats: CPU {cpu_percent}%, RAM {ram_percent}% used of {ram_total_gb}GB")
        return {
            "cpu_percent": cpu_percent,
            "ram_total_gb": ram_total_gb,
            "ram_used_gb": ram_used_gb,
            "ram_percent": ram_percent
        }
    except Exception as e:
        logger.error(f"Failed to retrieve system stats: {e}", exc_info=True)
        return {
            "cpu_percent": 0.0,
            "ram_total_gb": 0.0,
            "ram_used_gb": 0.0,
            "ram_percent": 0.0
        }

@track_latency("resource_monitor.get_process_stats")
def get_process_stats() -> dict:
    """Returns resource stats for ALFRED process."""
    try:
        process = psutil.Process(os.getpid())
        process_cpu = process.cpu_percent(interval=0.1)
        process_mem = process.memory_info().rss / (1024 ** 2) # in MB
        
        logger.debug(f"Retrieved process stats: CPU {process_cpu}%, RAM {process_mem:.2f}MB")
        return {
            "process_cpu": process_cpu,
            "process_mem_mb": round(process_mem, 2)
        }
    except Exception as e:
        logger.error(f"Failed to retrieve process stats: {e}", exc_info=True)
        return {
            "process_cpu": 0.0,
            "process_mem_mb": 0.0
        }

@track_latency("resource_monitor.format_stats_string")
def format_stats_string() -> str:
    """Returns stats in voice-friendly phrase."""
    sys_stats = get_system_stats()
    proc_stats = get_process_stats()
    
    phrase = (
        f"Sir, system CPU usage is currently at {sys_stats['cpu_percent']} percent, "
        f"and RAM usage is at {sys_stats['ram_percent']} percent, with {sys_stats['ram_used_gb']} gigabytes used out of {sys_stats['ram_total_gb']} gigabytes. "
        f"I am using {proc_stats['process_mem_mb']} megabytes of memory."
    )
    return phrase
