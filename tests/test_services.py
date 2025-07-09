import pytest
from unittest.mock import MagicMock
from models import Question, MediaItem


# Mock the database client before it's imported by services
@pytest.fixture(autouse=True)
def mock_db_client(mocker):
    return mocker.patch("services.db_client", MagicMock())


# Now import the services
from services import QuestionService


@pytest.fixture
def question_service():
    return QuestionService()


def test_render_question_html_image(question_service):
    """Tests that an image placeholder is correctly replaced."""
    # Arrange
    mock_question = Question(
        question_id="q1",
        text="Here is an image: %%IMG_1%%",
        source="test",
        media_placeholders=[{"placeholder": "%%IMG_1%%", "media_id": "m1"}],
    )
    mock_media_item = MediaItem(
        media_id="m1", type="image", path="images/test.jpg", description="A test image"
    )
    question_service.get_media_item_by_id = MagicMock(return_value=mock_media_item)

    # Act
    html = question_service.render_question_html(mock_question)

    # Assert
    assert "<img src='images/test.jpg'" in html
    assert "alt='A test image'" in html


def test_render_question_html_page(question_service):
    """Tests that a page placeholder is correctly replaced."""
    # Arrange
    mock_question = Question(
        question_id="q2",
        text="Here is a page: %%PAGE_1%%",
        source="test",
        media_placeholders=[{"placeholder": "%%PAGE_1%%", "media_id": "m2"}],
    )
    mock_media_item = MediaItem(
        media_id="m2", type="page", content="<h1>Test Page</h1>"
    )
    question_service.get_media_item_by_id = MagicMock(return_value=mock_media_item)

    # Act
    html = question_service.render_question_html(mock_question)

    # Assert
    assert "<div class='media-page'" in html
    assert "<h1>Test Page</h1>" in html


def test_toggle_favorite(question_service):
    """Tests the favorite toggling logic."""
    # Arrange
    test_id = "q_fav"
    mock_question = Question(
        question_id=test_id, text="", source="test", is_favorite=False
    )
    question_service.get_question_by_id = MagicMock(return_value=mock_question)
    question_service._update_question_field = MagicMock(return_value=True)

    # Act
    question_service.toggle_favorite(test_id)

    # Assert
    # Verify that the update method was called with the correct arguments
    question_service._update_question_field.assert_called_once_with(
        test_id, "is_favorite", True
    )


def test_toggle_marked(question_service):
    """Tests the marked toggling logic."""
    # Arrange
    test_id = "q_mark"
    mock_question = Question(
        question_id=test_id, text="", source="test", is_marked=False
    )
    question_service.get_question_by_id = MagicMock(return_value=mock_question)
    question_service._update_question_field = MagicMock(return_value=True)

    # Act
    question_service.toggle_marked(test_id)

    # Assert
    question_service._update_question_field.assert_called_once_with(
        test_id, "is_marked", True
    )


def test_update_notes(question_service):
    """Tests the notes update functionality."""
    # Arrange
    test_id = "q_notes"
    test_notes = "These are test notes"
    question_service._update_question_field = MagicMock(return_value=True)

    # Act
    result = question_service.update_notes(test_id, test_notes)

    # Assert
    assert result is True
    question_service._update_question_field.assert_called_once_with(
        test_id, "notes", test_notes
    )
