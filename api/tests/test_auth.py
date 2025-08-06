"""Tests for authentication module."""

from unittest.mock import Mock, patch

import pytest
import requests

from auth import get_user_from_request, make_userinfo_request, session_required
from error_handlers import APIError


class TestSessionRequired:
    """Tests for session_required decorator."""

    def test_session_required_with_valid_session(self, app, mock_session_user):
        """Test that session_required allows access with valid session."""
        with app.test_request_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess["user"] = mock_session_user

                @session_required
                def test_view(current_user):
                    return {"user": current_user}

                result = test_view()
                assert result["user"] == mock_session_user

    def test_session_required_without_session(self, app):
        """Test that session_required raises error without session."""
        with app.test_request_context():

            @session_required
            def test_view(current_user):
                return {"user": current_user}

            with pytest.raises(APIError) as exc_info:
                test_view()

            assert exc_info.value.status_code == 401
            assert "Authentication required" in str(exc_info.value)

    def test_session_required_with_empty_session(self, app):
        """Test that session_required raises error with empty session."""
        with app.test_request_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess["user"] = None

                @session_required
                def test_view(current_user):
                    return {"user": current_user}

                with pytest.raises(APIError) as exc_info:
                    test_view()

                assert exc_info.value.status_code == 401


class TestMakeUserinfoRequest:
    """Tests for make_userinfo_request function."""

    @patch("auth.requests.Session")
    def test_make_userinfo_request_success(self, mock_session_class, mock_userinfo):
        """Test successful userinfo request."""
        # Setup mock
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = mock_userinfo
        mock_session.get.return_value = mock_response
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Call function
        result = make_userinfo_request("test-token")

        # Assertions
        assert result == mock_userinfo
        mock_session.get.assert_called_once_with(
            "https://login.aai.lifescience-ri.eu/oidc/userinfo",
            headers={"Authorization": "Bearer test-token"},
            timeout=5,
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("auth.requests.Session")
    def test_make_userinfo_request_with_custom_endpoint(
        self, mock_session_class, mock_userinfo
    ):
        """Test userinfo request with custom endpoint."""
        with patch.dict(
            "os.environ", {"OIDC_USERINFO_URL": "http://custom-oidc/userinfo"}
        ):
            # Setup mock
            mock_session = Mock()
            mock_response = Mock()
            mock_response.json.return_value = mock_userinfo
            mock_session.get.return_value = mock_response
            mock_session_class.return_value.__enter__.return_value = mock_session

            # Call function
            result = make_userinfo_request("test-token")

            # Assertions
            assert result == mock_userinfo
            mock_session.get.assert_called_once_with(
                "http://custom-oidc/userinfo",
                headers={"Authorization": "Bearer test-token"},
                timeout=5,
            )

    @patch("auth.requests.Session")
    def test_make_userinfo_request_network_error(self, mock_session_class):
        """Test userinfo request with network error."""
        # Setup mock to raise exception
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Call function and expect error
        with pytest.raises(APIError) as exc_info:
            make_userinfo_request("test-token")

        assert exc_info.value.status_code == 401
        assert "Failed to validate token" in str(exc_info.value)

    @patch("auth.requests.Session")
    def test_make_userinfo_request_http_error(self, mock_session_class):
        """Test userinfo request with HTTP error."""
        # Setup mock
        mock_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_session.get.return_value = mock_response
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Call function and expect error
        with pytest.raises(APIError) as exc_info:
            make_userinfo_request("test-token")

        assert exc_info.value.status_code == 401
        assert "Failed to validate token" in str(exc_info.value)

    @patch("auth.requests.Session")
    def test_make_userinfo_request_timeout(self, mock_session_class):
        """Test userinfo request with timeout."""
        # Setup mock to timeout
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Request timed out")
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Call function and expect error
        with pytest.raises(APIError) as exc_info:
            make_userinfo_request("test-token")

        assert exc_info.value.status_code == 401
        assert "Failed to validate token" in str(exc_info.value)


class TestGetUserFromRequest:
    """Tests for get_user_from_request function."""

    @patch("auth.make_userinfo_request")
    def test_get_user_from_request_success(
        self, mock_make_userinfo, app, mock_userinfo
    ):
        """Test successful user extraction from request."""
        mock_make_userinfo.return_value = mock_userinfo

        with app.test_request_context(headers={"Authorization": "Bearer test-token"}):
            user_info, user_id = get_user_from_request()

            assert user_info == mock_userinfo
            assert user_id == mock_userinfo["sub"]
            mock_make_userinfo.assert_called_once_with("test-token")

    def test_get_user_from_request_no_header(self, app):
        """Test user extraction without Authorization header."""
        with app.test_request_context():
            with pytest.raises(APIError) as exc_info:
                get_user_from_request()

            assert exc_info.value.status_code == 401
            assert "Authorization required" in str(exc_info.value)

    def test_get_user_from_request_invalid_format_single_part(self, app):
        """Test user extraction with invalid token format (single part)."""
        with app.test_request_context(headers={"Authorization": "test-token"}):
            with pytest.raises(APIError) as exc_info:
                get_user_from_request()

            assert exc_info.value.status_code == 401
            assert "Invalid token format" in str(exc_info.value)

    def test_get_user_from_request_invalid_format_wrong_type(self, app):
        """Test user extraction with invalid token type."""
        with app.test_request_context(headers={"Authorization": "Basic test-token"}):
            with pytest.raises(APIError) as exc_info:
                get_user_from_request()

            assert exc_info.value.status_code == 401
            assert "Invalid token format" in str(exc_info.value)

    def test_get_user_from_request_invalid_format_too_many_parts(self, app):
        """Test user extraction with too many parts in header."""
        with app.test_request_context(
            headers={"Authorization": "Bearer test token extra"}
        ):
            with pytest.raises(APIError) as exc_info:
                get_user_from_request()

            assert exc_info.value.status_code == 401
            assert "Invalid token format" in str(exc_info.value)

    def test_get_user_from_request_case_insensitive_bearer(self, app, mock_userinfo):
        """Test that Bearer is case insensitive."""
        with patch("auth.make_userinfo_request") as mock_make_userinfo:
            mock_make_userinfo.return_value = mock_userinfo

            with app.test_request_context(
                headers={"Authorization": "bearer test-token"}
            ):
                user_info, user_id = get_user_from_request()

                assert user_info == mock_userinfo
                assert user_id == mock_userinfo["sub"]
                mock_make_userinfo.assert_called_once_with("test-token")

    @patch("auth.make_userinfo_request")
    def test_get_user_from_request_userinfo_error(self, mock_make_userinfo, app):
        """Test user extraction when userinfo request fails."""
        mock_make_userinfo.side_effect = APIError(
            "Token validation failed", status_code=401
        )

        with app.test_request_context(headers={"Authorization": "Bearer test-token"}):
            with pytest.raises(APIError) as exc_info:
                get_user_from_request()

            assert exc_info.value.status_code == 401
            assert "Token validation failed" in str(exc_info.value)
