"""Tests for API route handlers."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import responses
from error_handlers import APIError


class TestSessionRoutes:
    """Tests for session route handlers."""

    @patch("routes.session_routes.get_user_from_request")
    @patch("routes.session_routes.check_user_session_limit")
    @patch("routes.session_routes.save_object")
    def test_create_session_success(
        self, mock_save, mock_check_limit, mock_get_user, client, mock_userinfo
    ):
        """Test successful session creation."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_check_limit.return_value = None
        mock_save.return_value = "session-123"

        session_data = {
            "title": "Test Session",
            "description": "A test session",
            "data": {"test": "data"},
        }

        response = client.post(
            "/api/session",
            json=session_data,
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Session created successfully"
        assert "session_id" in data

    @patch("routes.session_routes.get_user_from_request")
    def test_create_session_no_data(self, mock_get_user, client, mock_userinfo):
        """Test session creation without data."""
        mock_get_user.return_value = (mock_userinfo, "user-123")

        response = client.post(
            "/api/session", headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "No data provided" in data["message"]

    @patch("routes.session_routes.get_user_from_request")
    def test_create_session_validation_error(
        self, mock_get_user, client, mock_userinfo
    ):
        """Test session creation with validation error."""
        mock_get_user.return_value = (mock_userinfo, "user-123")

        # Invalid session data (missing required fields)
        session_data = {"invalid_field": "value"}

        response = client.post(
            "/api/session",
            json=session_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 400

    @patch("routes.session_routes.get_user_from_request")
    @patch("routes.session_routes.list_objects_by_type")
    def test_list_user_sessions(
        self, mock_list_objects, mock_get_user, client, mock_userinfo
    ):
        """Test listing user sessions."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_list_objects.return_value = [
            {"id": "session-1", "title": "Session 1", "user_id": "user-123"},
            {"id": "session-2", "title": "Session 2", "user_id": "user-123"},
        ]

        response = client.get(
            "/api/sessions", headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["sessions"]) == 2

    @patch("routes.session_routes.get_user_from_request")
    @patch("routes.session_routes.find_object_by_id")
    def test_get_session_by_id(
        self, mock_find_object, mock_get_user, client, mock_userinfo
    ):
        """Test getting session by ID."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_find_object.return_value = {
            "id": "session-123",
            "title": "Test Session",
            "user_id": "user-123",
        }

        response = client.get(
            "/api/session/session-123", headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == "session-123"

    @patch("routes.session_routes.get_user_from_request")
    @patch("routes.session_routes.delete_session_by_id")
    def test_delete_session(self, mock_delete, mock_get_user, client, mock_userinfo):
        """Test deleting a session."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_delete.return_value = None

        response = client.delete(
            "/api/session/session-123", headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "deleted successfully" in data["message"]

    @patch("routes.session_routes.get_user_from_request")
    @patch("routes.session_routes.update_session_by_id")
    def test_update_session(self, mock_update, mock_get_user, client, mock_userinfo):
        """Test updating a session."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_update.return_value = None

        update_data = {"title": "Updated Session Title"}

        response = client.put(
            "/api/session/session-123",
            json=update_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "updated successfully" in data["message"]


class TestStoryRoutes:
    """Tests for story route handlers."""

    @patch("routes.story_routes.get_user_from_request")
    @patch("routes.story_routes.check_user_story_limit")
    @patch("routes.story_routes.save_object")
    def test_create_story_success(
        self, mock_save, mock_check_limit, mock_get_user, client, mock_userinfo
    ):
        """Test successful story creation."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_check_limit.return_value = None
        mock_save.return_value = "story-123"

        story_data = {
            "title": "Test Story",
            "description": "A test story",
            "scenes": [{"title": "Scene 1", "data": {}}],
        }

        response = client.post(
            "/api/story",
            json=story_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Story created successfully"

    @patch("routes.story_routes._get_story_by_id")
    def test_get_public_story_data(self, mock_get_story, client):
        """Test getting public story data without authentication."""
        mock_get_story.return_value = {
            "id": "story-123",
            "title": "Public Story",
            "is_published": True,
            "data": {"test": "data"},
        }

        response = client.get("/api/story/story-123/data")

        assert response.status_code == 200

    @patch("routes.story_routes.get_user_from_request")
    @patch("routes.story_routes.list_objects_by_type")
    def test_list_user_stories(
        self, mock_list_objects, mock_get_user, client, mock_userinfo
    ):
        """Test listing user stories."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_list_objects.return_value = [
            {"id": "story-1", "title": "Story 1", "user_id": "user-123"}
        ]

        response = client.get(
            "/api/stories", headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["stories"]) == 1

    @patch("routes.story_routes.get_user_from_request")
    @patch("routes.story_routes.update_story_by_id")
    def test_publish_story(self, mock_update, mock_get_user, client, mock_userinfo):
        """Test publishing a story."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_update.return_value = None

        response = client.post(
            "/api/story/story-123/publish",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "published successfully" in data["message"]

    @patch("routes.story_routes.get_user_from_request")
    @patch("routes.story_routes.update_story_by_id")
    def test_unpublish_story(self, mock_update, mock_get_user, client, mock_userinfo):
        """Test unpublishing a story."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_update.return_value = None

        response = client.post(
            "/api/story/story-123/unpublish",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "unpublished successfully" in data["message"]

    def test_generate_public_uri(self, app):
        """Test public URI generation."""
        with app.app_context():
            from routes.story_routes import generate_public_uri

            uri = generate_public_uri("story", "story-123")
            assert "story-123" in uri
            assert "/api/story/" in uri


class TestAdminRoutes:
    """Tests for admin route handlers."""

    @patch("routes.admin_routes.get_user_from_request")
    @patch("routes.admin_routes.extract_user_ids_from_objects")
    @patch("routes.admin_routes.list_objects_by_type")
    def test_get_user_stats(
        self,
        mock_list_objects,
        mock_extract_users,
        mock_get_user,
        client,
        mock_userinfo,
    ):
        """Test getting user statistics."""
        mock_get_user.return_value = (mock_userinfo, "admin-user")
        mock_list_objects.side_effect = [
            [{"user_id": "user-1"}, {"user_id": "user-2"}],  # sessions
            [{"user_id": "user-1"}],  # stories
        ]
        mock_extract_users.return_value = ["user-1", "user-2"]

        response = client.get(
            "/api/admin/user-stats", headers={"Authorization": "Bearer admin-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "total_users" in data
        assert "total_sessions" in data
        assert "total_stories" in data

    @patch("routes.admin_routes.get_user_from_request")
    @patch("routes.admin_routes.delete_all_user_data")
    def test_delete_user_data(self, mock_delete, mock_get_user, client, mock_userinfo):
        """Test deleting user data."""
        mock_get_user.return_value = (mock_userinfo, "admin-user")
        mock_delete.return_value = {"deleted_sessions": 2, "deleted_stories": 1}

        response = client.delete(
            "/api/admin/user/user-123", headers={"Authorization": "Bearer admin-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "deleted successfully" in data["message"]


class TestRouteAuthentication:
    """Tests for route authentication."""

    def test_session_route_requires_auth(self, client):
        """Test that session routes require authentication."""
        response = client.get("/api/sessions")
        assert response.status_code == 401

    def test_story_route_requires_auth_for_private_operations(self, client):
        """Test that private story operations require authentication."""
        response = client.get("/api/stories")
        assert response.status_code == 401

    def test_admin_route_requires_auth(self, client):
        """Test that admin routes require authentication."""
        response = client.get("/api/admin/user-stats")
        assert response.status_code == 401

    @responses.activate
    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected."""
        # Mock OIDC userinfo endpoint to return 401
        responses.add(
            responses.GET,
            "http://test-oidc/userinfo",
            json={"error": "invalid_token"},
            status=401,
        )

        response = client.get(
            "/api/sessions", headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401


class TestRouteValidation:
    """Tests for route input validation."""

    @patch("routes.session_routes.get_user_from_request")
    def test_session_creation_with_large_payload(
        self, mock_get_user, client, mock_userinfo
    ):
        """Test session creation with large payload is rejected."""
        mock_get_user.return_value = (mock_userinfo, "user-123")

        # Create a large payload
        large_data = {"data": "x" * (60 * 1024 * 1024)}  # 60MB

        response = client.post(
            "/api/session",
            json=large_data,
            headers={
                "Authorization": "Bearer test-token",
                "Content-Length": str(len(json.dumps(large_data))),
            },
        )

        assert response.status_code == 413

    @patch("routes.story_routes.get_user_from_request")
    def test_story_creation_with_invalid_json(
        self, mock_get_user, client, mock_userinfo
    ):
        """Test story creation with invalid JSON."""
        mock_get_user.return_value = (mock_userinfo, "user-123")

        response = client.post(
            "/api/story",
            data="invalid json",
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 400


class TestRouteErrorHandling:
    """Tests for route error handling."""

    @patch("routes.session_routes.get_user_from_request")
    @patch("routes.session_routes.save_object")
    def test_session_creation_storage_error(
        self, mock_save, mock_get_user, client, mock_userinfo
    ):
        """Test session creation with storage error."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_save.side_effect = APIError("Storage error", status_code=500)

        session_data = {"title": "Test Session", "data": {"test": "data"}}

        response = client.post(
            "/api/session",
            json=session_data,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "Storage error" in data["message"]

    @patch("routes.story_routes.get_user_from_request")
    @patch("routes.story_routes.list_objects_by_type")
    def test_story_list_storage_error(
        self, mock_list_objects, mock_get_user, client, mock_userinfo
    ):
        """Test story listing with storage error."""
        mock_get_user.return_value = (mock_userinfo, "user-123")
        mock_list_objects.side_effect = APIError("Storage unavailable", status_code=503)

        response = client.get(
            "/api/stories", headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 503
        data = response.get_json()
        assert "Storage unavailable" in data["message"]


class TestRouteContentTypes:
    """Tests for route content type handling."""

    @patch("routes.session_routes.get_user_from_request")
    def test_session_creation_requires_json(self, mock_get_user, client, mock_userinfo):
        """Test that session creation requires JSON content type."""
        mock_get_user.return_value = (mock_userinfo, "user-123")

        response = client.post(
            "/api/session",
            data="test data",
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "text/plain",
            },
        )

        assert response.status_code == 400

    def test_public_story_data_returns_correct_content_type(self, client):
        """Test that public story data returns correct content type."""
        with patch("routes.story_routes._get_story_by_id") as mock_get_story:
            mock_get_story.return_value = {
                "id": "story-123",
                "is_published": True,
                "data": b"binary data",
            }

            response = client.get("/api/story/story-123/data")

            # Should return appropriate content type for binary data
            assert response.status_code == 200
