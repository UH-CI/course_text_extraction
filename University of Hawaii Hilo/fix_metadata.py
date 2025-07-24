#!/usr/bin/env python3
"""
This script reads the University of Hawaii-Hilo 'hilo_courses_processed.json' file and converts metadata:
1. Transforms the metadata objects into a single string format
2. Preserves all other data as is
"""

import json
import os
from datetime import datetime

def convert_metadata_to_string(input_filepath, output_filepath):
    """
    Reads JSON data, converts metadata objects to strings, and saves to a new file.
    
    Args:
        input_filepath (str): Path to the input JSON file.
        output_filepath (str): Path to save the converted JSON file.
    """
    print(f"Reading data from {input_filepath}...")
    
    # Read the input JSON file
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False
    
    # Count original entries
    original_count = len(data)
    print(f"Processing {original_count} course entries...")
    
    # Convert metadata for each course entry
    for course in data:
        # Check if metadata exists and is a dictionary
        if 'metadata' in course and isinstance(course['metadata'], dict):
            # Build a string from metadata key-value pairs
            metadata_parts = []
            
            # Sort keys for consistent output
            for key, value in sorted(course['metadata'].items()):
                if value:  # Only include non-empty values
                    metadata_parts.append(f"{key}: {value}")
            
            # Join all parts with semicolons
            if metadata_parts:
                course['metadata'] = "; ".join(metadata_parts)
            else:
                course['metadata'] = ""
        
        # Ensure other fields are properly formatted too
        # Convert num_units to string if it's not already
        if 'num_units' in course and not isinstance(course['num_units'], str):
            course['num_units'] = str(course['num_units'])
        
        # Convert inst_ipeds to integer if it's not already
        if 'inst_ipeds' in course and not isinstance(course['inst_ipeds'], int):
            try:
                course['inst_ipeds'] = int(course['inst_ipeds'])
            except (ValueError, TypeError):
                print(f"Warning: Could not convert inst_ipeds to integer for {course.get('course_prefix', '')}{course.get('course_number', '')}")
    
    # Save the converted data to the output file
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Converted data saved to {output_filepath}")
        print(f"Processed {original_count} entries")
        return True
    except Exception as e:
        print(f"Error writing to output file: {e}")
        return False

if __name__ == "__main__":
    # Define file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, "hilo_courses_processed.json")
    output_file = os.path.join(current_dir, "..", "hilo_courses.json")
    
    # Process the file
    start_time = datetime.now()
    success = convert_metadata_to_string(input_file, output_file)
    end_time = datetime.now()
    
    if success:
        print(f"Process completed in {end_time - start_time}")
    else:
        print("Process failed.")
