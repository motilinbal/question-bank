import pytest
from unittest.mock import MagicMock
from bson import ObjectId


@pytest.fixture
def mock_mongo_client(mocker):
    """Mock the MongoClient to avoid actual database connections."""
    return mocker.patch("database.MongoClient")


def test_database_singleton():
    """Tests that Database class implements singleton pattern."""
    from database import Database

    # Create two instances
    db1 = Database()
    db2 = Database()

    # They should be the same object
    assert db1 is db2


def test_get_collection(mock_mongo_client):
    """Tests that get_collection returns the correct collection."""
    from database import Database

    # Arrange
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    mock_mongo_client.return_value = mock_client

    # Act
    db = Database()
    db.db = mock_db
    result = db.get_collection("test_collection")

    # Assert
    assert result == mock_collection
    mock_db.__getitem__.assert_called_once_with("test_collection")


def test_create_document(mock_mongo_client):
    """Tests document creation functionality."""
    from database import Database

    # Arrange
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_result = MagicMock()
    mock_result.inserted_id = ObjectId()

    mock_collection.insert_one.return_value = mock_result
    mock_db.__getitem__.return_value = mock_collection
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    # Act
    db = Database()
    db.db = mock_db
    test_doc = {"test": "data"}
    result = db.create_document("test_collection", test_doc)

    # Assert
    assert result == str(mock_result.inserted_id)
    mock_collection.insert_one.assert_called_once_with(test_doc)


def test_find_documents_with_projection(mock_mongo_client):
    """Tests find_documents with projection parameter."""
    from database import Database

    # Arrange
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.find.return_value = [{"_id": ObjectId(), "field1": "value1"}]

    mock_db.__getitem__.return_value = mock_collection
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    # Act
    db = Database()
    db.db = mock_db
    query = {"test": "query"}
    projection = {"field1": 1, "_id": 1}
    result = db.find_documents("test_collection", query, projection)

    # Assert
    mock_collection.find.assert_called_once_with(query, projection)
    assert len(result) == 1
