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

    def _hydrate_html(self, question: Question):
        """
        Parses the raw HTML to find asset placeholders.
        1. Replaces the original <a> tag in the HTML with just its text.
        2. Populates a structured list of 'inline_assets' in the Question object.
        """
        # Process question HTML
        if not question.raw_question_html:
            question.processed_question_html = ""
        else:
            question.processed_question_html = self._process_html_content(question.raw_question_html, question)

        # Process explanation HTML
        if not question.raw_explanation_html:
            question.processed_explanation_html = ""
        else:
            question.processed_explanation_html = self._process_html_content(question.raw_explanation_html, question)

    def _process_html_content(self, html: str, question: Question) -> str:
        """Helper method to process HTML content and collect inline assets."""
        if not html:
            return ""

        # This regex finds the <a> tags and captures the asset ID and the link text
        placeholder_pattern = re.compile(r'<a[^>]*href="\[\[(.*?)\]\]"[^>]*>(.*?)</a>', re.DOTALL)
        
        # Use a function to perform the replacement and populate the inline_assets list
        def replace_and_collect(match):
            asset_id = match.group(1)
            original_text = match.group(2).strip()
            asset_type = db_helpers.get_asset_type_from_db(asset_id)
            
            # Create the appropriate asset object and add it to our list
            if asset_type in [AssetType.IMAGE, AssetType.AUDIO, AssetType.VIDEO]:
                collection_name = f"{asset_type.value.capitalize()}s"
                doc = db_helpers.get_asset_document_by_id(asset_id, collection_name)
                if doc:
                    asset = FileAsset(
                        uuid=asset_id,
                        name=doc.get("name", ""),
                        asset_type=asset_type,
                        file_path=f"assets/{asset_type.value}s/{doc.get('name', '')}",
                        link_text=original_text  # Store the original link text
                    )
                    question.inline_assets.append(asset)
            
            elif asset_type in [AssetType.PAGE, AssetType.TABLE]:
                html_content = db_helpers.get_content_asset_html(asset_id, asset_type)
                if html_content:
                    asset = ContentAsset(
                        uuid=asset_id,
                        name=original_text,
                        asset_type=asset_type,
                        html_content=html_content,
                        link_text=original_text
                    )
                    question.inline_assets.append(asset)

            return original_text  # Return just the text to replace the <a> tag

        return placeholder_pattern.sub(replace_and_collect, html)

    def get_question(self, question_id: str) -> Question | None:
        """
        Public method to get the fully processed and hydrated question.
        """
        question = self._fetch_raw_question_by_id(question_id)
        if not question:
            return None
        
        # Hydrate the HTML (this now modifies the question object in-place)
        self._hydrate_html(question)
        
        return question

# Instantiate a singleton of the service for the app to use
question_service = QuestionService()