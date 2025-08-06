"""Tests for error handling utilities."""

from unittest.mock import Mock, patch

import pytest
from werkzeug.exceptions import RequestEntityTooLarge

from error_handlers import APIError, error_handler, handle_api_error


class TestAPIError:
    """Tests for APIError exception class."""

    def test_api_error_basic(self):
        """Test basic APIError creation."""
        error = APIError("Test error")

        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.details == {}

    def test_api_error_with_status_code(self):
        """Test APIError with custom status code."""
        error = APIError("Not found", status_code=404)

        assert error.message == "Not found"
        assert error.status_code == 404
        assert error.details == {}

    def test_api_error_with_details(self):
        """Test APIError with details."""
        details = {"field": "username", "reason": "already exists"}
        error = APIError("Validation error", status_code=422, details=details)

        assert error.message == "Validation error"
        assert error.status_code == 422
        assert error.details == details

    def test_api_error_inheritance(self):
        """Test that APIError inherits from Exception."""
        error = APIError("Test error")
        assert isinstance(error, Exception)

    def test_api_error_string_representation(self):
        """Test string representation of APIError."""
        error = APIError("Test error")
        # Should not raise an error when converted to string
        str(error)


class TestHandleApiError:
    """Tests for handle_api_error function."""

    def test_handle_api_error_basic(self, app):
        """Test basic error handling."""
        with app.app_context():
            error = APIError("Test error", status_code=400)
            response, status_code = handle_api_error(error)

            assert status_code == 400
            data = response.get_json()
            assert data["error"] is True
            assert data["message"] == "Test error"
            assert data["status_code"] == 400

    def test_handle_api_error_with_details(self, app):
        """Test error handling with details."""
        with app.app_context():
            details = {"field": "email", "reason": "invalid format"}
            error = APIError("Validation failed", status_code=422, details=details)
            response, status_code = handle_api_error(error)

            assert status_code == 422
            data = response.get_json()
            assert data["error"] is True
            assert data["message"] == "Validation failed"
            assert data["status_code"] == 422
            assert data["details"] == details

    def test_handle_api_error_no_details(self, app):
        """Test error handling without details."""
        with app.app_context():
            error = APIError("Simple error")
            response, status_code = handle_api_error(error)

            data = response.get_json()
            assert "details" not in data

    def test_handle_api_error_empty_details(self, app):
        """Test error handling with empty details."""
        with app.app_context():
            error = APIError("Error with empty details", details={})
            response, status_code = handle_api_error(error)

            data = response.get_json()
            assert "details" not in data


class TestErrorHandlerDecorator:
    """Tests for error_handler decorator."""

    def test_error_handler_success(self, app):
        """Test error handler with successful function execution."""
        with app.app_context():

            @error_handler
            def test_function():
                return {"status": "success"}

            result = test_function()
            assert result == {"status": "success"}

    def test_error_handler_api_error(self, app):
        """Test error handler with APIError."""
        with app.app_context():

            @error_handler
            def test_function():
                raise APIError("Test API error", status_code=403)

            response, status_code = test_function()

            assert status_code == 403
            data = response.get_json()
            assert data["error"] is True
            assert data["message"] == "Test API error"

    def test_error_handler_request_entity_too_large(self, app):
        """Test error handler with RequestEntityTooLarge exception."""
        with app.app_context():

            @error_handler
            def test_function():
                raise RequestEntityTooLarge("File too large")

            response, status_code = test_function()

            assert status_code == 413
            data = response.get_json()
            assert data["error"] is True
            assert data["message"] == "File size too large"
            assert data["details"]["type"] == "RequestEntityTooLarge"
            assert data["details"]["max_size_mb"] == 50

    def test_error_handler_unexpected_exception(self, app):
        """Test error handler with unexpected exception."""
        with app.app_context():

            @error_handler
            def test_function():
                raise ValueError("Unexpected error")

            response, status_code = test_function()

            assert status_code == 500
            data = response.get_json()
            assert data["error"] is True
            assert data["message"] == "An unexpected error occurred"
            assert data["details"]["type"] == "ValueError"
            assert data["details"]["description"] == "Unexpected error"

    def test_error_handler_preserves_function_metadata(self):
        """Test that error handler preserves function metadata."""

        @error_handler
        def test_function():
            """Test function docstring."""
            return "test"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."

    @patch("error_handlers.logger")
    def test_error_handler_logging_api_error(self, mock_logger, app):
        """Test that APIError is logged correctly."""
        with app.app_context():

            @error_handler
            def test_function():
                raise APIError("Test error", details={"test": "data"})

            test_function()

            mock_logger.error.assert_called_once_with(
                "API Error: Test error", extra={"details": {"test": "data"}}
            )

    @patch("error_handlers.logger")
    def test_error_handler_logging_request_entity_too_large(self, mock_logger, app):
        """Test that RequestEntityTooLarge is logged correctly."""
        with app.app_context():

            @error_handler
            def test_function():
                raise RequestEntityTooLarge("File size exceeded")

            test_function()

            mock_logger.warning.assert_called_once()

    @patch("error_handlers.logger")
    def test_error_handler_logging_unexpected_error(self, mock_logger, app):
        """Test that unexpected errors are logged correctly."""
        with app.app_context():

            @error_handler
            def test_function():
                raise RuntimeError("Unexpected runtime error")

            test_function()

            mock_logger.exception.assert_called_once_with("Unexpected error occurred")

    def test_error_handler_with_args_kwargs(self, app):
        """Test error handler with function that takes arguments."""
        with app.app_context():

            @error_handler
            def test_function(arg1, arg2, kwarg1=None):
                if arg1 == "error":
                    raise APIError("Test error")
                return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

            # Test successful execution
            result = test_function("test", "value", kwarg1="keyword")
            assert result == {"arg1": "test", "arg2": "value", "kwarg1": "keyword"}

            # Test error execution
            response, status_code = test_function("error", "value")
            assert status_code == 400
            data = response.get_json()
            assert data["message"] == "Test error"
