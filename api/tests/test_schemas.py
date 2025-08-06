"""Tests for schema validation."""

import pytest
from pydantic import ValidationError
from schemas import (
    BaseItemUpdate,
    SessionInput,
    SessionUpdate,
    StoryInput,
    base_metadata_schema,
    creator_schema,
)


class TestSessionInput:
    """Tests for SessionInput schema validation."""

    def test_session_input_valid_minimal(self):
        """Test SessionInput with minimal valid data."""
        data = {
            "title": "Test Session",
            "description": "A test session",
            "data": {"test": "data"},
        }

        session = SessionInput(**data)
        assert session.title == "Test Session"
        assert session.description == "A test session"
        assert session.data == {"test": "data"}

    def test_session_input_valid_full(self):
        """Test SessionInput with all fields."""
        data = {
            "title": "Full Test Session",
            "description": "A complete test session",
            "tags": ["test", "demo"],
            "data": {"camera": {"position": [0, 0, 10]}},
            "format": "json",
            "version": "1.0",
        }

        session = SessionInput(**data)
        assert session.title == "Full Test Session"
        assert session.tags == ["test", "demo"]
        assert session.format == "json"
        assert session.version == "1.0"

    def test_session_input_missing_required_field(self):
        """Test SessionInput validation with missing required field."""
        data = {"description": "Missing title", "data": {"test": "data"}}

        with pytest.raises(ValidationError) as exc_info:
            SessionInput(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("title",) for error in errors)

    def test_session_input_invalid_data_type(self):
        """Test SessionInput validation with invalid data type."""
        data = {
            "title": "Test Session",
            "description": "A test session",
            "data": "invalid data type",  # Should be dict
        }

        with pytest.raises(ValidationError) as exc_info:
            SessionInput(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("data",) for error in errors)

    def test_session_input_invalid_tags_type(self):
        """Test SessionInput validation with invalid tags type."""
        data = {
            "title": "Test Session",
            "description": "A test session",
            "data": {"test": "data"},
            "tags": "should be a list",
        }

        with pytest.raises(ValidationError) as exc_info:
            SessionInput(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("tags",) for error in errors)

    def test_session_input_default_values(self):
        """Test SessionInput default values."""
        data = {
            "title": "Test Session",
            "description": "A test session",
            "data": {"test": "data"},
        }

        session = SessionInput(**data)
        assert session.tags == []
        assert session.format == "binary"
        assert session.version == "1.0"


class TestSessionUpdate:
    """Tests for SessionUpdate schema validation."""

    def test_session_update_valid(self):
        """Test SessionUpdate with valid data."""
        data = {
            "title": "Updated Session",
            "description": "Updated description",
            "tags": ["updated"],
        }

        session_update = SessionUpdate(**data)
        assert session_update.title == "Updated Session"
        assert session_update.description == "Updated description"
        assert session_update.tags == ["updated"]

    def test_session_update_empty(self):
        """Test SessionUpdate with no fields (all optional)."""
        session_update = SessionUpdate()
        assert session_update.title is None
        assert session_update.description is None
        assert session_update.tags is None

    def test_session_update_partial(self):
        """Test SessionUpdate with partial data."""
        data = {"title": "New Title Only"}

        session_update = SessionUpdate(**data)
        assert session_update.title == "New Title Only"
        assert session_update.description is None


