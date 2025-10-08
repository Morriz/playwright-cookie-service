import glob
import json
import os

from lib.logger import setup_logger

logger = setup_logger(__name__)


def extract_cookies_from_trace(
    user_data_dir: str, login_url: str, request_id: str
) -> str:
    """
    Extract cookies from browser trace files.

    Args:
        user_data_dir: Path to browser profile directory
        login_url: Login URL to match in trace
        request_id: Request ID for logging

    Returns:
        Cookie string

    Raises:
        Exception: If no trace files found or no cookies extracted
    """
    traces_dir = os.path.join(user_data_dir, "traces")
    trace_files = glob.glob(os.path.join(traces_dir, "*.network"))

    if not trace_files:
        raise Exception("No trace files found")

    # Find trace file containing login_url
    matching_trace = None
    for trace_file in sorted(trace_files, key=os.path.getmtime, reverse=True):
        try:
            with open(trace_file) as f:
                if login_url in f.read():
                    matching_trace = trace_file
                    break
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to read trace file {trace_file}: {e}")

    if not matching_trace:
        raise Exception(f"No trace file found containing {login_url}")

    logger.info(f"[{request_id}] Reading trace file: {matching_trace}")
    latest_trace = matching_trace

    all_cookies = {}
    api_calls_found = []
    sample_headers = None

    with open(latest_trace) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                snapshot = record.get("snapshot", {})
                request_data = snapshot.get("request", {})
                url = request_data.get("url", "")

                if login_url in url:
                    api_calls_found.append(url)
                    headers = request_data.get("headers", [])

                    if sample_headers is None and headers:
                        sample_headers = headers

                    for header in headers:
                        header_name = header.get("name", "").lower()
                        if header_name == "cookie":
                            cookie_value = header.get("value", "")
                            if cookie_value:
                                for cookie in cookie_value.split("; "):
                                    if "=" in cookie:
                                        name, value = cookie.split("=", 1)
                                        all_cookies[name] = value
            except json.JSONDecodeError:
                continue

    logger.info(f"[{request_id}] Found {len(api_calls_found)} API calls in trace")
    logger.debug(f"[{request_id}] API calls: {api_calls_found[:5]}")

    if sample_headers:
        header_names = [h.get("name", "") for h in sample_headers]
        logger.info(f"[{request_id}] Sample headers from first API call: {header_names}")
    else:
        logger.warning(f"[{request_id}] No headers found in API calls")

    if not all_cookies:
        raise Exception(
            f"No cookies found in trace file. Found {len(api_calls_found)} API calls but no cookies."
        )

    cookie_string = "; ".join([f"{name}={value}" for name, value in all_cookies.items()])
    logger.info(f"[{request_id}] Collected {len(all_cookies)} unique cookies")
    logger.info(f"[{request_id}] Successfully extracted cookies from trace")

    return cookie_string
