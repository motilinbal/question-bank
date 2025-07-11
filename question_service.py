# question_service.py

import streamlit as st
import re
from typing import Union
from database import db_client
import database_helpers as db_helpers
from models import Question, FileAsset, AssetType, Choice, ContentAsset, LinkAsset

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
        
        # --- Fetch Primary Explanation Assets (from 'images' field) ---
        primary_explanation_assets = []
        for asset_id in question_doc.get("images", {}).get("explanation", []):
            # Check if it's an Image
            image_doc = db_helpers.get_asset_document_by_id(asset_id, "Images")
            if image_doc:
                asset = FileAsset(
                    uuid=asset_id,
                    name=image_doc.get("name", ""),
                    asset_type=AssetType.IMAGE,
                    file_path=f"assets/images/{image_doc.get('name', '')}"
                )
                primary_explanation_assets.append(asset)
                continue

            # Check if it's Audio
            audio_doc = db_helpers.get_asset_document_by_id(asset_id, "Audio")
            if audio_doc:
                asset = FileAsset(
                    uuid=asset_id,
                    name=audio_doc.get("name", ""),
                    asset_type=AssetType.AUDIO,
                    file_path=f"assets/audio/{audio_doc.get('name', '')}"
                )
                primary_explanation_assets.append(asset) 

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

    def _hydrate_html(self, html: str) -> str:
        """
        Finds all placeholder <a> tags with href="[[...]]" and replaces them
        with a clean, functional link.
        """
        if not html:
            return ""

        # FINAL, CORRECT REGEX:
        # This specifically finds <a> tags where the href is a [[...]] placeholder.
        # It captures the UUID inside the brackets.
        # re.DOTALL flag makes . match newlines too
        placeholder_pattern = re.compile(r'<a[^>]*href="\[\[(.*?)\]\]"[^>]*>.*?</a>', re.DOTALL)

        def replace_placeholder(match):
            # The UUID is in the first (and only) capture group.
            asset_id = match.group(1)

            # It's an internal UUID, find its type
            asset_type = db_helpers.get_asset_type_from_db(asset_id)

            if asset_type in [AssetType.PAGE, AssetType.TABLE, AssetType.IMAGE, AssetType.VIDEO, AssetType.AUDIO]:
                # For Pages and Tables, create a link that can trigger a modal in the UI
                return f'<a href="/viewer/{asset_type.value}/{asset_id}" target="_blank">View {asset_type.value.capitalize()}</a>'

            # If the asset is not found, return an error message.
            return f'[Asset Not Found: {asset_id}]'

        return placeholder_pattern.sub(replace_placeholder, html)

    def get_question(self, question_id: str) -> Question | None:
        """
        Public method to get the fully processed and hydrated question.
        """
        question = self._fetch_raw_question_by_id(question_id)
        if not question:
            return None
        
        # Hydrate the HTML
        question.processed_question_html = self._hydrate_html(question.raw_question_html)
        question.processed_explanation_html = self._hydrate_html(question.raw_explanation_html)
        
        return question

# Instantiate a singleton of the service for the app to use
question_service = QuestionService()