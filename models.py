from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
from datetime import datetime
from enum import Enum

# --- Asset Models (defined first so they can be used in Question) ---

class AssetType(str, Enum):
    """Enumeration for the different types of assets."""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    PAGE = "page"
    TABLE = "table"
    EXTERNAL_LINK = "external_link"

class BaseAsset(BaseModel):
    """A base model for all asset types, containing common fields."""
    uuid: str
    asset_type: AssetType

class FileAsset(BaseAsset):
    """Represents an asset that corresponds to a physical file on the server."""
    name: str
    file_path: str
    link_text: str = ""

class ContentAsset(BaseAsset):
    """Represents an asset whose content is stored directly as HTML in the database."""
    name: str
    html_content: str
    link_text: str = ""

class LinkAsset(BaseModel):
    """Represents a simple external hyperlink."""
    url: str
    asset_type: AssetType = AssetType.EXTERNAL_LINK

# A sub-model for the multiple-choice answers
class Choice(BaseModel):
    text: str
    id: int
    is_correct: bool

# A sub-model for the new way images are structured
class ImageSet(BaseModel):
    question: List[str] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)

class Question(BaseModel):
    """
    Represents a fully processed question, including all its categorized assets and processed HTML.
    This is the "target" model that our new service will produce.
    """
    id: str
    name: str
    source: str
    tags: list[str]
    choices: list[Choice]
    is_favorite: bool = False
    is_marked: bool = False
    notes: str = ""

    # Raw HTML content from the database
    raw_question_html: str
    raw_explanation_html: str

    # HTML content after [[...]] placeholders have been processed
    processed_question_html: str = ""
    processed_explanation_html: str = ""

    # Structured lists of all assets associated with the question
    primary_question_assets: list[FileAsset] = []
    primary_explanation_assets: list[FileAsset] = []
    
    # List of inline assets found in the HTML content
    inline_assets: list[Union[FileAsset, ContentAsset, LinkAsset]] = []


# MediaItem and Source models remain the same as they describe our *target* schema
class MediaItem(BaseModel):
    id: str = Field(default_factory=str, alias="_id") # Assuming media IDs are also strings
    media_id: str = Field(...)
    type: str # e.g., 'image', 'video', 'audio', 'page'
    path: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        validate_by_name = True
        populate_by_name = True

class Source(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    name: str = Field(...)
    description: Optional[str] = None
    url: Optional[str] = None

    class Config:
        validate_by_name = True
        populate_by_name = True

