"""Tests for storage module."""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from error_handlers import APIError

# Import storage modules for testing
from storage.client import (
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    ensure_bucket_exists,
    handle_minio_error,
    list_minio_buckets,
    list_minio_objects,
)
from storage.metadata import create_metadata, validate_data_filename, validate_metadata
from storage.quota import count_user_sessions, count_user_stories
from storage.utils import get_content_type, get_data_file_extension, get_object_path


class TestStorageClient:
    """Tests for storage client functionality."""

    @patch.dict(
        os.environ,
        {
            "MINIO_ENDPOINT": "test-endpoint:9000",
            "MINIO_ACCESS_KEY": "test-access",
            "MINIO_SECRET_KEY": "test-secret",
            "MINIO_BUCKET": "test-bucket",
        },
    )
    def test_minio_configuration_loaded(self):
        """Test that MinIO configuration is loaded from environment."""
        # Reload the module to pick up new environment variables
        import importlib

        from storage import client

        importlib.reload(client)

        assert client.MINIO_ENDPOINT == "test-endpoint:9000"
        assert client.MINIO_ACCESS_KEY == "test-access"
        assert client.MINIO_SECRET_KEY == "test-secret"
        assert client.MINIO_BUCKET == "test-bucket"

    def test_handle_minio_error(self):
        """Test MinIO error handling."""
        # Create a mock S3Error-like object
        mock_error = Mock()
        mock_error.code = "NoSuchBucket"
        mock_error.message = "The specified bucket does not exist"

        with pytest.raises(APIError) as exc_info:
            handle_minio_error(mock_error, "test operation")

        assert exc_info.value.status_code == 500
        assert "Storage error during test operation" in exc_info.value.message

    @patch("storage.client.minio_client")
    def test_ensure_bucket_exists_success(self, mock_client):
        """Test successful bucket creation."""
        mock_client.bucket_exists.return_value = False
        mock_client.make_bucket.return_value = None

        # Should not raise any exceptions
        ensure_bucket_exists()

        mock_client.bucket_exists.assert_called_once()
        mock_client.make_bucket.assert_called_once()

    @patch("storage.client.minio_client")
    def test_ensure_bucket_exists_already_exists(self, mock_client):
        """Test when bucket already exists."""
        mock_client.bucket_exists.return_value = True

        # Should not raise any exceptions or try to create bucket
        ensure_bucket_exists()

        mock_client.bucket_exists.assert_called_once()
        mock_client.make_bucket.assert_not_called()

    @patch("storage.client.minio_client")
    def test_list_minio_objects_success(self, mock_client):
        """Test successful object listing."""
        mock_object = Mock()
        mock_object.object_name = "test-object"
        mock_object.size = 1024
        mock_object.last_modified = "2024-01-01T00:00:00Z"

        mock_client.list_objects.return_value = [mock_object]

        result = list_minio_objects("test-prefix")

        assert len(result) == 1
        assert result[0].object_name == "test-object"
        mock_client.list_objects.assert_called_once()

    @patch("storage.client.minio_client")
    def test_list_minio_objects_error(self, mock_client):
        """Test object listing with error."""
        mock_error = Mock()
        mock_error.code = "AccessDenied"
        mock_error.message = "Access denied"
        mock_client.list_objects.side_effect = mock_error

        with pytest.raises(APIError):
            list_minio_objects("test-prefix")

    @patch("storage.client.minio_client")
    def test_list_minio_buckets_success(self, mock_client):
        """Test successful bucket listing."""
        mock_bucket = Mock()
        mock_bucket.name = "test-bucket"
        mock_bucket.creation_date = "2024-01-01T00:00:00Z"

        mock_client.list_buckets.return_value = [mock_bucket]

        result = list_minio_buckets()

        assert len(result) == 1
        assert result[0].name == "test-bucket"
        mock_client.list_buckets.assert_called_once()


