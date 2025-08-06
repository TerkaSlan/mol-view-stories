"""Tests for utility functions."""

import io
import json
from unittest.mock import Mock, patch

import pytest
from utils import SizeLimitedStream, SizeValidationMiddleware, validate_payload_size
from werkzeug.exceptions import RequestEntityTooLarge


class TestValidatePayloadSize:
    """Tests for validate_payload_size decorator."""

    def test_validate_payload_size_success(self, app):
        """Test successful validation with valid payload size."""
        with app.test_request_context("/", content_length=1024):

            @validate_payload_size()
            def test_view():
                return {"status": "ok"}

            result = test_view()
            assert result["status"] == "ok"

    def test_validate_payload_size_too_large(self, app):
        """Test validation failure with payload too large."""
        # 100MB payload size
        large_size = 100 * 1024 * 1024

        with app.test_request_context("/", content_length=large_size):

            @validate_payload_size()
            def test_view():
                return {"status": "ok"}

            response, status_code = test_view()

            assert status_code == 413
            response_data = response.get_json()
            assert response_data["error"] is True
            assert "Request payload too large" in response_data["message"]
            assert response_data["details"]["max_size_mb"] == 50

    def test_validate_payload_size_custom_limit(self, app):
        """Test validation with custom size limit."""
        with app.test_request_context("/", content_length=15 * 1024 * 1024):  # 15MB

            @validate_payload_size(max_size_mb=10)
            def test_view():
                return {"status": "ok"}

            response, status_code = test_view()

            assert status_code == 413
            response_data = response.get_json()
            assert response_data["details"]["max_size_mb"] == 10

    def test_validate_payload_size_no_content_length(self, app):
        """Test validation failure when no Content-Length header."""
        with app.test_request_context("/"):

            @validate_payload_size()
            def test_view():
                return {"status": "ok"}

            response, status_code = test_view()

            assert status_code == 400
            response_data = response.get_json()
            assert "Content-Length header required" in response_data["message"]

    def test_validate_payload_size_zero_content_length(self, app):
        """Test validation success with zero content length."""
        with app.test_request_context("/", content_length=0):

            @validate_payload_size()
            def test_view():
                return {"status": "ok"}

            result = test_view()
            assert result["status"] == "ok"


class TestSizeLimitedStream:
    """Tests for SizeLimitedStream class."""

    def test_size_limited_stream_read_within_limit(self):
        """Test reading within size limit."""
        data = b"Hello, World!"
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=100)

        result = limited_stream.read()
        assert result == data
        assert limited_stream.bytes_read == len(data)

    def test_size_limited_stream_read_exceeds_limit(self):
        """Test reading that exceeds size limit."""
        data = b"Hello, World!" * 100  # Large data
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=10)

        with pytest.raises(RequestEntityTooLarge):
            limited_stream.read()

    def test_size_limited_stream_read_partial(self):
        """Test partial reading within limit."""
        data = b"Hello, World!"
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=100)

        result1 = limited_stream.read(5)
        result2 = limited_stream.read(8)

        assert result1 == b"Hello"
        assert result2 == b", World!"
        assert limited_stream.bytes_read == 13

    def test_size_limited_stream_read_partial_exceeds(self):
        """Test partial reading that eventually exceeds limit."""
        data = b"Hello, World!"
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=10)

        result1 = limited_stream.read(5)  # Should work
        assert result1 == b"Hello"

        with pytest.raises(RequestEntityTooLarge):
            limited_stream.read(10)  # Should exceed limit

    def test_size_limited_stream_readline(self):
        """Test readline within limit."""
        data = b"Line 1\nLine 2\nLine 3\n"
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=100)

        line1 = limited_stream.readline()
        line2 = limited_stream.readline()

        assert line1 == b"Line 1\n"
        assert line2 == b"Line 2\n"
        assert limited_stream.bytes_read == 14

    def test_size_limited_stream_readline_exceeds(self):
        """Test readline that exceeds limit."""
        data = b"Very long line that exceeds the limit\n"
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=10)

        with pytest.raises(RequestEntityTooLarge):
            limited_stream.readline()

    def test_size_limited_stream_readlines(self):
        """Test readlines within limit."""
        data = b"Line 1\nLine 2\nLine 3\n"
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=100)

        lines = limited_stream.readlines()

        assert lines == [b"Line 1\n", b"Line 2\n", b"Line 3\n"]
        assert limited_stream.bytes_read == len(data)

    def test_size_limited_stream_readlines_exceeds(self):
        """Test readlines that exceeds limit."""
        data = b"Line 1\n" * 100  # Many lines
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=10)

        with pytest.raises(RequestEntityTooLarge):
            limited_stream.readlines()

    def test_size_limited_stream_custom_logger(self):
        """Test SizeLimitedStream with custom logger."""
        mock_logger = Mock()
        data = b"Too much data"
        stream = io.BytesIO(data)
        limited_stream = SizeLimitedStream(stream, max_size=5, logger=mock_logger)

        with pytest.raises(RequestEntityTooLarge):
            limited_stream.read()

        mock_logger.warning.assert_called_once()

    def test_size_limited_stream_getattr(self):
        """Test that other attributes are delegated to wrapped stream."""
        stream = io.BytesIO(b"test")
        limited_stream = SizeLimitedStream(stream, max_size=100)

        # Test that we can access stream attributes
        assert hasattr(limited_stream, "seek")
        assert hasattr(limited_stream, "tell")

        # Test seek functionality
        limited_stream.seek(0)
        assert limited_stream.tell() == 0


