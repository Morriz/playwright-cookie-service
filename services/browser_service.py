import glob
import os

from lib.logger import setup_logger

logger = setup_logger(__name__)


def setup_browser_profile(base_dir: str | None = None) -> str:
    """
    Set up persistent browser profile directory.

    Args:
        base_dir: Base directory for browser profile. Defaults to current working directory.

    Returns:
        Path to user data directory
    """
    if base_dir is None:
        base_dir = os.getcwd()

    user_data_dir = os.path.join(base_dir, "browser_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    return user_data_dir


def cleanup_login_traces(user_data_dir: str, login_url: str, request_id: str) -> None:
    """
    Remove trace files that contain the login URL.

    Args:
        user_data_dir: Path to browser profile directory
        login_url: Login URL to search for
        request_id: Request ID for logging
    """
    traces_dir = os.path.join(user_data_dir, "traces")
    if not os.path.exists(traces_dir):
        return

    trace_files = glob.glob(os.path.join(traces_dir, "*.network"))
    for trace_file in trace_files:
        try:
            with open(trace_file) as f:
                if login_url in f.read():
                    os.remove(trace_file)
                    logger.info(f"[{request_id}] Removed old trace file: {trace_file}")
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to read/remove trace file {trace_file}: {e}")