class TestStoryInput:
    """Tests for StoryInput schema validation."""

    def test_story_input_valid_minimal(self):
        """Test StoryInput with minimal valid data."""
        data = {
            "title": "Test Story",
            "description": "A test story",
            "scenes": [
                {
                    "title": "Scene 1",
                    "description": "First scene",
                    "data": {"test": "data"},
                }
            ],
        }

        story = StoryInput(**data)
        assert story.title == "Test Story"
        assert len(story.scenes) == 1
        assert story.scenes[0]["title"] == "Scene 1"

    def test_story_input_valid_full(self):
        """Test StoryInput with all fields."""
        data = {
            "title": "Full Test Story",
            "description": "A complete test story",
            "tags": ["story", "test"],
            "scenes": [
                {
                    "title": "Scene 1",
                    "description": "First scene",
                    "data": {"camera": {"position": [0, 0, 10]}},
                },
                {
                    "title": "Scene 2",
                    "description": "Second scene",
                    "data": {"camera": {"position": [5, 5, 15]}},
                },
            ],
            "format": "json",
            "version": "2.0",
        }

        story = StoryInput(**data)
        assert story.title == "Full Test Story"
        assert len(story.scenes) == 2
        assert story.format == "json"
        assert story.version == "2.0"

    def test_story_input_missing_required_field(self):
        """Test StoryInput validation with missing required field."""
        data = {
            "description": "Missing title",
            "scenes": [{"title": "Scene 1", "description": "Test", "data": {}}],
        }

        with pytest.raises(ValidationError) as exc_info:
            StoryInput(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("title",) for error in errors)

    def test_story_input_empty_scenes(self):
        """Test StoryInput validation with empty scenes."""
        data = {"title": "Test Story", "description": "A test story", "scenes": []}

        with pytest.raises(ValidationError) as exc_info:
            StoryInput(**data)

        # Should fail validation due to empty scenes list
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("scenes",) for error in errors)

    def test_story_input_invalid_scene_structure(self):
        """Test StoryInput validation with invalid scene structure."""
        data = {
            "title": "Test Story",
            "description": "A test story",
            "scenes": [
                {
                    "title": "Scene 1",
                    # Missing description and data
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            StoryInput(**data)

        errors = exc_info.value.errors()
        # Should have errors for missing scene fields
        assert len(errors) > 0

    def test_story_input_default_values(self):
        """Test StoryInput default values."""
        data = {
            "title": "Test Story",
            "description": "A test story",
            "scenes": [
                {
                    "title": "Scene 1",
                    "description": "Test scene",
                    "data": {"test": "data"},
                }
            ],
        }

        story = StoryInput(**data)
        assert story.tags == []
        assert story.format == "binary"
        assert story.version == "1.0"


class TestBaseItemUpdate:
    """Tests for BaseItemUpdate schema validation."""

    def test_base_item_update_valid(self):
        """Test BaseItemUpdate with valid data."""
        data = {
            "title": "Updated Item",
            "description": "Updated description",
            "tags": ["new", "tags"],
        }

        update = BaseItemUpdate(**data)
        assert update.title == "Updated Item"
        assert update.description == "Updated description"
        assert update.tags == ["new", "tags"]

    def test_base_item_update_empty(self):
        """Test BaseItemUpdate with no fields."""
        update = BaseItemUpdate()
        assert update.title is None
        assert update.description is None
        assert update.tags is None

    def test_base_item_update_partial(self):
        """Test BaseItemUpdate with partial data."""
        data = {"description": "Only description updated"}

        update = BaseItemUpdate(**data)
        assert update.title is None
        assert update.description == "Only description updated"
        assert update.tags is None

    def test_base_item_update_invalid_tags(self):
        """Test BaseItemUpdate validation with invalid tags."""
        data = {"tags": "should be a list"}

        with pytest.raises(ValidationError) as exc_info:
            BaseItemUpdate(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("tags",) for error in errors)


class TestSchemaIntegration:
    """Integration tests for schema functionality."""

    def test_session_input_to_dict(self):
        """Test converting SessionInput to dictionary."""
        data = {
            "title": "Test Session",
            "description": "A test session",
            "data": {"test": "data"},
            "tags": ["test"],
        }

        session = SessionInput(**data)
        session_dict = session.dict()

        assert session_dict["title"] == "Test Session"
        assert session_dict["tags"] == ["test"]
        assert "data" in session_dict

    def test_story_input_to_dict(self):
        """Test converting StoryInput to dictionary."""
        data = {
            "title": "Test Story",
            "description": "A test story",
            "scenes": [
                {
                    "title": "Scene 1",
                    "description": "Test scene",
                    "data": {"camera": {"position": [0, 0, 10]}},
                }
            ],
            "tags": ["story", "test"],
        }

        story = StoryInput(**data)
        story_dict = story.dict()

        assert story_dict["title"] == "Test Story"
        assert len(story_dict["scenes"]) == 1
        assert story_dict["scenes"][0]["title"] == "Scene 1"

    def test_schema_validation_preserves_data_types(self):
        """Test that schema validation preserves correct data types."""
        data = {
            "title": "Test Session",
            "description": "A test session",
            "data": {
                "number": 42,
                "boolean": True,
                "list": [1, 2, 3],
                "nested": {"key": "value"},
            },
        }

        session = SessionInput(**data)

        assert isinstance(session.data["number"], int)
        assert isinstance(session.data["boolean"], bool)
        assert isinstance(session.data["list"], list)
        assert isinstance(session.data["nested"], dict)

    def test_update_schema_excludes_none_values(self):
        """Test that update schemas properly exclude None values."""
        data = {
            "title": "New Title",
            "description": None,  # Should be excluded when converted
            "tags": ["test"],
        }

        update = BaseItemUpdate(**data)
        update_dict = update.dict(exclude_none=True)

        assert "title" in update_dict
        assert "description" not in update_dict
        assert "tags" in update_dict


class TestSchemaConstants:
    """Tests for schema constants and definitions."""

    def test_creator_schema_structure(self):
        """Test creator schema structure."""
        assert "type" in creator_schema
        assert creator_schema["type"] == "object"
        assert "required" in creator_schema
        assert "id" in creator_schema["required"]
        assert "name" in creator_schema["required"]
        assert "email" in creator_schema["required"]

    def test_base_metadata_schema_structure(self):
        """Test base metadata schema structure."""
        assert "type" in base_metadata_schema
        assert base_metadata_schema["type"] == "object"
        assert "required" in base_metadata_schema
        assert "id" in base_metadata_schema["required"]
        assert "type" in base_metadata_schema["required"]
        assert "creator" in base_metadata_schema["required"]

    def test_schema_property_types(self):
        """Test that schema properties have correct types."""
        props = base_metadata_schema["properties"]

        assert props["id"]["format"] == "uuid"
        assert props["type"]["enum"] == ["session", "story"]
        assert props["created_at"]["format"] == "date-time"
        assert props["updated_at"]["format"] == "date-time"
        assert props["tags"]["type"] == "array"
