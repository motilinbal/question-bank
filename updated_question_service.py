# updated_question_service.py
"""
Updated question service that works with the new accurate data models
"""
from typing import Optional
from updated_legacy_adapter import updated_legacy_adapter
from models import Question

class UpdatedQuestionService:
    """Question service that works with updated models and real database structure"""
    
    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Get a question by ID using updated adapter"""
        return updated_legacy_adapter.get_question_by_id(question_id)
    
    def render_question_html(self, question: Question, show_answer: bool = False) -> str:
        """Render question HTML with proper structure for medical questions"""
        html = f"<div class='question-container'>"
        
        # Display the main question
        html += f"<div class='question-text'>{question.question_html}</div>"
        
        # Display question images if any
        if question.images.question:
            html += "<div class='question-images'>"
            for img_id in question.images.question:
                # For now, just show the image ID - you'll need to implement actual image serving
                html += f"<div class='image-placeholder'>Image: {img_id}</div>"
            html += "</div>"
        
        # Display choices
        if question.choices:
            html += "<div class='choices'><strong>Choices:</strong><br>"
            for choice in question.choices:
                choice_class = ""
                if show_answer and choice.is_correct:
                    choice_class = "style='background-color: #d4edda; border: 1px solid #c3e6cb; padding: 5px; margin: 2px 0;'"
                html += f"<div {choice_class}>{choice.id}. {choice.text}</div>"
            html += "</div>"
        
        # Show explanation and explanation images only if answer is revealed
        if show_answer:
            html += "<div class='explanation'>"
            html += f"<strong>Explanation:</strong><br>{question.explanation_html}"
            
            # Display explanation images if any
            if question.images.explanation:
                html += "<div class='explanation-images'>"
                for img_id in question.images.explanation:
                    html += f"<div class='image-placeholder'>Explanation Image: {img_id}</div>"
                html += "</div>"
            html += "</div>"
        
        html += "</div>"
        return html
    
    def toggle_favorite(self, question_id: str) -> bool:
        """Toggle favorite status"""
        question = self.get_question_by_id(question_id)
        if question:
            new_value = not question.is_favorite
            return updated_legacy_adapter.update_question_field(question_id, "is_favorite", new_value)
        return False
    
    def toggle_marked(self, question_id: str) -> bool:
        """Toggle marked status (difficult)"""
        question = self.get_question_by_id(question_id)
        if question:
            new_value = not question.difficult
            return updated_legacy_adapter.update_question_field(question_id, "is_marked", new_value)
        return False
    
    def update_notes(self, question_id: str, notes: str) -> bool:
        """Update notes for a question"""
        return updated_legacy_adapter.update_question_field(question_id, "notes", notes)

# Global service instance
updated_question_service = UpdatedQuestionService()