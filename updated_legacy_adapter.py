# updated_legacy_adapter.py
"""
Updated adapter to work with the new accurate data models
"""
from typing import Dict, Any, List, Optional
from database import db_client
import config
from models import Question, Choice, ImageSet

class UpdatedLegacyAdapter:
    """Adapts legacy database structure to work with our updated models"""
    
    def get_sources(self) -> List[str]:
        """Get unique sources from Questions collection"""
        try:
            pipeline = [{"$group": {"_id": "$source"}}]
            sources = [s["_id"] for s in db_client.get_collection(config.QUESTIONS_COLLECTION).aggregate(pipeline)]
            return sorted([s for s in sources if s])
        except:
            return []
    
    def get_tags(self) -> List[str]:
        """Get unique tags from Questions collection"""
        try:
            pipeline = [{"$unwind": "$tags"}, {"$group": {"_id": "$tags"}}]
            tags = [t["_id"] for t in db_client.get_collection(config.QUESTIONS_COLLECTION).aggregate(pipeline)]
            return sorted([t for t in tags if t])
        except:
            return []
    
    def find_questions_paginated(self, query: Dict[str, Any], page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Find questions with pagination and return paginated results with total count"""
        # Map our query fields to legacy fields
        legacy_query = self._build_legacy_query(query)
        
        # Define lightweight projection for list view (exclude heavy HTML content)
        list_projection = {
            "_id": 1,
            "name": 1,
            "source": 1,
            "tags": 1,
            "flagged": 1,
            "difficult": 1,
            "notes": 1
        }
        
        # Calculate pagination
        skip_amount = (page - 1) * page_size
        
        # Get total count efficiently
        total_count = db_client.count_documents(config.QUESTIONS_COLLECTION, legacy_query)
        
        # Get paginated documents with projection
        raw_docs = db_client.find_documents(
            config.QUESTIONS_COLLECTION, 
            legacy_query, 
            projection=list_projection,
            skip=skip_amount,
            limit=page_size
        )
        
        # Convert to lightweight Question objects for list view
        questions = []
        for doc in raw_docs:
            try:
                # Create minimal Question object for list view (no heavy HTML content)
                question_data = {
                    "_id": doc["_id"],
                    "name": doc.get("name", ""),
                    "source": doc.get("source", ""),
                    "tags": doc.get("tags", []),
                    "images": ImageSet(),  # Empty for list view
                    "question": "",  # Empty for list view
                    "explanation": "",  # Empty for list view
                    "choices": [],  # Empty for list view
                    "flagged": doc.get("flagged", False),
                    "difficult": doc.get("difficult", False),
                    "is_favorite": doc.get("flagged", False),
                    "notes": doc.get("notes", "")
                }
                
                question = Question.model_validate(question_data)
                questions.append(question)
            except Exception as e:
                print(f"Warning: Could not parse question {doc.get('_id', 'unknown')}: {e}")
                continue
        
        return {
            "questions": questions,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    def _build_legacy_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Build legacy MongoDB query from our query format"""
        legacy_query = {}
        
        if "text" in query:
            search_term = query["text"]
            legacy_query["$text"] = {"$search": search_term}
        
        if "source" in query:
            legacy_query["source"] = query["source"]
            
        if "tags" in query:
            legacy_query["tags"] = query["tags"]
            
        if "is_favorite" in query:
            legacy_query["flagged"] = query["is_favorite"]
            
        if "is_marked" in query:
            legacy_query["difficult"] = query["is_marked"]
        
        return legacy_query
    
    def find_questions(self, query: Dict[str, Any], projection: Dict[str, Any] = None) -> List[Question]:
        """Legacy method for backward compatibility - fetches full questions"""
        legacy_query = self._build_legacy_query(query)
        raw_docs = db_client.find_documents(config.QUESTIONS_COLLECTION, legacy_query, projection)
        
        # Convert to full Question objects (original implementation)
        questions = []
        for doc in raw_docs:
            try:
                # Parse choices from the legacy format
                choices = []
                if "choices" in doc and doc["choices"]:
                    for i, choice_data in enumerate(doc["choices"], 1):
                        if isinstance(choice_data, dict):
                            choice_text = choice_data.get('text', '')
                            choice_id = choice_data.get('id', i)
                            is_correct = choice_data.get('is_correct', False)
                            choices.append(Choice(text=choice_text, id=choice_id, is_correct=is_correct))
                        elif isinstance(choice_data, str):
                            choices.append(Choice(text=choice_data, id=i, is_correct=(i == 1)))
                        else:
                            continue
                
                # Parse images
                images = ImageSet()
                if "images" in doc and isinstance(doc["images"], dict):
                    images.question = doc["images"].get("question", [])
                    images.explanation = doc["images"].get("explanation", [])
                
                # Create Question object with proper field mapping
                question_data = {
                    "_id": doc["_id"],
                    "name": doc.get("name", ""),
                    "source": doc.get("source", ""),
                    "tags": doc.get("tags", []),
                    "images": images,
                    "question": doc.get("question", ""),
                    "explanation": doc.get("explanation", ""),
                    "choices": choices,
                    "flagged": doc.get("flagged", False),
                    "difficult": doc.get("difficult", False),
                    "is_favorite": doc.get("flagged", False),
                    "notes": doc.get("notes", "")
                }
                
                question = Question.model_validate(question_data)
                questions.append(question)
            except Exception as e:
                print(f"Warning: Could not parse question {doc.get('_id', 'unknown')}: {e}")
                continue
        
        return questions
    
    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Get a single question by ID"""
        questions = self.find_questions({"_id": question_id})
        return questions[0] if questions else None
    
    def update_question_field(self, question_id: str, field: str, value: Any) -> bool:
        """Update a question field with proper field mapping"""
        question_doc = db_client.find_documents(config.QUESTIONS_COLLECTION, {"_id": question_id})
        if not question_doc:
            return False
        
        doc_id = str(question_doc[0]["_id"])
        
        # Map our fields to legacy fields
        legacy_field = field
        if field == "is_favorite":
            legacy_field = "flagged"
        elif field == "is_marked":
            legacy_field = "difficult"
        
        updates = {legacy_field: value}
        return db_client.update_document(config.QUESTIONS_COLLECTION, doc_id, updates)

# Global adapter instance
updated_legacy_adapter = UpdatedLegacyAdapter()