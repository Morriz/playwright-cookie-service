"""Unit tests for services modules."""

import json
import os
import tempfile

import pytest

from services.browser_service import cleanup_login_traces
from services.cookie_extractor import extract_cookies_from_trace


class TestBrowserService:
    """Tests for browser_service.py"""

    def test_cleanup_login_traces_removes_matching(self):
        """Test that cleanup removes traces containing login URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data_dir = os.path.join(tmpdir, "browser_profile")
            traces_dir = os.path.join(user_data_dir, "traces")
            os.makedirs(traces_dir)

            # Create trace file with login URL
            trace1 = os.path.join(traces_dir, "trace1.network")
            with open(trace1, "w") as f:
                f.write("https://x.com/login some content")

            # Create trace file without login URL
            trace2 = os.path.join(traces_dir, "trace2.network")
            with open(trace2, "w") as f:
                f.write("https://example.com some content")

            cleanup_login_traces(user_data_dir, "https://x.com/login", "test-id")

            assert not os.path.exists(trace1)
            assert os.path.exists(trace2)

    def test_cleanup_login_traces_no_traces_dir(self):
        """Test cleanup when traces directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data_dir = os.path.join(tmpdir, "browser_profile")
            os.makedirs(user_data_dir)

            # Should not raise error
            cleanup_login_traces(user_data_dir, "https://x.com/login", "test-id")


class TestCookieExtractor:
    """Tests for cookie_extractor.py"""

    def test_extract_cookies_from_trace_success(self):
        """Test successful cookie extraction from trace file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data_dir = os.path.join(tmpdir, "browser_profile")
            traces_dir = os.path.join(user_data_dir, "traces")
            os.makedirs(traces_dir)

            # Create trace file with cookies
            trace_file = os.path.join(traces_dir, "trace.network")
            trace_data = {
                "snapshot": {
                    "request": {
                        "url": "https://x.com/login",
                        "headers": [
                            {"name": "Cookie", "value": "auth_token=abc123; ct0=xyz789"},
                            {"name": "User-Agent", "value": "Mozilla/5.0"},
                        ],
                    }
                }
            }

            with open(trace_file, "w") as f:
                f.write(json.dumps(trace_data) + "\n")

            cookies = extract_cookies_from_trace(user_data_dir, "https://x.com/login", "test-id")

            assert "auth_token=abc123" in cookies
            assert "ct0=xyz789" in cookies

    def test_extract_cookies_merges_from_multiple_requests(self):
        """Test that cookies are merged from multiple API calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data_dir = os.path.join(tmpdir, "browser_profile")
            traces_dir = os.path.join(user_data_dir, "traces")
            os.makedirs(traces_dir)

            trace_file = os.path.join(traces_dir, "trace.network")

            # First request with some cookies
            trace1 = {
                "snapshot": {
                    "request": {
                        "url": "https://x.com/login",
                        "headers": [{"name": "Cookie", "value": "cookie1=value1"}],
                    }
                }
            }

            # Second request with more cookies
            trace2 = {
                "snapshot": {
                    "request": {
                        "url": "https://x.com/login/verify",
                        "headers": [{"name": "Cookie", "value": "cookie1=value1; cookie2=value2"}],
                    }
                }
            }

            with open(trace_file, "w") as f:
                f.write(json.dumps(trace1) + "\n")
                f.write(json.dumps(trace2) + "\n")

            cookies = extract_cookies_from_trace(user_data_dir, "https://x.com/login", "test-id")

            assert "cookie1=value1" in cookies
            assert "cookie2=value2" in cookies

    def test_extract_cookies_no_trace_files(self):
        """Test error when no trace files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data_dir = os.path.join(tmpdir, "browser_profile")
            traces_dir = os.path.join(user_data_dir, "traces")
            os.makedirs(traces_dir)

            with pytest.raises(Exception, match="No trace files found"):
                extract_cookies_from_trace(user_data_dir, "https://x.com/login", "test-id")

    def test_extract_cookies_no_matching_url(self):
        """Test error when no trace contains login URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data_dir = os.path.join(tmpdir, "browser_profile")
            traces_dir = os.path.join(user_data_dir, "traces")
            os.makedirs(traces_dir)

            trace_file = os.path.join(traces_dir, "trace.network")
            trace_data = {
                "snapshot": {
                    "request": {
                        "url": "https://example.com",
                        "headers": [{"name": "Cookie", "value": "test=value"}],
                    }
                }
            }

            with open(trace_file, "w") as f:
                f.write(json.dumps(trace_data) + "\n")

            with pytest.raises(Exception, match="No trace file found containing"):
                extract_cookies_from_trace(user_data_dir, "https://x.com/login", "test-id")

    def test_extract_cookies_no_cookies_in_trace(self):
        """Test error when trace exists but has no cookies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data_dir = os.path.join(tmpdir, "browser_profile")
            traces_dir = os.path.join(user_data_dir, "traces")
            os.makedirs(traces_dir)

            trace_file = os.path.join(traces_dir, "trace.network")
            trace_data = {
                "snapshot": {
                    "request": {
                        "url": "https://x.com/login",
                        "headers": [{"name": "User-Agent", "value": "Mozilla/5.0"}],
                    }
                }
            }

            with open(trace_file, "w") as f:
                f.write(json.dumps(trace_data) + "\n")

            with pytest.raises(Exception, match="No cookies found in trace file"):
                extract_cookies_from_trace(user_data_dir, "https://x.com/login", "test-id")
