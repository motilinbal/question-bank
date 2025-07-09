# DocuMedica Refactoring: Phase 1 Implementation Plan

## **Objective: Setup and Foundation**

The goal of Phase 1 is to establish the core technical foundation of the new DocuMedica application. This includes setting up the project environment, defining the directory structure, implementing the data models, and creating a robust data access layer for interacting with MongoDB.

---

### **Task 1.2: Directory and File Structure**

* **Goal**: Establish the logical folder and file structure for the application code.
* **Steps**:
    1.  **Create Asset Directories**: From the project root, create the necessary folders for media assets.
        ```bash
        mkdir -p assets/images assets/videos assets/audio
        ```
    2.  **Create Core Python Files**: Create the empty Python files that will house the core logic.
        ```bash
        touch main.py database.py models.py services.py config.py
        ```
    3.  **Create Environment File**: Create the `.env` file for configuration.
        ```bash
        touch .env
        ```
* **Definition of Done (DoD)**:
    * ✅ The directory structure `assets/images/`, `assets/videos/`, and `assets/audio/` exists.
    * ✅ The files `main.py`, `database.py`, `models.py`, `services.py`, and `config.py` exist in the project root.
    * ✅ The `.env` file exists and is correctly ignored by Git.

---

### **Task 1.3: Configuration Management**

* **Goal**: Implement a secure and flexible way to manage application settings.
* **Steps**:
    1.  **Populate `.env` File**: Add the MongoDB connection details to the `.env` file.
        ```ini
        # .env
        MONGO_URI="mongodb://localhost:27017/"
        DB_NAME="documedica_refactored"
        ```
    2.  **Implement `config.py`**: Write the code to load and expose these settings.

        ```python
        # config.py
        import os
        from dotenv import load_dotenv

        # Load environment variables from .env file
        load_dotenv()

        # Database Configuration
        MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        DB_NAME = os.getenv("DB_NAME", "documedica_refactored")

        # Asset Paths
        ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
        IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
        VIDEOS_DIR = os.path.join(ASSETS_DIR, 'videos')
        AUDIO_DIR = os.path.join(ASSETS_DIR, 'audio')
        ```
* **Definition of Done (DoD)**:
    * ✅ Importing `MONGO_URI` and `DB_NAME` from `config.py` provides the correct values from the `.env` file.
    * ✅ Default values are provided in `os.getenv()` to ensure the application can run even if the `.env` file is missing.

---

### **Task 1.4: Pydantic Data Models Implementation**

* **Goal**: Define robust, self-validating data structures for all application entities.
* **Steps**:
    1.  **Implement Models in `models.py`**: Write the Pydantic models as specified in the master plan. Pay close attention to types, default values, and MongoDB compatibility.

        ```python
        # models.py
        from pydantic import BaseModel, Field
        from typing import List, Optional, Literal
        from datetime import datetime
        from bson import ObjectId

        class PyObjectId(ObjectId):
            @classmethod
            def __get_validators__(cls):
                yield cls.validate

            @classmethod
            def validate(cls, v):
                if not ObjectId.is_valid(v):
                    raise ValueError("Invalid objectid")
                return ObjectId(v)

            @classmethod
            def __modify_schema__(cls, field_schema):
                field_schema.update(type="string")

        class MediaItem(BaseModel):
            id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
            media_id: str = Field(...)
            type: Literal['image', 'video', 'audio', 'page']
            path: Optional[str] = None
            content: Optional[str] = None
            description: Optional[str] = None
            created_at: datetime = Field(default_factory=datetime.utcnow)

            class Config:
                allow_population_by_field_name = True
                arbitrary_types_allowed = True
                json_encoders = {ObjectId: str}

        class Question(BaseModel):
            id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
            question_id: str = Field(...)
            text: str
            source: str
            tags: List[str] = Field(default_factory=list)
            is_marked: bool = False
            is_favorite: bool = False
            notes: Optional[str] = None
            media_placeholders: List[dict] = Field(default_factory=list) # e.g., [{"placeholder": "%%IMG1%%", "media_id": "xyz"}]
            created_at: datetime = Field(default_factory=datetime.utcnow)
            updated_at: datetime = Field(default_factory=datetime.utcnow)

            class Config:
                allow_population_by_field_name = True
                arbitrary_types_allowed = True
                json_encoders = {ObjectId: str}

        class Source(BaseModel):
            id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
            name: str = Field(...)
            description: Optional[str] = None
            url: Optional[str] = None

            class Config:
                allow_population_by_field_name = True
                arbitrary_types_allowed = True
                json_encoders = {ObjectId: str}
        ```
