import os
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.decompress_logs")
def handle_decompress_logs(command: str) -> str:
    try:
        from FILES.log_compressor import decompress_log
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logs_dir = os.path.join(base_dir, "logs")
        count = 0
        if os.path.exists(logs_dir):
            for item in os.listdir(logs_dir):
                if item.endswith(".compressed_logs"):
                    decompress_log(os.path.join(logs_dir, item))
                    count += 1
        if count > 0:
            return f"Successfully decompressed {count} log file(s), sir."
        else:
            return "No compressed log files were found in the logs directory, sir."
    except Exception as e:
        logger.error(f"Failed to decompress logs: {e}", exc_info=True)
        return f"Failed to decompress logs: {str(e)}"

@track_latency("commands.process_command.compress_logs")
def handle_compress_logs(command: str) -> str:
    try:
        from FILES.log_compressor import compress_all_rotated_logs
        compress_all_rotated_logs()
        return "Log compression process completed, sir."
    except Exception as e:
        logger.error(f"Failed to compress logs: {e}", exc_info=True)
        return f"Failed to compress logs: {str(e)}"
