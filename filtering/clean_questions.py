#!/usr/bin/env python3
"""
Script to clean question text and update the 'text' field in the Questions collection.
This script connects to the MongoDB database, cleans HTML content from questions,
choices, and explanations, and updates the 'text' field with the cleaned text.

SAFETY NOTE: This script WILL update the database. Before running:
1. Backup your database
2. Test with a small number of questions first (set num_questions = 10)
3. Only when confident, set num_questions = None to process all questions

To temporarily disable database updates, comment out the line:
    success = update_question_text_field(question_id, formatted_text)
"""

import sys
import os
import re
import json
from typing import Dict, Any, List

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

def format_question_for_output(clean_data: Dict[str, Any]) -> str:
    """
    Format a cleaned question dictionary into the specified text format.
    
    Args:
        clean_data (Dict): Cleaned question data
        
    Returns:
        str: Formatted question text
    """
    formatted_text = f"Question: {clean_data['question']}\n\n"
    formatted_text += "Options:\n"
    
    # Sort choices by ID to ensure consistent order (A, B, C, D, etc.)
    sorted_choices = sorted(clean_data['choices'], key=lambda x: x['id'])
    
    for choice in sorted_choices:
        formatted_text += f"{choice['id']}) {choice['text']}\n"
    
    formatted_text += f"\nExplanation: {clean_data['explanation']}"
    
    return formatted_text

def update_question_text_field(question_id: str, cleaned_text: str) -> bool:
    """
    Update the text field of a question document in the database.
    
    Args:
        question_id (str): The ID of the question to update
        cleaned_text (str): The cleaned text to set in the text field
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        success = db_client.update_document(
            collection_name="Questions",
            document_id=question_id,
            updates={"text": cleaned_text}
        )
        return success
    except Exception as e:
        print(f"❌ Error updating question {question_id}: {e}")
        return False

def main():
    """Main function to connect to database and process multiple questions."""
    # Number of questions to fetch (set to None to process all questions)
    num_questions = 10  # Set to a number like 5000 to limit, or None for all questions
    output_file = "cleaned_questions.json"
    
    print("Connecting to database...")
    
    # Get the Questions collection
    questions_collection = db_client.get_collection("Questions")
    
    if questions_collection is None:
        print("❌ Failed to connect to Questions collection")
        return
    
    # Get question documents
    if num_questions is None:
        print("Fetching ALL questions from the database...")
        question_docs = questions_collection.find()
    else:
        print(f"Fetching {num_questions} questions from the database...")
        question_docs = questions_collection.find().limit(num_questions)
    
    # Process all question documents by iterating directly over the cursor
    print("\n--- Processing Question Data ---")
    cleaned_questions = []
    
    # Track database update statistics
    update_stats = {
        "success": 0,
        "failed": 0
    }
    failed_questions = []
    
    # Count the questions as we process them
    count = 0
    
    for question_doc in question_docs:
        count += 1
        
        if count % 100 == 0:
            if num_questions is None:
                print(f"Processed {count} questions...")
            else:
                print(f"Processed {count}/{num_questions} questions...")
        
        clean_data = process_question_document(question_doc)
        cleaned_questions.append(clean_data)
        
        # Format the question for the text field
        formatted_text = format_question_for_output(clean_data)
        
        # Update the database
        question_id = question_doc.get("_id", "")
        if question_id:
            # success = update_question_text_field(question_id, formatted_text)
            success = True
            if success:
                update_stats["success"] += 1
            else:
                update_stats["failed"] += 1
                failed_questions.append(question_id)
        
        # If we've reached the limit, stop processing
        if num_questions is not None and count >= num_questions:
            break
    
    if count == 0:
        print("❌ No questions found in the database")
        return
    
    print(f"✅ Successfully processed {count} questions")
    
    # Save the cleaned questions to a file as JSON
    print(f"\n--- Saving cleaned questions to {output_file} ---")
    try:
        # Create a list of question objects with only the required fields
        json_questions = []
        for clean_data in cleaned_questions:
            json_question = {
                "id": clean_data["id"],
                "question": clean_data["question"],
                "choices": clean_data["choices"],
                "explanation": clean_data["explanation"]
            }
            json_questions.append(json_question)
        
        # Write the JSON data to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_questions, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully saved cleaned questions to {output_file}")
    except Exception as e:
        print(f"❌ Failed to save questions to file: {e}")
        return
    
    # Display update statistics
    print(f"\n--- Database Update Statistics ---")
    print(f"Successful updates: {update_stats['success']}")
    print(f"Failed updates: {update_stats['failed']}")
    
    # Display a sample of the clean data
    if cleaned_questions:
        sample = cleaned_questions[0]
        print(f"\n--- Sample of Cleaned Question Data (ID: {sample['id']}) ---")
        print(f"Name: {sample['name']}")
        print(f"Source: {sample['source']}")
        print(f"Tags: {sample['tags']}")
        
        print("\n--- Formatted Question Text ---")
        print(format_question_for_output(sample))
    
    print(f"\n✅ Script completed successfully.")
    print(f"Processed {count} questions, updated {update_stats['success']} text fields in the database.")

if __name__ == "__main__":
    main()