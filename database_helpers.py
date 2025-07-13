# database_helpers.py

from database import db_client
from models import AssetType
import os
from PIL import Image

def get_asset_document_by_id(asset_id: str, collection_name: str) -> dict | None:
    """Fetches a single asset document from a given collection by its ID."""
    return db_client.get_collection(collection_name).find_one({"_id": asset_id})

def get_asset_type_from_db(asset_id: str) -> AssetType | None:
    """
    Checks all asset collections to find the type of a given asset ID.
    This is for resolving inline [[...]] assets, which we will use in Step 2.2.
    """
    if db_client.get_collection("Images").find_one({"_id": asset_id}, {"_id": 1}):
        return AssetType.IMAGE
    if db_client.get_collection("Audio").find_one({"_id": asset_id}, {"_id": 1}):
        return AssetType.AUDIO
    if db_client.get_collection("Videos").find_one({"_id": asset_id}, {"_id": 1}):
        return AssetType.VIDEO
    if db_client.get_collection("Pages").find_one({"_id": asset_id}, {"_id": 1}):
        return AssetType.PAGE
    if db_client.get_collection("Tables").find_one({"_id": asset_id}, {"_id": 1}):
        return AssetType.TABLE
    return None

def get_content_asset_html(asset_id: str, asset_type: AssetType) -> str | None:
    """Fetches the HTML content for a Page or Table asset."""
    collection_name = "Pages" if asset_type == AssetType.PAGE else "Tables"
    doc = get_asset_document_by_id(asset_id, collection_name)
    return doc.get("html") if doc else None

def set_favorite_status(question_id: str, is_favorite: bool) -> None:
    """
    Updates the 'difficult' field for a given question to mark it as a favorite.
    """
    db_client.get_collection("Questions").update_one(
        {"_id": question_id},
        {"$set": {"difficult": is_favorite}}
    )

def set_done_status(question_id: str, is_done: bool) -> None:
    """
    Updates the 'flagged' field for a given question to mark it as done.
    """
    db_client.get_collection("Questions").update_one(
        {"_id": question_id},
        {"$set": {"flagged": is_done}}
    )

def get_image_dimensions(image_id: str) -> tuple[int, int] | None:
    """
    Finds an image by its ID and returns its (width, height) dimensions.
    """
    image_doc = get_asset_document_by_id(image_id, "Images")
    if not image_doc:
        return None
    
    file_path = f"static/images/{image_doc.get('name', '')}"
    
    if not os.path.exists(file_path):
        return None
        
    try:
        with Image.open(file_path) as img:
            return img.size  # Returns (width, height)
    except Exception:
        return None