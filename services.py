import json
import shutil
import os
from typing import Dict, Any, Optional
from datetime import datetime

from database import db_client
from models import Source, MediaItem, Question
import config


class IngestionService:
    """Handles the ingestion of new questions and media from structured data."""

    def get_or_create_source(self, source_name: str, source_desc: str = "") -> str:
        """Finds a source by name or creates it if it doesn't exist.

        Args:
            source_name: The name of the source to find or create.
            source_desc: Optional description for the source if creating new.

        Returns:
            The ObjectId string of the existing or newly created source.
        """
        sources_collection = db_client.get_collection(config.SOURCES_COLLECTION)
        existing_source = sources_collection.find_one({"name": source_name})
        if existing_source:
            print(f"Found existing source: {source_name}")
            return str(existing_source["_id"])
        else:
            print(f"Creating new source: {source_name}")
            new_source = Source(name=source_name, description=source_desc)
            source_id = db_client.create_document(
                config.SOURCES_COLLECTION, new_source.model_dump(by_alias=True)
            )
            return source_id

    def process_media_item(self, media_data: Dict[str, Any]) -> str:
        """Processes a single media item, saves it, and returns its media_id.

        Args:
            media_data: Dictionary containing media item information including
                       media_id, type, and either asset_path or content.

        Returns:
            The media_id of the processed item, or None if processing failed.
        """
        media_id = media_data.get("media_id")
        media_type = media_data.get("type")

        # Check if media already exists
        media_collection = db_client.get_collection(config.MEDIA_COLLECTION)
        if media_collection.find_one({"media_id": media_id}):
            print(f"Media item {media_id} already exists. Skipping.")
            return media_id

        # Use model_validate to handle dict -> Pydantic model conversion
        new_media = MediaItem.model_validate(media_data)

        if media_type == "page":
            print(f"Processing page: {media_id}")
            db_client.create_document(
                config.MEDIA_COLLECTION, new_media.model_dump(by_alias=True)
            )

        elif media_type in ["image", "video", "audio"]:
            print(f"Processing file: {media_id}")
            original_asset_path = media_data.get("asset_path")
            if not original_asset_path or not os.path.exists(original_asset_path):
                print(
                    f"Warning: Asset file not found for {media_id} at {original_asset_path}. Skipping file copy."
                )
                return None

            filename = os.path.basename(original_asset_path)
            target_dir = os.path.join(config.ASSETS_DIR, f"{media_type}s")
            target_path = os.path.join(target_dir, filename)

            os.makedirs(target_dir, exist_ok=True)
            shutil.copy(original_asset_path, target_path)

            new_media.path = os.path.join(f"{media_type}s", filename).replace("\\", "/")
            db_client.create_document(
                config.MEDIA_COLLECTION, new_media.model_dump(by_alias=True)
            )

        return media_id

    def import_from_json(self, file_path: str):
        """Main method to run the ingestion process from a JSON file.

        Args:
            file_path: Path to the JSON file containing questions and media data.
                      Expected format includes source_name, source_description,
                      and questions array with media items.
        """
        print(f"\n--- Starting ingestion from {file_path} ---")
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing JSON file: {e}")
            return

        source_id = self.get_or_create_source(
            data["source_name"], data.get("source_description", "")
        )
        if not source_id:
            print("Could not get or create source. Aborting.")
            return

        for q_data in data.get("questions", []):
            question_id = q_data["question_id"]
            if db_client.find_documents(
                config.QUESTIONS_COLLECTION, {"question_id": question_id}
            ):
                print(f"Question {question_id} already exists. Skipping.")
                continue

            media_placeholders = []
            for m_data in q_data.get("media", []):
                processed_media_id = self.process_media_item(m_data)
                if processed_media_id:
                    media_placeholders.append(
                        {
                            "placeholder": m_data["placeholder"],
                            "media_id": processed_media_id,
                        }
                    )

            # Use model_validate to create Pydantic instance from dict
            q_data["source"] = data["source_name"]
            q_data["media_placeholders"] = media_placeholders
            new_question = Question.model_validate(q_data)
            db_client.create_document(
                config.QUESTIONS_COLLECTION, new_question.model_dump(by_alias=True)
            )
            print(f"Successfully imported question: {new_question.question_id}")

        print("\n--- Ingestion Complete ---")


