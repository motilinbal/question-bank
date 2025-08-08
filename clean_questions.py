#!/usr/bin/env python3
"""
Script to extract and display clean text from a single medical question.
This script connects to the MongoDB database and extracts question data
without making any changes to the database.
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
    formatted_text = f"        Question: {clean_data['question']}\n\n"
    formatted_text += "        Options:\n"
    
    # Sort choices by ID to ensure consistent order (A, B, C, D, etc.)
    sorted_choices = sorted(clean_data['choices'], key=lambda x: x['id'])
    
    for choice in sorted_choices:
        formatted_text += f"        {choice['id']}) {choice['text']}\n"
    
    formatted_text += f"\n        Explanation: {clean_data['explanation']}"
    
    return formatted_text

def main():
    """Main function to connect to database and process multiple questions."""
    # Number of questions to fetch
    num_questions = 5000
    output_file = "cleaned_questions.txt"
    
    print("Connecting to database...")
    
    # Get the Questions collection
    questions_collection = db_client.get_collection("Questions")
    
    if questions_collection is None:
        print("❌ Failed to connect to Questions collection")
        return
    
    # Get multiple question documents
    print(f"Fetching {num_questions} questions from the database...")
    question_docs = questions_collection.find().limit(num_questions)
    
    # Convert cursor to list to check if we got any results
    question_docs_list = list(question_docs)
    
    if not question_docs_list:
        print("❌ No questions found in the database")
        return
    
    print(f"✅ Successfully fetched {len(question_docs_list)} questions")
    
    # Process all question documents
    print("\n--- Processing Question Data ---")
    cleaned_questions = []
    
    for i, question_doc in enumerate(question_docs_list):
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(question_docs_list)} questions...")
        
        clean_data = process_question_document(question_doc)
        cleaned_questions.append(clean_data)
    
    # Save the cleaned questions to a file in the specified format
    print(f"\n--- Saving {len(cleaned_questions)} cleaned questions to {output_file} ---")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, clean_data in enumerate(cleaned_questions):
                # Format each question according to the specified template
                formatted_question = format_question_for_output(clean_data)
                
                # Write the formatted question to the file
                f.write(formatted_question)
                
                # Add a separator between questions (except for the last one)
                if i < len(cleaned_questions) - 1:
                    f.write("\n\n" + "="*80 + "\n\n")
        
        print(f"✅ Successfully saved cleaned questions to {output_file}")
    except Exception as e:
        print(f"❌ Failed to save questions to file: {e}")
        return
    
    # Display a sample of the clean data
    if cleaned_questions:
        sample = cleaned_questions[0]
        print(f"\n--- Sample of Cleaned Question Data (ID: {sample['id']}) ---")
        print(f"Name: {sample['name']}")
        print(f"Source: {sample['source']}")
        print(f"Tags: {sample['tags']}")
        
        print("\n--- Formatted Question Text ---")
        print(format_question_for_output(sample))
    
    print(f"\n✅ Script completed successfully. Processed {len(cleaned_questions)} questions and saved to {output_file}.")
    print("No changes were made to the database.")

if __name__ == "__main__":
    main()