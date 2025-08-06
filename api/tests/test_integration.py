"""Integration tests for the entire API."""

import json
from unittest.mock import Mock, patch

import pytest
import responses


class TestAPIIntegration:
    """End-to-end integration tests."""

    @responses.activate
    @patch("storage.client.minio_client")
    def test_full_session_workflow(self, mock_minio, client):
        """Test complete session workflow: create, list, update, delete."""
        # Mock OIDC userinfo endpoint
        responses.add(
            responses.GET,
            "http://test-oidc/userinfo",
            json={
                "sub": "test-user-123",
                "name": "Test User",
                "email": "test@example.com",
            },
            status=200,
        )

        # Mock MinIO operations
        mock_minio.put_object.return_value = Mock()
        mock_minio.get_object.return_value = Mock()
        mock_minio.list_objects.return_value = []
        mock_minio.remove_object.return_value = Mock()

        auth_headers = {"Authorization": "Bearer valid-token"}

        # 1. Create session
        session_data = {
            "title": "Integration Test Session",
            "description": "A session for integration testing",
            "data": {"camera": {"position": [0, 0, 10]}},
            "tags": ["integration", "test"],
        }

        with patch("routes.session_routes.save_object") as mock_save:
            mock_save.return_value = "session-123"

            response = client.post(
                "/api/session", json=session_data, headers=auth_headers
            )

            assert response.status_code == 201
            create_data = response.get_json()
            assert "session_id" in create_data

        # 2. List sessions
        with patch("routes.session_routes.list_objects_by_type") as mock_list:
            mock_list.return_value = [
                {
                    "id": "session-123",
                    "title": "Integration Test Session",
                    "user_id": "test-user-123",
                }
            ]

            response = client.get("/api/sessions", headers=auth_headers)

            assert response.status_code == 200
            list_data = response.get_json()
            assert len(list_data["sessions"]) == 1

        # 3. Update session
        update_data = {"title": "Updated Integration Test Session"}

        with patch("routes.session_routes.update_session_by_id") as mock_update:
            mock_update.return_value = None

            response = client.put(
                "/api/session/session-123", json=update_data, headers=auth_headers
            )

            assert response.status_code == 200

        # 4. Delete session
        with patch("routes.session_routes.delete_session_by_id") as mock_delete:
            mock_delete.return_value = None

            response = client.delete("/api/session/session-123", headers=auth_headers)

            assert response.status_code == 200

    @responses.activate
    @patch("storage.client.minio_client")
    def test_full_story_workflow(self, mock_minio, client):
        """Test complete story workflow: create, publish, get public data."""
        # Mock OIDC userinfo endpoint
        responses.add(
            responses.GET,
            "http://test-oidc/userinfo",
            json={
                "sub": "story-user-456",
                "name": "Story User",
                "email": "story@example.com",
            },
            status=200,
        )

        # Mock MinIO operations
        mock_minio.put_object.return_value = Mock()
        mock_minio.get_object.return_value = Mock()
        mock_minio.list_objects.return_value = []

        auth_headers = {"Authorization": "Bearer valid-token"}

        # 1. Create story
        story_data = {
            "title": "Integration Test Story",
            "description": "A story for integration testing",
            "scenes": [
                {
                    "title": "Opening Scene",
                    "description": "The first scene",
                    "data": {"camera": {"position": [0, 0, 10]}},
                },
                {
                    "title": "Closing Scene",
                    "description": "The final scene",
                    "data": {"camera": {"position": [10, 10, 20]}},
                },
            ],
            "tags": ["integration", "story", "test"],
        }

        with patch("routes.story_routes.save_object") as mock_save:
            mock_save.return_value = "story-456"

            response = client.post("/api/story", json=story_data, headers=auth_headers)

            assert response.status_code == 201
            create_data = response.get_json()
            assert "story_id" in create_data

        # 2. Publish story
        with patch("routes.story_routes.update_story_by_id") as mock_update:
            mock_update.return_value = None

            response = client.post("/api/story/story-456/publish", headers=auth_headers)

            assert response.status_code == 200

        # 3. Get public story data (no auth required)
        with patch("routes.story_routes._get_story_by_id") as mock_get_story:
            mock_get_story.return_value = {
                "id": "story-456",
                "title": "Integration Test Story",
                "is_published": True,
                "data": b"story data",
            }

            response = client.get("/api/story/story-456/data")

            assert response.status_code == 200

    def test_error_handling_integration(self, client):
        """Test error handling across the API."""
        # Test 401 unauthorized
        response = client.get("/api/sessions")
        assert response.status_code == 401

        # Test 400 bad request
        response = client.post(
            "/api/session",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

        # Test 413 payload too large
        large_payload = {"data": "x" * (60 * 1024 * 1024)}  # 60MB
        response = client.post(
            "/api/session",
            json=large_payload,
            headers={"Content-Length": str(len(json.dumps(large_payload)))},
        )
        assert response.status_code == 413

    def test_health_check_integration(self, client):
        """Test health check endpoint integration."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert "message" in data

    @responses.activate
    def test_authentication_integration(self, client):
        """Test authentication integration with OIDC."""
        # Test valid token
        responses.add(
            responses.GET,
            "http://test-oidc/userinfo",
            json={
                "sub": "auth-test-user",
                "name": "Auth Test User",
                "email": "auth@example.com",
            },
            status=200,
        )

        with patch("routes.session_routes.list_objects_by_type") as mock_list:
            mock_list.return_value = []

            response = client.get(
                "/api/sessions", headers={"Authorization": "Bearer valid-token"}
            )

            assert response.status_code == 200

        # Test invalid token
        responses.reset()
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

    @patch("storage.client.minio_client")
    def test_storage_integration(self, mock_minio, app):
        """Test storage integration."""
        # Test that storage operations work with mocked MinIO
        mock_minio.bucket_exists.return_value = True
        mock_minio.put_object.return_value = Mock()
        mock_minio.get_object.return_value = Mock()

        with app.app_context():
            from storage import list_objects_by_type, save_object

            # These should not raise exceptions
            try:
                save_object("session", "test-id", "user-123", {"test": "data"})
                list_objects_by_type("session")
            except Exception as e:
                # If we get an exception, it should be an APIError, not a connection error
                from error_handlers import APIError

                assert isinstance(e, APIError)

    def test_content_type_integration(self, client):
        """Test content type handling integration."""
        # Test JSON content type
        response = client.post(
            "/api/session",
            json={"test": "data"},
            headers={"Content-Type": "application/json"},
        )

        # Should fail with auth error, not content type error
        assert response.status_code == 401

        # Test incorrect content type
        response = client.post(
            "/api/session", data="test data", headers={"Content-Type": "text/plain"}
        )

        # Should fail with bad request or auth error
        assert response.status_code in [400, 401]

    def test_cors_integration(self, client):
        """Test CORS integration."""
        # Test CORS preflight request
        response = client.options(
            "/api/session",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers


class TestAPIPerformance:
    """Performance-related integration tests."""

    def test_request_size_limits(self, client):
        """Test that request size limits are enforced."""
        # Test request that's too large
        large_data = {"data": "x" * (60 * 1024 * 1024)}  # 60MB

        response = client.post(
            "/api/session",
            json=large_data,
            headers={"Content-Length": str(len(json.dumps(large_data)))},
        )

        assert response.status_code == 413

        # Test request without Content-Length header
        response = client.post("/api/session", json={"test": "data"})

        # Should either succeed (if auth is mocked) or fail with auth error
        # The key is that it shouldn't fail due to missing Content-Length
        assert response.status_code in [200, 201, 400, 401]

    @patch("storage.client.minio_client")
    def test_concurrent_request_handling(self, mock_minio, client):
        """Test handling of concurrent requests."""
        mock_minio.put_object.return_value = Mock()

        # This is a basic test - in a real scenario you'd use threading
        # to test actual concurrency
        responses_list = []

        for i in range(5):
            response = client.get("/ready")
            responses_list.append(response.status_code)

        # All health checks should succeed
        assert all(status == 200 for status in responses_list)


class TestAPIDocumentation:
    """Tests related to API documentation and discoverability."""

    def test_api_endpoints_discoverable(self, client):
        """Test that main API endpoints are discoverable."""
        # Test that main endpoints return appropriate responses
        endpoints = ["/ready", "/api/sessions", "/api/stories"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should return either success or auth required, not 404
            assert response.status_code != 404

    def test_error_responses_consistent(self, client):
        """Test that error responses have consistent format."""
        # Test various error conditions
        responses_to_test = [
            client.get("/api/sessions"),  # 401 unauthorized
            client.post("/api/session", data="invalid"),  # 400 bad request
        ]

        for response in responses_to_test:
            if response.status_code >= 400:
                data = response.get_json()
                assert "error" in data
                assert "message" in data
                assert "status_code" in data
                assert data["error"] is True
                assert data["status_code"] == response.status_code
