#!/usr/bin/env python3
"""
This script reads the University of Hawaii Maui 'courses_extracted.json' file and cleans the data:
1. Converts metadata from dictionary to formatted string
2. Converts num_units to string
3. Converts inst_ipeds to integer
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
    
    # Count original entries
    original_count = len(data)
    print(f"Processing {original_count} course entries...")
    
    # Clean each entry
    for entry in data:
        # Convert num_units to string
        if 'num_units' in entry:
            entry['num_units'] = str(entry['num_units'])
        
        # Convert inst_ipeds to integer
        if 'inst_ipeds' in entry:
            try:
                entry['inst_ipeds'] = int(entry['inst_ipeds'])
            except ValueError as e:
                print(f"Warning: Could not convert inst_ipeds to integer for {entry.get('course_prefix', '')}{entry.get('course_number', '')}: {e}")
        
        # Convert metadata from dictionary to string
        if 'metadata' in entry and isinstance(entry['metadata'], dict):
            metadata_parts = []
            
            # Format lecture hours if available
            if 'lecture_hours' in entry['metadata']:
                lecture_hours = entry['metadata'].get('lecture_hours')
                if lecture_hours:
                    metadata_parts.append(f"Class Hours: {int(lecture_hours)//15} lecture")
            
            # Add semester offered if available (default placeholder since it's not in the input)
            # This is just a placeholder - actual semester data isn't in the input
            
            # Add prerequisites if available
            if 'prerequisites' in entry['metadata'] and entry['metadata']['prerequisites']:
                metadata_parts.append(f"Prerequisites: {entry['metadata']['prerequisites']}")
            
            # Join all parts with semicolons
            entry['metadata'] = "; ".join(metadata_parts)
    
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
    output_file = os.path.join(current_dir, "maui_courses_clean.json")
    
    # Process the file
    start_time = datetime.now()
    success = clean_json_data(input_file, output_file)
    end_time = datetime.now()
    
    if success:
        print(f"Process completed in {end_time - start_time}")
    else:
        print("Process failed.")