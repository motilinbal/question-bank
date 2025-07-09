# DocuMedica Refactoring: Phase 2 Implementation Plan

## **Objective: Data Ingestion and Core Application Logic**

With the foundational database and models in place, Phase 2 focuses on building the application's engine. We will implement the services required to process and import data from external sources into our MongoDB schema and create the logic for retrieving and managing questions.

**Estimated Time to Complete:** 5-7 hours

---

### **Task 2.1: Data Ingestion Service**

* **Goal**: Develop a robust service capable of parsing structured data (e.g., from JSON files), creating the corresponding documents in MongoDB, and organizing associated asset files. This service will be the primary mechanism for populating the application with content.

* **Steps**:

    1.  **Create a Sample Data Structure**: To guide development, define a sample JSON structure that represents a batch of questions to be imported. Create a file named `sample_import.json` in the project root. This structure should mirror the relationships in our models.

        ```json
        // sample_import.json
        {
          "source_name": "UWorld",
          "source_description": "A popular question bank for medical students.",
          "questions": [
            {
              "question_id": "uw-med-123",
              "text": "A 45-year-old patient presents with chest pain. An ECG is shown below. %%EXHIBIT_1%% What is the most likely diagnosis?",
              "tags": ["cardiology", "ecg", "mi"],
              "media": [
                {
                  "media_id": "uw-ecg-456",
                  "type": "image",
                  "placeholder": "%%EXHIBIT_1%%",
                  "asset_path": "path/to/your/local/ecg-456.jpg",
                  "description": "ECG showing ST-segment elevation."
                }
              ]
            },
            {
              "question_id": "uw-pharm-789",
              "text": "What is the mechanism of action for the drug described in the attached page? %%PAGE_1%%",
              "tags": ["pharmacology", "moa"],
              "media": [
                {
                  "media_id": "uw-drug-info-101",
                  "type": "page",
                  "placeholder": "%%PAGE_1%%",
                  "content": "<h1>Aspirin</h1><p>Aspirin works by inhibiting cyclooxygenase (COX) enzymes...</p>"
                }
              ]
            }
          ]
        }
        ```

    2.  **Implement the `IngestionService` in `services.py`**: Create a class to encapsulate all ingestion logic. It will interact with the `db_client` and `models`.

        ```python
        # services.py
        import json
        import shutil
        import os
        from typing import Dict, Any, List

        from database import db_client
        from models import Source, MediaItem, Question
        import config

        class IngestionService:
            """Handles the ingestion of new questions and media from structured data."""

            def get_or_create_source(self, source_name: str, source_desc: str = "") -> str:
                """Finds a source by name or creates it if it doesn't exist. Returns the source's ObjectId string."""
                sources_collection = db_client.get_collection("sources")
                existing_source = sources_collection.find_one({"name": source_name})
                if existing_source:
                    print(f"Found existing source: {source_name}")
                    return str(existing_source["_id"])
                else:
                    print(f"Creating new source: {source_name}")
                    new_source = Source(name=source_name, description=source_desc)
                    source_id = db_client.create_document("sources", new_source.dict(by_alias=True))
                    return source_id

            def process_media_item(self, media_data: Dict[str, Any]) -> str:
                """Processes a single media item, saves it, and returns its media_id."""
                media_id = media_data.get("media_id")
                media_type = media_data.get("type")

                # Check if media already exists
                media_collection = db_client.get_collection("media")
                if media_collection.find_one({"media_id": media_id}):
                    print(f"Media item {media_id} already exists. Skipping.")
                    return media_id

                new_media = MediaItem(**media_data)

                if media_type == "page":
                    # Content is already in the data, just save the model
                    print(f"Processing page: {media_id}")
                    db_client.create_document("media", new_media.dict(by_alias=True))

                elif media_type in ["image", "video", "audio"]:
                    # For file-based media, copy the asset to the project's asset folder
                    print(f"Processing file: {media_id}")
                    original_asset_path = media_data.get("asset_path")
                    if not original_asset_path or not os.path.exists(original_asset_path):
                        print(f"⚠️ Warning: Asset file not found for {media_id} at {original_asset_path}. Skipping file copy.")
                        return None # Or handle error as needed

                    filename = os.path.basename(original_asset_path)
                    target_dir = os.path.join(config.ASSETS_DIR, f"{media_type}s") # e.g., assets/images
                    target_path = os.path.join(target_dir, filename)

                    shutil.copy(original_asset_path, target_path)

                    # Update the model's path to the new relative path
                    new_media.path = os.path.join(f"{media_type}s", filename)
                    db_client.create_document("media", new_media.dict(by_alias=True))

                return media_id

            def import_from_json(self, file_path: str):
                """Main method to run the ingestion process from a JSON file."""
                print(f"\n--- Starting ingestion from {file_path} ---")
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"❌ Error reading or parsing JSON file: {e}")
                    return

                source_id = self.get_or_create_source(data["source_name"], data.get("source_description", ""))
                if not source_id:
                     print("❌ Could not get or create source. Aborting.")
                     return

                for q_data in data.get("questions", []):
                    # Check if question already exists
                    questions_collection = db_client.get_collection("questions")
                    if questions_collection.find_one({"question_id": q_data["question_id"]}):
                        print(f"Question {q_data['question_id']} already exists. Skipping.")
                        continue

                    # Process all media for the question
                    media_placeholders = []
                    for m_data in q_data.get("media", []):
                        processed_media_id = self.process_media_item(m_data)
                        if processed_media_id:
                            media_placeholders.append({
                                "placeholder": m_data["placeholder"],
                                "media_id": processed_media_id
                            })

                    # Create the Question document
                    new_question = Question(
                        question_id=q_data["question_id"],
                        text=q_data["text"],
                        source=data["source_name"],
                        tags=q_data.get("tags", []),
                        media_placeholders=media_placeholders
                    )
                    db_client.create_document("questions", new_question.dict(by_alias=True))
                    print(f"✅ Successfully imported question: {new_question.question_id}")

                print("\n--- Ingestion Complete ---")
        ```

    3.  **Update `main.py` for Testing**: Modify `main.py` to run the ingestion service.

        ```python
        # main.py (updated)
        from services import IngestionService

        if __name__ == "__main__":
            # Ensure you have a 'sample_import.json' and the asset file it points to.
            # For example, create a dummy file: `touch path/to/your/local/ecg-456.jpg`
            ingestion_service = IngestionService()
            ingestion_service.import_from_json("sample_import.json")
        ```

