#!/usr/bin/env python3
"""
Script to extract and display clean text from a single medical question.
This script connects to the MongoDB database and extracts question data
without making any changes to the database.
"""

import sys
import os
import re
from typing import Dict, Any

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"❌ Failed to import BeautifulSoup: {e}")
    print("Please ensure beautifulsoup4 is installed in your virtual environment")
    print("Run: pip install beautifulsoup4")
    sys.exit(1)

try:
    from database import db_client
except ImportError as e:
    print(f"❌ Failed to import database module: {e}")
    print("Please ensure all dependencies are installed and PYTHONPATH is set correctly")
    sys.exit(1)

def html_to_text(html_content: str) -> str:
    """
    Convert HTML content to clean text using BeautifulSoup with enhanced cleaning.
    
    Args:
        html_content (str): HTML string to convert
        
    Returns:
        str: Clean text without HTML tags and excessive whitespace
    """
    if not html_content:
        return ""
    
    # Parse HTML and extract text
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Get text and normalize whitespace
    text = soup.get_text()
    
    # Remove excessive whitespace and newlines
    # Replace multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Trim leading and trailing whitespace
    text = text.strip()
    
    return text

def process_question_document(question_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single question document and extract clean text.
    
    Args:
        question_doc (Dict): Raw question document from MongoDB
        
    Returns:
        Dict: Clean text organized in a structured format
    """
    # Extract basic information
    question_id = question_doc.get("_id", "")
    name = question_doc.get("name", "")
    source = question_doc.get("source", "")
    tags = question_doc.get("tags", [])
    
    # Extract and clean HTML content
    raw_question_html = question_doc.get("question", "")
    raw_explanation_html = question_doc.get("explanation", "")
    
    clean_question = html_to_text(raw_question_html)
    clean_explanation = html_to_text(raw_explanation_html)
    
    # Process choices
    choices = question_doc.get("choices", [])
    clean_choices = []
    for choice in choices:
        choice_text = choice.get("text", "")
        clean_choice_text = html_to_text(choice_text)
        clean_choices.append({
            "id": choice.get("id"),
            "text": clean_choice_text,
            "is_correct": choice.get("is_correct", False)
        })
    
    # Create structured output
    clean_question_data = {
        "id": question_id,
        "name": name,
        "source": source,
        "tags": tags,
        "question": clean_question,
        "choices": clean_choices,
        "explanation": clean_explanation
    }
    
    return clean_question_data

def main():
    """Main function to connect to database and process one question."""
    print("Connecting to database...")
    
    # Get the Questions collection
    questions_collection = db_client.get_collection("Questions")
    
    if questions_collection is None:
        print("❌ Failed to connect to Questions collection")
        return
    
    # Get one question document
    print("Fetching one question from the database...")
    question_doc = questions_collection.find_one()
    
    if not question_doc:
        print("❌ No questions found in the database")
        return
    
    print(f"✅ Successfully fetched question with ID: {question_doc.get('_id', 'Unknown')}")
    
    # Process the question document
    print("\n--- Processing Question Data ---")
    clean_data = process_question_document(question_doc)
    
    # Display the clean data
    print(f"\nQuestion ID: {clean_data['id']}")
    print(f"Name: {clean_data['name']}")
    print(f"Source: {clean_data['source']}")
    print(f"Tags: {clean_data['tags']}")
    
    print("\n--- Clean Question Text ---")
    print(clean_data['question'])
    
    print("\n--- Clean Choices ---")
    for choice in clean_data['choices']:
        print(f"{choice['id']}) {choice['text']} (Correct: {choice['is_correct']})")
    
    print("\n--- Clean Explanation ---")
    print(clean_data['explanation'])
    
    print("\n✅ Script completed successfully. No changes were made to the database.")

if __name__ == "__main__":
    main()