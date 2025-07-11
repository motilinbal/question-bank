# database_helpers.py

from database import db_client
from models import AssetType

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