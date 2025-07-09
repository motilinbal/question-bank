# database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from typing import Optional, Dict, Any, List
import config


class Database:
    """Handles all interactions with the MongoDB database."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "client"):
            try:
                self.client = MongoClient(
                    config.MONGO_URI, serverSelectionTimeoutMS=5000
                )
                # The ismaster command is cheap and does not require auth.
                self.client.admin.command("ismaster")
                self.db = self.client[config.DB_NAME]
                print("✅ Database connection successful.")
            except ConnectionFailure as e:
                print(f"❌ Database connection failed: {e}")
                self.client = None
                self.db = None

    def get_collection(self, collection_name: str):
        """Gets a collection from the database."""
        if self.db is not None:
            return self.db[collection_name]
        return None

    def create_document(
        self, collection_name: str, document: Dict[str, Any]
    ) -> Optional[str]:
        """Inserts a new document into a collection."""
        collection = self.get_collection(collection_name)
        if collection is not None:
            result = collection.insert_one(document)
            return str(result.inserted_id)
        return None

    def get_document_by_id(
        self, collection_name: str, document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Finds a single document by its _id."""
        collection = self.get_collection(collection_name)
        if collection is not None:
            try:
                return collection.find_one({"_id": ObjectId(document_id)})
            except Exception:
                return None
        return None

    def find_documents(
        self,
        collection_name: str,
        query: Dict[str, Any],
        projection: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """Finds multiple documents matching a query."""
        collection = self.get_collection(collection_name)
        if collection is not None:
            return list(collection.find(query, projection))
        return []

    def update_document(
        self, collection_name: str, document_id: str, updates: Dict[str, Any]
    ) -> bool:
        """Updates a document by its _id."""
        collection = self.get_collection(collection_name)
        if collection is not None:
            result = collection.update_one(
                {"_id": ObjectId(document_id)}, {"$set": updates}
            )
            return result.matched_count > 0
        return False

    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Deletes a document by its _id."""
        collection = self.get_collection(collection_name)
        if collection is not None:
            result = collection.delete_one({"_id": ObjectId(document_id)})
            return result.deleted_count > 0
        return False

    def close(self):
        """Closes the database connection."""
        if self.client:
            self.client.close()
            print("Database connection closed.")


# Singleton instance for the application to use
db_client = Database()