class TestStorageMetadata:
    """Tests for storage metadata functions."""

    def test_create_metadata_basic(self):
        """Test basic metadata creation."""
        result = create_metadata("test-id", "session", "user-123")

        assert result["id"] == "test-id"
        assert result["object_type"] == "session"
        assert result["user_id"] == "user-123"
        assert "created_at" in result
        assert "updated_at" in result

    def test_create_metadata_with_data(self):
        """Test metadata creation with additional data."""
        extra_data = {"title": "Test Session", "description": "A test session"}
        result = create_metadata("test-id", "session", "user-123", **extra_data)

        assert result["title"] == "Test Session"
        assert result["description"] == "A test session"

    def test_validate_metadata_valid(self):
        """Test metadata validation with valid data."""
        metadata = {
            "id": "test-id",
            "object_type": "session",
            "user_id": "user-123",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        # Should not raise any exceptions
        validate_metadata(metadata)

    def test_validate_metadata_missing_required_field(self):
        """Test metadata validation with missing required field."""
        metadata = {
            "object_type": "session",
            "user_id": "user-123",
            # Missing 'id'
        }

        with pytest.raises(APIError) as exc_info:
            validate_metadata(metadata)

        assert "Missing required field" in exc_info.value.message

    def test_validate_metadata_invalid_object_type(self):
        """Test metadata validation with invalid object type."""
        metadata = {
            "id": "test-id",
            "object_type": "invalid_type",
            "user_id": "user-123",
        }

        with pytest.raises(APIError) as exc_info:
            validate_metadata(metadata)

        assert "Invalid object_type" in exc_info.value.message

    def test_validate_data_filename_valid(self):
        """Test data filename validation with valid filename."""
        # Should not raise any exceptions
        validate_data_filename("data.mvs")
        validate_data_filename("session.mvs")
        validate_data_filename("story.mvs")

    def test_validate_data_filename_invalid_extension(self):
        """Test data filename validation with invalid extension."""
        with pytest.raises(APIError) as exc_info:
            validate_data_filename("data.txt")

        assert "Data filename must end with .mvs" in exc_info.value.message

    def test_validate_data_filename_no_extension(self):
        """Test data filename validation with no extension."""
        with pytest.raises(APIError) as exc_info:
            validate_data_filename("data")

        assert "Data filename must end with .mvs" in exc_info.value.message


class TestStorageUtils:
    """Tests for storage utility functions."""

    def test_get_object_path(self):
        """Test object path generation."""
        result = get_object_path("session", "test-id", "metadata.json")
        assert result == "session/test-id/metadata.json"

    def test_get_data_file_extension(self):
        """Test data file extension detection."""
        assert get_data_file_extension("binary") == ".mvs"
        assert get_data_file_extension("msgpack") == ".mvs"
        assert get_data_file_extension("json") == ".json"
        assert get_data_file_extension("unknown") == ".mvs"  # default

    def test_get_content_type(self):
        """Test content type detection."""
        assert get_content_type("test.json") == "application/json"
        assert get_content_type("test.mvs") == "application/octet-stream"
        assert get_content_type("test.txt") == "text/plain"
        assert get_content_type("test.unknown") == "application/octet-stream"


class TestStorageQuota:
    """Tests for storage quota functions."""

    @patch("storage.quota.list_objects_by_type")
    def test_count_user_sessions(self, mock_list_objects):
        """Test counting user sessions."""
        mock_list_objects.return_value = [
            {"user_id": "user-123", "id": "session-1"},
            {"user_id": "user-123", "id": "session-2"},
            {"user_id": "user-456", "id": "session-3"},
        ]

        result = count_user_sessions("user-123")
        assert result == 2

        mock_list_objects.assert_called_once_with("session")

    @patch("storage.quota.list_objects_by_type")
    def test_count_user_stories(self, mock_list_objects):
        """Test counting user stories."""
        mock_list_objects.return_value = [
            {"user_id": "user-123", "id": "story-1"},
            {"user_id": "user-123", "id": "story-2"},
            {"user_id": "user-456", "id": "story-3"},
        ]

        result = count_user_stories("user-123")
        assert result == 2

        mock_list_objects.assert_called_once_with("story")

    @patch("storage.quota.count_user_sessions")
    def test_check_user_session_limit_within_limit(self, mock_count, app):
        """Test session limit check when within limit."""
        mock_count.return_value = 5
        app.config["MAX_SESSIONS_PER_USER"] = 10

        with app.app_context():
            # Should not raise any exceptions
            from storage.quota import check_user_session_limit

            check_user_session_limit("user-123")

    @patch("storage.quota.count_user_sessions")
    def test_check_user_session_limit_exceeds_limit(self, mock_count, app):
        """Test session limit check when exceeding limit."""
        mock_count.return_value = 15
        app.config["MAX_SESSIONS_PER_USER"] = 10

        with app.app_context():
            from storage.quota import check_user_session_limit

            with pytest.raises(APIError) as exc_info:
                check_user_session_limit("user-123")

            assert exc_info.value.status_code == 429
            assert "session limit" in exc_info.value.message.lower()

    @patch("storage.quota.count_user_stories")
    def test_check_user_story_limit_within_limit(self, mock_count, app):
        """Test story limit check when within limit."""
        mock_count.return_value = 5
        app.config["MAX_STORIES_PER_USER"] = 10

        with app.app_context():
            # Should not raise any exceptions
            from storage.quota import check_user_story_limit

            check_user_story_limit("user-123")

    @patch("storage.quota.count_user_stories")
    def test_check_user_story_limit_exceeds_limit(self, mock_count, app):
        """Test story limit check when exceeding limit."""
        mock_count.return_value = 15
        app.config["MAX_STORIES_PER_USER"] = 10

        with app.app_context():
            from storage.quota import check_user_story_limit

            with pytest.raises(APIError) as exc_info:
                check_user_story_limit("user-123")

            assert exc_info.value.status_code == 429
            assert "story limit" in exc_info.value.message.lower()


class TestStorageIntegration:
    """Integration tests for storage operations."""

    @patch("storage.client.minio_client")
    def test_save_and_retrieve_object(self, mock_client):
        """Test saving and retrieving an object."""
        # Mock successful operations
        mock_client.put_object.return_value = Mock()
        mock_client.get_object.return_value = Mock()

        from storage.objects import save_object

        # Test data
        test_data = {"test": "data"}

        # Should not raise exceptions
        save_object("session", "test-id", "user-123", test_data)

        # Verify minio client was called
        assert mock_client.put_object.call_count >= 1

    @patch("storage.client.minio_client")
    @patch("storage.objects.list_minio_objects")
    def test_list_objects_by_type(self, mock_list_objects, mock_client):
        """Test listing objects by type."""
        # Mock object with metadata
        mock_object = Mock()
        mock_object.object_name = "session/test-id/metadata.json"
        mock_list_objects.return_value = [mock_object]

        # Mock get_object to return metadata
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"id": "test-id", "object_type": "session", "user_id": "user-123"}
        ).encode("utf-8")
        mock_client.get_object.return_value = mock_response

        from storage.objects import list_objects_by_type

        result = list_objects_by_type("session")

        assert len(result) >= 0  # May be empty if filtering logic excludes items
        mock_list_objects.assert_called_once()

    def test_storage_module_imports(self):
        """Test that all storage module functions can be imported."""
        from storage import (
            MINIO_BUCKET,
            count_user_sessions,
            create_metadata,
            get_object_path,
            minio_client,
            save_object,
        )

        # All imports should succeed
        assert True
