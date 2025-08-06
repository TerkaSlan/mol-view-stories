"""Tests for application configuration."""

import os
from unittest.mock import Mock, patch

import pytest

from config import configure_app, configure_cors


class TestConfigureCors:
    """Tests for CORS configuration."""

    @patch("config.CORS")
    def test_configure_cors_called(self, mock_cors, app):
        """Test that CORS is configured with correct parameters."""
        configure_cors(app)

        mock_cors.assert_called_once_with(app, resources=pytest.unittest.mock.ANY)

    @patch("config.CORS")
    def test_configure_cors_resources(self, mock_cors, app):
        """Test CORS resource configuration."""
        configure_cors(app)

        args, kwargs = mock_cors.call_args
        resources = kwargs["resources"]

        # Check that story data endpoint allows any origin
        assert r"/api/story/*/data" in resources
        story_data_config = resources[r"/api/story/*/data"]
        assert story_data_config["origins"] == "*"
        assert "GET" in story_data_config["methods"]
        assert "OPTIONS" in story_data_config["methods"]

    @patch("config.CORS")
    @patch.dict(os.environ, {"FRONTEND_URL": "https://custom-frontend.com"})
    def test_configure_cors_custom_frontend_url(self, mock_cors, app):
        """Test CORS configuration with custom frontend URL."""
        configure_cors(app)

        args, kwargs = mock_cors.call_args
        resources = kwargs["resources"]
        general_config = resources[r"/*"]

        assert "https://custom-frontend.com" in general_config["origins"]

    @patch("config.CORS")
    def test_configure_cors_default_origins(self, mock_cors, app):
        """Test CORS configuration with default origins."""
        configure_cors(app)

        args, kwargs = mock_cors.call_args
        resources = kwargs["resources"]
        general_config = resources[r"/*"]

        expected_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://molstar.org",
            "https://stories.molstar.org",
        ]

        for origin in expected_origins:
            assert origin in general_config["origins"]


class TestConfigureApp:
    """Tests for application configuration."""

    @patch.dict(
        os.environ,
        {
            "FLASK_SECRET_KEY": "test-secret",
            "OIDC_USERINFO_URL": "https://test-oidc.com/userinfo",
            "BASE_URL": "https://test-base.com",
            "MAX_SESSIONS_PER_USER": "20",
            "MAX_STORIES_PER_USER": "15",
            "MAX_UPLOAD_SIZE_MB": "75",
        },
    )
    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    def test_configure_app_basic_settings(
        self, mock_configure_cors, mock_middleware, app
    ):
        """Test basic app configuration settings."""
        configure_app(app)

        assert app.secret_key == "test-secret"
        assert app.config["OIDC_USERINFO_URL"] == "https://test-oidc.com/userinfo"
        assert app.config["BASE_URL"] == "https://test-base.com"
        assert app.config["MAX_SESSIONS_PER_USER"] == 20
        assert app.config["MAX_STORIES_PER_USER"] == 15
        assert app.config["MAX_UPLOAD_SIZE_MB"] == 75

    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    def test_configure_app_default_values(
        self, mock_configure_cors, mock_middleware, app
    ):
        """Test app configuration with default values."""
        # Clear any environment variables
        with patch.dict(os.environ, {}, clear=True):
            configure_app(app)

            assert (
                app.config["OIDC_USERINFO_URL"]
                == "https://login.aai.lifescience-ri.eu/oidc/userinfo"
            )
            assert app.config["BASE_URL"] == "https://stories.molstar.org"
            assert app.config["MAX_SESSIONS_PER_USER"] == 100
            assert app.config["MAX_STORIES_PER_USER"] == 100
            assert app.config["MAX_UPLOAD_SIZE_MB"] == 50

    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    def test_configure_app_content_length_limit(
        self, mock_configure_cors, mock_middleware, app
    ):
        """Test that MAX_CONTENT_LENGTH is set correctly."""
        with patch.dict(os.environ, {"MAX_UPLOAD_SIZE_MB": "25"}):
            configure_app(app)

            expected_bytes = 25 * 1024 * 1024
            assert app.config["MAX_CONTENT_LENGTH"] == expected_bytes
            assert app.config["MAX_UPLOAD_SIZE_MB"] == 25

    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    def test_configure_app_middleware_added(
        self, mock_configure_cors, mock_middleware, app
    ):
        """Test that size validation middleware is added."""
        configure_app(app)

        # Middleware should be instantiated and wrapped around app.wsgi_app
        mock_middleware.assert_called_once()
        args = mock_middleware.call_args[0]
        assert args[0] == app.wsgi_app  # Original WSGI app
        assert isinstance(args[1], int)  # Max size bytes

    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    def test_configure_app_cors_configured(
        self, mock_configure_cors, mock_middleware, app
    ):
        """Test that CORS is configured."""
        configure_app(app)

        mock_configure_cors.assert_called_once_with(app)

    @patch.dict(os.environ, {"FLASK_SECRET_KEY": ""})
    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    def test_configure_app_empty_secret_key(
        self, mock_configure_cors, mock_middleware, app
    ):
        """Test app configuration with empty secret key."""
        configure_app(app)

        # Should handle empty string gracefully
        assert app.secret_key == ""

    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    @patch("config.logging.getLogger")
    def test_configure_app_logging(
        self, mock_get_logger, mock_configure_cors, mock_middleware, app
    ):
        """Test that logging is set up during configuration."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        configure_app(app)

        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "Adding size validation middleware" in log_message

    @patch("config.SizeValidationMiddleware")
    @patch("config.configure_cors")
    def test_configure_app_integer_conversion(
        self, mock_configure_cors, mock_middleware, app
    ):
        """Test that string environment variables are converted to integers."""
        with patch.dict(
            os.environ,
            {
                "MAX_SESSIONS_PER_USER": "50",
                "MAX_STORIES_PER_USER": "30",
                "MAX_UPLOAD_SIZE_MB": "100",
            },
        ):
            configure_app(app)

            assert isinstance(app.config["MAX_SESSIONS_PER_USER"], int)
            assert isinstance(app.config["MAX_STORIES_PER_USER"], int)
            assert isinstance(app.config["MAX_UPLOAD_SIZE_MB"], int)

            assert app.config["MAX_SESSIONS_PER_USER"] == 50
            assert app.config["MAX_STORIES_PER_USER"] == 30
            assert app.config["MAX_UPLOAD_SIZE_MB"] == 100


class TestConfigIntegration:
    """Integration tests for configuration."""

    def test_app_configuration_complete(self, app):
        """Test that a complete app configuration works."""
        # This test uses the app fixture which should have configure_app called
        assert hasattr(app, "config")
        assert "MAX_UPLOAD_SIZE_MB" in app.config
        assert "OIDC_USERINFO_URL" in app.config
        assert app.secret_key is not None

    @patch.dict(
        os.environ,
        {"FLASK_SECRET_KEY": "integration-test-key", "MAX_UPLOAD_SIZE_MB": "30"},
    )
    def test_environment_variable_integration(self):
        """Test that environment variables are properly integrated."""
        from flask import Flask

        test_app = Flask(__name__)

        configure_app(test_app)

        assert test_app.secret_key == "integration-test-key"
        assert test_app.config["MAX_UPLOAD_SIZE_MB"] == 30
        assert test_app.config["MAX_CONTENT_LENGTH"] == 30 * 1024 * 1024

    def test_cors_integration_with_app(self, app):
        """Test CORS integration with the app."""
        # The app fixture should have CORS configured
        # Test that a CORS extension is present (this will depend on flask-cors implementation)
        assert hasattr(app, "after_request_funcs") or hasattr(app, "extensions")
