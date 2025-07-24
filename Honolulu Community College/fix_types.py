#!/usr/bin/env python3
"""
This script reads the University of Hawaii-West Oahu 'courses_extracted.json' file and cleans the data:
1. Converts all properties to strings except 'inst_ipeds'
2. Converts 'inst_ipeds' to integer
3. Ensures 'metadata' is a single string (converting from object if necessary)
"""

import json
import os
from datetime import datetime

def clean_json_data(input_filepath, output_filepath):
    """
    Reads JSON data, cleans fields according to requirements, and saves to a new file.
    
    Args:
        input_filepath (str): Path to the input JSON file.
        output_filepath (str): Path to save the cleaned JSON file.
    """
    print(f"Reading data from {input_filepath}...")
    
    # Read the input JSON file
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False
    
    # Make sure we have top-level metadata and courses array
    if 'courses' not in data:
        print("Error: No 'courses' array found in JSON data")
        return False
    
    # Count original entries
    original_count = len(data['courses'])
    print(f"Processing {original_count} course entries...")
    
    # Clean each course entry
    for course in data['courses']:
        # Convert num_units to string
        if 'num_units' in course and not isinstance(course['num_units'], str):
            course['num_units'] = str(course['num_units'])
        
        # Convert inst_ipeds to integer
        if 'inst_ipeds' in course:
            try:
                course['inst_ipeds'] = int(course['inst_ipeds'])
            except ValueError as e:
                print(f"Warning: Could not convert inst_ipeds to integer for {course.get('course_prefix', '')}{course.get('course_number', '')}: {e}")
        
        # Convert metadata from dictionary to string if it's an object
        if 'metadata' in course and isinstance(course['metadata'], dict):
            metadata_parts = []
            
            # Add cross_list if available
            if 'cross_list' in course['metadata'] and course['metadata']['cross_list']:
                metadata_parts.append(f"Cross-list: {course['metadata']['cross_list']}")
            
            # Add prerequisites if available
            if 'prerequisites' in course['metadata'] and course['metadata']['prerequisites']:
                metadata_parts.append(f"Pre: {course['metadata']['prerequisites']}")
            
            # Add lecture hours if available
            if 'lecture_hours' in course['metadata'] and course['metadata']['lecture_hours']:
                metadata_parts.append(f"Lecture Hours: {course['metadata']['lecture_hours']}")
            
            # Add lab hours if available
            if 'lab_hours' in course['metadata'] and course['metadata']['lab_hours']:
                metadata_parts.append(f"Lab Hours: {course['metadata']['lab_hours']}")
            
            # Join all parts with semicolons
            if metadata_parts:
                course['metadata'] = "; ".join(metadata_parts)
            else:
                course['metadata'] = ""
    
    # Save the cleaned data to the output file
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Cleaned data saved to {output_filepath}")
        print(f"Processed {original_count} entries")
        return True
    except Exception as e:
        print(f"Error writing to output file: {e}")
        return False

if __name__ == "__main__":
    # Define file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, "courses_extracted.json")
    output_file = os.path.join(current_dir, "honolulucc_courses.json")
    
    # Process the file
    start_time = datetime.now()
    success = clean_json_data(input_file, output_file)
    end_time = datetime.now()
    
    if success:
        print(f"Process completed in {end_time - start_time}")
    else:
        print("Process failed.")