* **Definition of Done (DoD)**:
    * ✅ Running `python main.py` successfully parses `sample_import.json`.
    * ✅ A new `Source` document is created in the `sources` collection if it doesn't already exist.
    * ✅ New `MediaItem` documents are created in the `media` collection.
    * ✅ For file-based media, the corresponding file is copied from its original location to the correct subdirectory within the project's `assets` folder.
    * ✅ New `Question` documents are created in the `questions` collection, correctly referencing the source and media placeholders.
    * ✅ The service is idempotent; running the import a second time does not create duplicate documents.

---

### **Task 2.2: Question Retrieval and Rendering Service**

* **Goal**: Create a service to fetch a question and all its associated media from the database, then assemble the full, renderable HTML content.

* **Steps**:

    1.  **Implement `QuestionService` in `services.py`**: Add a new class for handling question-related logic.

        ```python
        # services.py (continued)
        class QuestionService:
            """Handles retrieving, rendering, and managing questions."""

            def get_question_by_id(self, question_id: str) -> Optional[Question]:
                """Retrieves a single question document by its unique question_id."""
                doc = db_client.find_documents("questions", {"question_id": question_id})
                if doc:
                    return Question(**doc[0])
                return None

            def get_media_item_by_id(self, media_id: str) -> Optional[MediaItem]:
                """Retrieves a single media item by its unique media_id."""
                doc = db_client.find_documents("media", {"media_id": media_id})
                if doc:
                    return MediaItem(**doc[0])
                return None

            def render_question_html(self, question: Question) -> str:
                """Replaces media placeholders in question text with actual HTML content."""
                html = question.text
                for placeholder_info in question.media_placeholders:
                    placeholder = placeholder_info["placeholder"]
                    media_id = placeholder_info["media_id"]
                    media_item = self.get_media_item_by_id(media_id)

                    if not media_item:
                        replacement_html = f""
                    elif media_item.type == "page":
                        replacement_html = f"<div class='media-page'>{media_item.content}</div>"
                    elif media_item.type == "image":
                        # In a real app, this might point to a served endpoint, but for local Streamlit,
                        # we can use file paths directly or base64 encode.
                        replacement_html = f"<img src='{media_item.path}' alt='{media_item.description}'>"
                    elif media_item.type == "video":
                        replacement_html = f"<video controls><source src='{media_item.path}'></video>"
                    elif media_item.type == "audio":
                         replacement_html = f"<audio controls><source src='{media_item.path}'></audio>"
                    else:
                        replacement_html = ""

                    html = html.replace(placeholder, replacement_html)
                return html
        ```

