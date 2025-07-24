#!/usr/bin/env python3
"""
UH Hilo Course Metadata Extraction

This script processes the hilo_courses.json file and separates course descriptions
from metadata such as prerequisites, corequisites, class length, and semester offerings.
The metadata is extracted to a separate field, and the course description is cleaned.

Usage:
    python extract_hilo_metadata.py

Requirements:
    - google-generativeai
    - json
"""

import json
import re
import os
import google.generativeai as genai
from pathlib import Path

# Configure the Gemini API key
# Note: User will need to set their GOOGLE_API_KEY environment variable
api_key = os.environ.get('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Please set it with your Gemini API key.")

genai.configure(api_key=api_key)

# Define the Gemini model to use
model = genai.GenerativeModel('gemini-1.5-flash')

def load_json_data(file_path):
    """Load course data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json_data(data, file_path):
    """Save processed course data to JSON file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    print(f"Processed data saved to {file_path}")

def extract_metadata_patterns(course_desc):
    """
    Use regex patterns to extract common metadata patterns from course descriptions.
    Returns a tuple of (clean_description, metadata_dict)
    """
    metadata = {}
    
    # Extract prerequisites using regex
    prereq_pattern = r'(?:Pre|Prereq|Prerequisites?):\s*([^\.]+)\.?'
    prereq_match = re.search(prereq_pattern, course_desc, re.IGNORECASE)
    if prereq_match:
        metadata['prerequisites'] = prereq_match.group(1).strip()
    
    # Extract corequisites
    coreq_pattern = r'(?:Co-?req|Co-?requisites?):\s*([^\.]+)\.?'
    coreq_match = re.search(coreq_pattern, course_desc, re.IGNORECASE)
    if coreq_match:
        metadata['corequisites'] = coreq_match.group(1).strip()
    
    # Extract recommended preparation
    rec_pattern = r'(?:Rec Prep|Recommended Preparation|Recommended):\s*([^\.]+)\.?'
    rec_match = re.search(rec_pattern, course_desc, re.IGNORECASE)
    if rec_match:
        metadata['recommended_preparation'] = rec_match.group(1).strip()
    
    # Extract semester offered
    sem_pattern = r'(?:Semester[s]? Offered|Offered):\s*([^\.]+)\.?'
    sem_match = re.search(sem_pattern, course_desc, re.IGNORECASE)
    if sem_match:
        metadata['semester_offered'] = sem_match.group(1).strip()
    
    # Extract class hours/credits
    hours_pattern = r'(?:Class Hours|Credits):\s*([^\.]+)\.?'
    hours_match = re.search(hours_pattern, course_desc, re.IGNORECASE)
    if hours_match:
        metadata['class_hours'] = hours_match.group(1).strip()
        
    # Extract attributes (common in UH Hilo courses)
    attr_pattern = r'\(Attributes:\s*([^\)]+)\)'
    attr_match = re.search(attr_pattern, course_desc)
    if attr_match:
        metadata['attributes'] = attr_match.group(1).strip()
    
    # Clean the description by removing all identified metadata
    clean_desc = course_desc
    for pattern in [prereq_pattern, coreq_pattern, rec_pattern, sem_pattern, hours_pattern, attr_pattern]:
        clean_desc = re.sub(pattern, '', clean_desc, flags=re.IGNORECASE)
    
    # Clean up any double spaces and periods
    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
    clean_desc = re.sub(r'\.+', '.', clean_desc).strip()
    clean_desc = re.sub(r'\.\s*$', '', clean_desc).strip() + '.'
    
    return clean_desc, metadata

def process_with_gemini(course):
    """
    Use Gemini AI to process course descriptions that might have complex metadata patterns.
    """
    try:
        prompt = f"""
        I have a university course description that may contain metadata. Please separate the actual course description 
        from any metadata like prerequisites, corequisites, class hours, semester offerings, etc.
        
        Course: {course['course_prefix']} {course['course_number']} - {course['course_title']}
        Description: {course['course_desc']}
        
        Return a JSON object with two fields:
        1. "clean_description": The course description without any metadata
        2. "metadata": An object containing all extracted metadata fields and their values
        
        If no metadata exists, return an empty object for "metadata".
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        if '```json' in response_text:
            # Extract JSON between markdown code blocks if present
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            json_str = response_text[json_start:json_end].strip()
        else:
            # Otherwise, try to find a JSON object in the text
            json_str = response_text.strip()
            
        result = json.loads(json_str)
        return result.get('clean_description', course['course_desc']), result.get('metadata', {})
    
    except Exception as e:
        print(f"Error processing with Gemini: {e}")
        print(f"Falling back to pattern extraction for {course['course_prefix']} {course['course_number']}")
        return extract_metadata_patterns(course['course_desc'])

def process_courses(courses):
    """Process each course to extract metadata from descriptions."""
    total = len(courses)
    processed_courses = []
    
    for i, course in enumerate(courses):
        if (i + 1) % 50 == 0:
            print(f"Processing course {i+1}/{total}")
        
        # First try pattern-based extraction
        clean_desc, metadata_dict = extract_metadata_patterns(course['course_desc'])
        
        # If pattern extraction didn't find much, use Gemini
        if len(metadata_dict) <= 1:
            clean_desc, metadata_dict = process_with_gemini(course)
        
        # Create a copy of the course with the updated fields
        updated_course = course.copy()
        updated_course['course_desc'] = clean_desc
        updated_course['metadata'] = metadata_dict
        
        processed_courses.append(updated_course)
    
    return processed_courses

def main():
    # File paths
    base_dir = Path(__file__).parent
    input_file = base_dir / "University of Hawaii Hilo" / "hilo_courses.json"
    output_file = base_dir / "University of Hawaii Hilo" / "hilo_courses_processed.json"
    
    # Load course data
    print(f"Loading course data from {input_file}")
    courses = load_json_data(input_file)
    print(f"Found {len(courses)} courses")
    
    # Process courses
    print("Processing courses...")
    processed_courses = process_courses(courses)
    
    # Save processed data
    save_json_data(processed_courses, output_file)
    print("Processing complete!")

if __name__ == "__main__":
    main()
