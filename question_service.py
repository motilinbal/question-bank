# question_service.py

import streamlit as st
from database import db_client
import database_helpers as db_helpers
from models import Question, FileAsset, AssetType, Choice

class QuestionService:
    @st.cache_data(show_spinner=False)
    def _fetch_raw_question_by_id(_self, question_id: str) -> Question | None:
        """
        Fetches the raw question data from MongoDB and populates the base Question model.
        This method is cached to ensure high performance on repeated lookups.
        """
        question_doc = db_client.get_collection("Questions").find_one({"_id": question_id})
        if not question_doc:
            return None

        # --- Fetch Primary Assets (from 'images' field) ---
        primary_question_assets = []
        for asset_id in question_doc.get("images", {}).get("question", []):
            # Check if it's an Image
            image_doc = db_helpers.get_asset_document_by_id(asset_id, "Images")
            if image_doc:
                asset = FileAsset(
                    uuid=asset_id,
                    name=image_doc.get("name", ""),
                    asset_type=AssetType.IMAGE,
                    file_path=f"assets/images/{image_doc.get('name', '')}" # Construct path
                )
                primary_question_assets.append(asset)
                continue

            # Check if it's Audio
            audio_doc = db_helpers.get_asset_document_by_id(asset_id, "Audio")
            if audio_doc:
                asset = FileAsset(
                    uuid=asset_id,
                    name=audio_doc.get("name", ""),
                    asset_type=AssetType.AUDIO,
                    file_path=f"assets/audio/{audio_doc.get('name', '')}" # Construct path
                )
                primary_question_assets.append(asset)
        
        # (This logic would be duplicated for primary_explanation_assets)
        # For now, we'll leave it empty to keep the example concise.
        primary_explanation_assets = [] 

        # --- Create the Question Model ---
        question_model = Question(
            id=question_doc["_id"],
            name=question_doc.get("name", ""),
            source=question_doc.get("source", ""),
            tags=question_doc.get("tags", []),
            choices=[Choice(**c) for c in question_doc.get("choices", [])],
            
            # Populate raw HTML fields
            raw_question_html=question_doc.get("question", ""),
            raw_explanation_html=question_doc.get("explanation", ""),
            
            # Populate primary asset fields
            primary_question_assets=primary_question_assets,
            primary_explanation_assets=primary_explanation_assets,
        )

        return question_model

    def get_question(self, question_id: str) -> Question | None:
        """Public method to get the raw question."""
        return self._fetch_raw_question_by_id(question_id)

# Instantiate a singleton of the service for the app to use
question_service = QuestionService()