class QuestionService:
    """Handles retrieving, rendering, and managing questions."""

    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Retrieves a single question document by its unique question_id.

        Args:
            question_id: The unique identifier of the question to retrieve.

        Returns:
            Question object if found, None otherwise.
        """
        docs = db_client.find_documents(
            config.QUESTIONS_COLLECTION, {"question_id": question_id}
        )
        if docs:
            return Question.model_validate(docs[0])
        return None

    def get_media_item_by_id(self, media_id: str) -> Optional[MediaItem]:
        """Retrieves a single media item by its unique media_id.

        Args:
            media_id: The unique identifier of the media item to retrieve.

        Returns:
            MediaItem object if found, None otherwise.
        """
        docs = db_client.find_documents(config.MEDIA_COLLECTION, {"media_id": media_id})
        if docs:
            return MediaItem.model_validate(docs[0])
        return None

    def render_question_html(self, question: Question) -> str:
        """Replaces media placeholders in question text with actual HTML content.

        Args:
            question: Question object containing text and media placeholders.

        Returns:
            HTML string with placeholders replaced by appropriate media elements.
        """
        html = question.text
        for placeholder_info in question.media_placeholders:
            placeholder = placeholder_info["placeholder"]
            media_id = placeholder_info["media_id"]
            media_item = self.get_media_item_by_id(media_id)

            replacement_html = ""
            if not media_item:
                replacement_html = ""
            elif media_item.type == "page":
                replacement_html = (
                    f"<div class='media-page' style='border: 1px solid #ccc; "
                    f"padding: 10px; margin: 10px 0;'>{media_item.content}</div>"
                )
            elif media_item.type == "image":
                replacement_html = (
                    f"<img src='{media_item.path}' "
                    f"alt='{media_item.description or 'Image'}' "
                    f"style='max-width: 100%; height: auto;'>"
                )
            elif media_item.type == "video":
                replacement_html = (
                    f"<video controls src='{media_item.path}' "
                    f"style='max-width: 100%;'></video>"
                )
            elif media_item.type == "audio":
               replacement_html = f"<audio controls src='{media_item.path}'></audio>"

            html = html.replace(placeholder, replacement_html)
        return html

    def _update_question_field(self, question_id: str, field: str, value: Any) -> bool:
        """Generic helper to update a single field for a question."""
        question_doc = db_client.find_documents(
            config.QUESTIONS_COLLECTION, {"question_id": question_id}
        )
        if not question_doc:
            return False

        doc_id = str(question_doc[0]["_id"])
        updates = {field: value, "updated_at": datetime.utcnow()}
        return db_client.update_document(config.QUESTIONS_COLLECTION, doc_id, updates)

    def toggle_favorite(self, question_id: str) -> bool:
        """Toggles the 'is_favorite' status of a question.

        Args:
            question_id: The unique identifier of the question to update.

        Returns:
            True if the update was successful, False otherwise.
        """
        question = self.get_question_by_id(question_id)
        if question:
            return self._update_question_field(
                question_id, "is_favorite", not question.is_favorite
            )
        return False

    def toggle_marked(self, question_id: str) -> bool:
        """Toggles the 'is_marked' status of a question.

        Args:
            question_id: The unique identifier of the question to update.

        Returns:
            True if the update was successful, False otherwise.
        """
        question = self.get_question_by_id(question_id)
        if question:
            return self._update_question_field(
                question_id, "is_marked", not question.is_marked
            )
        return False

    def update_notes(self, question_id: str, notes: str) -> bool:
        """Updates the 'notes' for a question.

        Args:
            question_id: The unique identifier of the question to update.
            notes: The new notes content to save.

        Returns:
            True if the update was successful, False otherwise.
        """
        return self._update_question_field(question_id, "notes", notes)