* **Definition of Done (DoD)**:
    * ✅ `get_question_by_id` correctly fetches a question and deserializes it into a Pydantic `Question` model.
    * ✅ `get_media_item_by_id` correctly fetches a media item.
    * ✅ `render_question_html` successfully replaces all `%%PLACEHOLDER%%` strings in the question text with the appropriate HTML tags (`<img>`, `<video>`, `<div>` for pages, etc.).

---

### **Task 2.3: Question Management Service**

* **Goal**: Implement methods to modify the state of a question (marking, favoriting, adding notes).

* **Steps**:

    1.  **Extend `QuestionService` in `services.py`**: Add methods for updating question properties.

        ```python
        # services.py (QuestionService extended)
        from datetime import datetime

        class QuestionService:
            # ... (previous methods from Task 2.2) ...

            def _update_question_field(self, question_id: str, field: str, value: Any) -> bool:
                """Generic helper to update a single field for a question."""
                question_doc = db_client.find_documents("questions", {"question_id": question_id})
                if not question_doc:
                    return False

                doc_id = str(question_doc[0]["_id"])
                updates = {
                    field: value,
                    "updated_at": datetime.utcnow()
                }
                return db_client.update_document("questions", doc_id, updates)

            def toggle_favorite(self, question_id: str) -> bool:
                """Toggles the 'is_favorite' status of a question."""
                question = self.get_question_by_id(question_id)
                if question:
                    return self._update_question_field(question_id, "is_favorite", not question.is_favorite)
                return False

            def toggle_marked(self, question_id: str) -> bool:
                """Toggles the 'is_marked' status of a question."""
                question = self.get_question_by_id(question_id)
                if question:
                    return self._update_question_field(question_id, "is_marked", not question.is_marked)
                return False

            def update_notes(self, question_id: str, notes: str) -> bool:
                """Updates the 'notes' for a question."""
                return self._update_question_field(question_id, "notes", notes)
        ```

* **Definition of Done (DoD)**:
    * ✅ Calling `toggle_favorite` on a `question_id` successfully flips the boolean value of `is_favorite` in the database.
    * ✅ Calling `toggle_marked` successfully flips the `is_marked` value.
    * ✅ Calling `update_notes` successfully overwrites the `notes` field with the provided string.
    * ✅ The `updated_at` field for the question is correctly updated after each modification.

---

**Phase 2 Completion Review**: Upon completing all tasks and meeting their DoD criteria, the application's core logic is now implemented. The system can be populated with data and can programmatically retrieve and manage that data. The project is now ready for the development of the user-facing UI in Phase 3.