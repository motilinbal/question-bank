# question_service.py

import streamlit as st
import re
import os
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

        primary_question_assets = []
        for asset_id in question_doc.get("images", {}).get("question", []):
            image_doc = db_helpers.get_asset_document_by_id(asset_id, "Images")
            if image_doc:
                asset = FileAsset(
                    uuid=asset_id, name=image_doc.get("name", ""), asset_type=AssetType.IMAGE,
                    file_path=f"static/images/{image_doc.get('name', '')}"
                )
                primary_question_assets.append(asset)
                continue
            audio_doc = db_helpers.get_asset_document_by_id(asset_id, "Audio")
            if audio_doc:
                asset = FileAsset(
                    uuid=asset_id, name=audio_doc.get("name", ""), asset_type=AssetType.AUDIO,
                    file_path=f"static/audio/{audio_doc.get('name', '')}"
                )
                primary_question_assets.append(asset)
        
        primary_explanation_assets = []
        for asset_id in question_doc.get("images", {}).get("explanation", []):
            image_doc = db_helpers.get_asset_document_by_id(asset_id, "Images")
            if image_doc:
                asset = FileAsset(
                    uuid=asset_id, name=image_doc.get("name", ""), asset_type=AssetType.IMAGE,
                    file_path=f"static/images/{image_doc.get('name', '')}"
                )
                primary_explanation_assets.append(asset)
                continue
            audio_doc = db_helpers.get_asset_document_by_id(asset_id, "Audio")
            if audio_doc:
                asset = FileAsset(
                    uuid=asset_id, name=audio_doc.get("name", ""), asset_type=AssetType.AUDIO,
                    file_path=f"static/audio/{audio_doc.get('name', '')}"
                )
                primary_explanation_assets.append(asset) 

        return Question(
            id=question_doc["_id"],
            name=question_doc.get("name", ""),
            source=question_doc.get("source", ""),
            tags=question_doc.get("tags", []),
            choices=[Choice(**c) for c in question_doc.get("choices", [])],
            raw_question_html=question_doc.get("question", ""),
            raw_explanation_html=question_doc.get("explanation", ""),
            primary_question_assets=primary_question_assets,
            primary_explanation_assets=primary_explanation_assets,
        )


    def _hydrate_html(self, raw_html: str, inline_assets: list, start_index: int) -> str:
        """
        Recursively finds asset placeholders, populates the inline_assets list,
        and replaces placeholders with appropriate content or links.
        """
        if not raw_html:
            return ""

        link_pattern = re.compile(r'<a[^>]*href="\[\[(.*?)\]\]"[^>]*>(.*?)</a>', re.DOTALL)
        media_pattern = re.compile(r'src="\[\[(.*?)\]\]"(?=[^>]*>)')
        current_asset_index = start_index

        def replace_link_and_collect(match):
            nonlocal current_asset_index
            asset_id, original_text = match.group(1), match.group(2).strip()
            asset_type = db_helpers.get_asset_type_from_db(asset_id)
            asset_object = None

            if not asset_type: return original_text

            if asset_type in [AssetType.IMAGE, AssetType.AUDIO, AssetType.VIDEO]:
                collection_name = f"{asset_type.value.capitalize()}s"
                doc = db_helpers.get_asset_document_by_id(asset_id, collection_name)
                if doc:
                    asset_object = FileAsset(
                        uuid=asset_id, name=doc.get("name", ""), asset_type=asset_type,
                        file_path=f"static/{asset_type.value}s/{doc.get('name', '')}",
                        link_text=original_text
                    )
            elif asset_type in [AssetType.PAGE, AssetType.TABLE]:
                html_content = db_helpers.get_content_asset_html(asset_id, asset_type)
                if html_content:
                    processed_nested_html = self._hydrate_html(html_content, inline_assets, len(inline_assets))
                    

                    asset_object = ContentAsset(
                        uuid=asset_id, name=original_text, asset_type=asset_type,
                        html_content=processed_nested_html,
                        link_text=original_text
                    )

            if asset_object:
                inline_assets.append(asset_object)
                replacement_html = f'<span style="color: #80bfff; text-decoration: underline; cursor: pointer;">{original_text}<sup>[{current_asset_index + 1}]</sup></span>'
                current_asset_index += 1
                return replacement_html
            
            return original_text

        def replace_media_src(match):
            asset_id = match.group(1)
            asset_type = db_helpers.get_asset_type_from_db(asset_id)
            if asset_type in [AssetType.IMAGE, AssetType.AUDIO, AssetType.VIDEO]:
                collection_name = f"{asset_type.value.capitalize()}s"
                doc = db_helpers.get_asset_document_by_id(asset_id, collection_name)
                if doc:
                    file_name = doc.get('name', '')
                    if file_name:
                        asset_type_plural = f"{asset_type.value}s"
                        static_url = f"/app/static/{asset_type_plural}/{file_name}"
                        return f'src="{static_url}"'
            return 'src=""'

        processed_html = link_pattern.sub(replace_link_and_collect, raw_html)
        final_html = media_pattern.sub(replace_media_src, processed_html)
        return final_html.replace('height:100%', '')

    def get_question(self, question_id: str) -> Question | None:
        question = self._fetch_raw_question_by_id(question_id)
        if not question: return None
        
        all_inline_assets = []
        question.processed_question_html = self._hydrate_html(question.raw_question_html, all_inline_assets, 0)
        question.processed_explanation_html = self._hydrate_html(question.raw_explanation_html, all_inline_assets, len(all_inline_assets))
        question.inline_assets = all_inline_assets
        return question

    def toggle_favorite(self, question_id: str) -> bool:
        question_doc = db_client.get_collection("Questions").find_one({"_id": question_id})
        if not question_doc: return False
        new_status = not question_doc.get("difficult", False)
        db_helpers.set_favorite_status(question_id, new_status)
        self._fetch_raw_question_by_id.clear()
        return new_status

    def toggle_done(self, question_id: str) -> bool:
        question_doc = db_client.get_collection("Questions").find_one({"_id": question_id})
        if not question_doc: return False
        new_status = not question_doc.get("flagged", False)
        db_helpers.set_done_status(question_id, new_status)
        self._fetch_raw_question_by_id.clear()
        return new_status

    def get_question_status(self, question_id: str) -> dict:
        question_doc = db_client.get_collection("Questions").find_one({"_id": question_id})
        if not question_doc: return {"is_favorite": False, "is_done": False}
        return {"is_favorite": question_doc.get("difficult", False), "is_done": question_doc.get("flagged", False)}

question_service = QuestionService()