class TestSizeValidationMiddleware:
    """Tests for SizeValidationMiddleware class."""

    def test_middleware_allows_small_request(self):
        """Test middleware allows requests within size limit."""

        def dummy_app(environ, start_response):
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"OK"]

        middleware = SizeValidationMiddleware(dummy_app, max_size_bytes=1024 * 1024)

        environ = {"CONTENT_LENGTH": "1024", "wsgi.input": io.BytesIO(b"x" * 1024)}

        def start_response(status, headers):
            assert status == "200 OK"

        result = list(middleware(environ, start_response))
        assert result == [b"OK"]

    def test_middleware_rejects_large_request(self):
        """Test middleware rejects requests that exceed size limit."""

        def dummy_app(environ, start_response):
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"OK"]

        middleware = SizeValidationMiddleware(dummy_app, max_size_bytes=1024)

        large_size = 2048  # Exceeds 1024 byte limit
        environ = {
            "CONTENT_LENGTH": str(large_size),
            "wsgi.input": io.BytesIO(b"x" * large_size),
        }

        def start_response(status, headers):
            assert status == "413 Payload Too Large"
            assert ("Content-Type", "application/json") in headers

        result = list(middleware(environ, start_response))
        response_data = json.loads(result[0].decode("utf-8"))

        assert response_data["error"] is True
        assert "Request payload too large" in response_data["message"]
        assert response_data["status_code"] == 413

    def test_middleware_handles_invalid_content_length(self):
        """Test middleware handles invalid Content-Length header."""

        def dummy_app(environ, start_response):
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"OK"]

        middleware = SizeValidationMiddleware(dummy_app, max_size_bytes=1024)

        environ = {
            "CONTENT_LENGTH": "invalid",  # Invalid content length
            "wsgi.input": io.BytesIO(b"test"),
        }

        def start_response(status, headers):
            assert status == "200 OK"

        result = list(middleware(environ, start_response))
        assert result == [b"OK"]

    def test_middleware_handles_missing_content_length(self):
        """Test middleware handles missing Content-Length header."""

        def dummy_app(environ, start_response):
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"OK"]

        middleware = SizeValidationMiddleware(dummy_app, max_size_bytes=1024)

        environ = {"wsgi.input": io.BytesIO(b"test")}

        def start_response(status, headers):
            assert status == "200 OK"

        result = list(middleware(environ, start_response))
        assert result == [b"OK"]

    def test_middleware_wraps_input_stream(self):
        """Test middleware wraps wsgi.input with SizeLimitedStream."""

        def dummy_app(environ, start_response):
            # Check that wsgi.input is wrapped
            assert isinstance(environ["wsgi.input"], SizeLimitedStream)
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"OK"]

        middleware = SizeValidationMiddleware(dummy_app, max_size_bytes=1024)

        original_stream = io.BytesIO(b"test")
        environ = {"CONTENT_LENGTH": "4", "wsgi.input": original_stream}

        def start_response(status, headers):
            pass

        list(middleware(environ, start_response))

    def test_middleware_create_error_response(self):
        """Test error response creation."""

        def dummy_app(environ, start_response):
            return [b"OK"]

        middleware = SizeValidationMiddleware(dummy_app, max_size_bytes=1024 * 1024)

        response = middleware._create_error_response(received_size=2 * 1024 * 1024)
        response_data = json.loads(response.decode("utf-8"))

        assert response_data["error"] is True
        assert response_data["status_code"] == 413
        assert response_data["details"]["max_size_mb"] == 1.0
        assert response_data["details"]["received_size_mb"] == 2.0

    def test_middleware_custom_logger(self):
        """Test middleware with custom logger."""
        mock_logger = Mock()

        def dummy_app(environ, start_response):
            return [b"OK"]

        middleware = SizeValidationMiddleware(
            dummy_app, max_size_bytes=1024, logger=mock_logger
        )

        environ = {
            "CONTENT_LENGTH": "2048",  # Exceeds limit
            "wsgi.input": io.BytesIO(b"x" * 2048),
        }

        def start_response(status, headers):
            pass

        list(middleware(environ, start_response))
        mock_logger.warning.assert_called_once()
