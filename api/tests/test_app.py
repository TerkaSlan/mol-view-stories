"""Tests for the main Flask application."""

import json
from unittest.mock import patch

import pytest

from app import app as flask_app


class TestAppConfiguration:
    """Tests for Flask app configuration."""

    def test_app_creation(self, app):
        """Test that the app is created properly."""
        assert app is not None
        assert app.config["TESTING"] is True

    def test_health_check_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["message"] == "Service is ready"

    def test_blueprints_registered(self, app):
        """Test that all blueprints are registered."""
        blueprint_names = [bp.name for bp in app.blueprints.values()]

        assert "sessions" in blueprint_names
        assert "stories" in blueprint_names
        assert "admin" in blueprint_names


class TestGlobalErrorHandlers:
    """Tests for global error handlers."""

    def test_request_entity_too_large_handler(self, app):
        """Test the global RequestEntityTooLarge error handler."""
        with app.test_request_context():
            from werkzeug.exceptions import RequestEntityTooLarge

            # Trigger the error handler
            with app.app_context():
                error = RequestEntityTooLarge()
                response, status_code = flask_app.handle_file_too_large(error)

                assert status_code == 413
                data = response.get_json()
                assert data["error"] is True
                assert data["message"] == "File size too large"
                assert data["status_code"] == 413
                assert "max_size_mb" in data["details"]

    def test_validate_request_size_skip_endpoints(self, app):
        """Test that request size validation skips certain endpoints."""
        with app.test_request_context("/ready", method="POST"):
            # Should return None (no validation)
            result = flask_app.validate_request_size()
            assert result is None

    def test_validate_request_size_skip_get_requests(self, app):
        """Test that request size validation skips GET requests."""
        with app.test_request_context("/api/test", method="GET"):
            result = flask_app.validate_request_size()
            assert result is None

    def test_validate_request_size_valid_post(self, app):
        """Test request size validation with valid POST request."""
        with app.test_request_context(
            "/api/test", method="POST", headers={"Content-Length": "1024"}
        ):
            result = flask_app.validate_request_size()
            assert result is None

    def test_validate_request_size_large_post(self, app):
        """Test request size validation with large POST request."""
        large_size = 100 * 1024 * 1024  # 100MB

        with app.test_request_context(
            "/api/test", method="POST", headers={"Content-Length": str(large_size)}
        ):
            response, status_code = flask_app.validate_request_size()

            assert status_code == 413
            data = response.get_json()
            assert data["error"] is True
            assert "Request payload too large" in data["message"]

    def test_validate_request_size_put_request(self, app):
        """Test request size validation with PUT request."""
        large_size = 100 * 1024 * 1024  # 100MB

        with app.test_request_context(
            "/api/test", method="PUT", headers={"Content-Length": str(large_size)}
        ):
            response, status_code = flask_app.validate_request_size()

            assert status_code == 413
            data = response.get_json()
            assert data["error"] is True

    def test_validate_request_size_no_content_length(self, app):
        """Test request size validation without Content-Length header."""
        with app.test_request_context("/api/test", method="POST"):
            # Should not raise error when no Content-Length header
            result = flask_app.validate_request_size()
            assert result is None


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.options("/ready")

        # Should have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers

    def test_cors_preflight_request(self, client):
        """Test CORS preflight request handling."""
        response = client.options(
            "/api/session",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )

        assert response.status_code == 200


class TestAppIntegration:
    """Integration tests for the main app."""

    def test_app_starts_without_errors(self):
        """Test that the app can be created without errors."""
        from app import app

        assert app is not None
        assert app.name == "app"

    @patch("app.configure_app")
    def test_app_configuration_called(self, mock_configure):
        """Test that app configuration is called during setup."""
        # Import triggers app creation
        import importlib

        import app as app_module

        importlib.reload(app_module)

        mock_configure.assert_called_once()

    def test_wsgi_middleware_added(self, app):
        """Test that WSGI middleware is properly added."""
        # The middleware should be wrapped around the app
        assert hasattr(app, "wsgi_app")

        # Test that the middleware works
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_LENGTH": "1024",
            "wsgi.input": None,
            "PATH_INFO": "/test",
            "QUERY_STRING": "",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "5000",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.errors": None,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        def start_response(status, headers):
            pass

        # This should not raise an error
        response = app.wsgi_app(environ, start_response)
        assert response is not None
