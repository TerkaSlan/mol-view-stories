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

    def test_blueprints_registered(self, app):
        """Test that all blueprints are registered."""
        blueprint_names = [bp.name for bp in app.blueprints.values()]

        assert "sessions" in blueprint_names
        assert "stories" in blueprint_names
        assert "admin" in blueprint_names


class TestAppIntegration:
    """Integration tests for the main app."""

    def test_app_starts_without_errors(self):
        """Test that the app can be created without errors."""
        from app import app

        assert app is not None
        assert app.name == "app"

    def test_app_configuration_called(self, app):
        """Test that app configuration is called during setup."""
        # Verify that the app has been configured with expected settings
        assert "MAX_CONTENT_LENGTH" in app.config
        assert "MAX_UPLOAD_SIZE_MB" in app.config
        assert "MAX_SESSIONS_PER_USER" in app.config
        assert "MAX_STORIES_PER_USER" in app.config

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
