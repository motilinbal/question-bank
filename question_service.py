# question_service.py

import streamlit as st
import re
import base64
import mimetypes
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

    def _hydrate_html(self, raw_html: str, inline_assets: list, start_index: int) -> str:
        """
        Recursively finds all asset placeholders (in <a> and <img> tags),
        replaces them, and populates the inline_assets list.
        """
        if not raw_html:
            return ""

        # --- PATTERN 1: For <a> tags, e.g., <a href="[[...]]">text</a> ---
        # This pattern replaces the entire link with an annotated span.
        link_pattern = re.compile(
            r'<a[^>]*href="\[\[(.*?)\]\]"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        
        # --- PATTERN 2: For <img>, <audio>, <video> tags, e.g., <img src="[[...]]"> ---
        # This pattern replaces the src attribute with a Base64 data URI.
        media_pattern = re.compile(r'src="\[\[(.*?)\]\]"(?=[^>]*>)')

        current_asset_index = start_index

        def replace_link_and_collect(match):
            nonlocal current_asset_index
            asset_id = match.group(1)
            original_text = match.group(2).strip()
            asset_type = db_helpers.get_asset_type_from_db(asset_id)
            
            asset_object = None
            
            # --- THIS IS THE NEW, UNIVERSAL LOGIC ---
            if not asset_type:
                return original_text # Asset type not found, return plain text

            if asset_type in [AssetType.IMAGE, AssetType.AUDIO, AssetType.VIDEO]:
                collection_name = f"{asset_type.value.capitalize()}s"
                doc = db_helpers.get_asset_document_by_id(asset_id, collection_name)
                if doc:
                    asset_object = FileAsset(
                        uuid=asset_id, name=doc.get("name", ""), asset_type=asset_type,
                        file_path=f"assets/{asset_type.value}s/{doc.get('name', '')}",
                        link_text=original_text
                    )
            elif asset_type in [AssetType.PAGE, AssetType.TABLE]:
                html_content = db_helpers.get_content_asset_html(asset_id, asset_type)
                if html_content:
                    # RECURSIVE CALL: process the nested HTML
                    processed_nested_html = self._hydrate_html(html_content, inline_assets, len(inline_assets))
                    asset_object = ContentAsset(
                        uuid=asset_id, name=original_text, asset_type=asset_type,
                        html_content=processed_nested_html,
                        link_text=original_text
                    )

            if asset_object:
                inline_assets.append(asset_object)
                replacement_html = (
                    f'<span style="color: #80bfff; text-decoration: underline; cursor: pointer;">'
                    f'{original_text}<sup>[{current_asset_index + 1}]</sup></span>'
                )
                current_asset_index += 1
                return replacement_html
            
            return original_text # Fallback to plain text if asset not found

        def replace_media_src(match):
            asset_id = match.group(1)
            asset_type = db_helpers.get_asset_type_from_db(asset_id)

            if asset_type in [AssetType.IMAGE, AssetType.AUDIO, AssetType.VIDEO]:
                collection_name = f"{asset_type.value.capitalize()}s"
                doc = db_helpers.get_asset_document_by_id(asset_id, collection_name)
                if doc:
                    file_path = f"assets/{asset_type.value}s/{doc.get('name', '')}"
                    try:
                        with open(file_path, "rb") as f:
                            data = f.read()
                        base64_data = base64.b64encode(data).decode('utf-8')
                        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                        # Return the full src attribute with the data URI
                        return f'src="data:{mime_type};base64,{base64_data}"'
                    except FileNotFoundError:
                        return 'src=""' # Return empty src if file not found
            return 'src=""' # Fallback for unknown assets

        # Perform hydration in two passes
        processed_html = link_pattern.sub(replace_link_and_collect, raw_html)
        final_html = media_pattern.sub(replace_media_src, processed_html)
        
        return final_html

    def get_question(self, question_id: str) -> Question | None:
        """
        Public method to get the fully processed and hydrated question.
        """
        question = self._fetch_raw_question_by_id(question_id)
        if not question:
            return None
        
        all_inline_assets = []
        question.processed_question_html = self._hydrate_html(question.raw_question_html, all_inline_assets, 0)
        question.processed_explanation_html = self._hydrate_html(question.raw_explanation_html, all_inline_assets, len(all_inline_assets))
        
        question.inline_assets = all_inline_assets
        return question

# Instantiate a singleton of the service for the app to use
question_service = QuestionService()