* **Definition of Done (DoD)**:
    * ✅ The `models.py` file contains the `Question`, `MediaItem`, and `Source` Pydantic models.
    * ✅ Models include robust type hinting and validation (e.g., `Literal` for media type).
    * ✅ A custom `PyObjectId` class is implemented to handle MongoDB's `ObjectId` seamlessly within Pydantic.
    * ✅ `Config` subclasses are correctly configured for MongoDB aliasing (`_id`) and JSON serialization.
    * ✅ Instantiating a model with invalid data (e.g., wrong type) raises a `ValidationError`.

---

### **Task 1.5: Database Connection and Basic CRUD Layer**

* **Goal**: Create a reliable, reusable, and well-documented class for all MongoDB interactions.
* **Steps**:
    1.  **Implement `Database` Class in `database.py`**: Write the class to manage the connection and provide CRUD operations.

        ```python
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
                if not hasattr(self, 'client'):
                    try:
                        self.client = MongoClient(config.MONGO_URI)
                        # The ismaster command is cheap and does not require auth.
                        self.client.admin.command('ismaster')
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

            def create_document(self, collection_name: str, document: Dict[str, Any]) -> Optional[str]:
                """Inserts a new document into a collection."""
                collection = self.get_collection(collection_name)
                if collection is not None:
                    result = collection.insert_one(document)
                    return str(result.inserted_id)
                return None

            def get_document_by_id(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
                """Finds a single document by its _id."""
                collection = self.get_collection(collection_name)
                if collection is not None:
                    return collection.find_one({"_id": ObjectId(document_id)})
                return None

            def find_documents(self, collection_name: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
                """Finds multiple documents matching a query."""
                collection = self.get_collection(collection_name)
                if collection is not None:
                    return list(collection.find(query))
                return []

            def update_document(self, collection_name: str, document_id: str, updates: Dict[str, Any]) -> bool:
                """Updates a document by its _id."""
                collection = self.get_collection(collection_name)
                if collection is not None:
                    result = collection.update_one({"_id": ObjectId(document_id)}, {"$set": updates})
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
        ```
    2.  **Add a Basic Test**: In a temporary test script or `if __name__ == "__main__"` block, verify the functionality.
        * Create a `Database` instance.
        * Use `create_document` to add a sample `Source` document.
        * Use `get_document_by_id` to retrieve it.
        * Use `update_document` to change its description.
        * Use `delete_document` to clean it up.
        * Call `db_client.close()` at the end.

* **Definition of Done (DoD)**:
    * ✅ The `Database` class is implemented as a singleton to prevent multiple connections.
    * ✅ The class successfully connects to the MongoDB instance on initialization.
    * ✅ All CRUD methods (`create`, `get`, `update`, `delete`) are implemented and function correctly against the database.
    * ✅ Methods correctly handle `ObjectId` conversions for queries.
    * ✅ Basic connection error handling is in place.
    * ✅ A test script confirms that all CRUD operations work as expected.

---

**Phase 1 Completion Review**: Once all tasks are completed and their DoD criteria are met, Phase 1 is officially concluded. The project now has a solid, well-structured foundation ready for the implementation of core application services in Phase 2.