from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

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
    # Map the DB's string '_id' to our main identifier 'question_id'
    question_id: str = Field(..., alias="_id")
    name: str
    source: str
    tags: List[str] = Field(default_factory=list)

    # Use the exact field name 'images' and the new ImageSet model
    images: ImageSet = Field(default_factory=ImageSet)

    # Use clearer names for the HTML content
    question_html: str = Field(..., alias="question")
    explanation_html: str = Field(..., alias="explanation")

    # The list of choices using our new Choice model
    choices: List[Choice]

    # Align with the database's boolean flags
    flagged: bool = False
    difficult: bool = False

    # --- Fields we are adding for our app's functionality ---
    is_favorite: bool = False
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # Pydantic v2 configuration
        validate_by_name = True
        populate_by_name = True


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