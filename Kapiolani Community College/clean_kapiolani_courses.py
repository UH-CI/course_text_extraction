#!/usr/bin/env python3
"""
This script reads the kapiolani_courses.json file and produces a new JSON file
with the 'source_url' and 'extraction_timestamp' fields removed from every entry.
"""

import json
import os
from datetime import datetime

def clean_json_data(input_filepath, output_filepath):
    """
    Reads JSON data, removes specified fields, and saves to a new file.
    
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
    
    # Remove specified fields from each entry
    cleaned_data = []
    for entry in data:
        # Create a new entry without the specified fields
        clean_entry = {k: v for k, v in entry.items() 
                       if k not in ['source_url', 'extraction_timestamp']}
        cleaned_data.append(clean_entry)
    
    # Save the cleaned data to the output file
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        print(f"Cleaned data saved to {output_filepath}")
        print(f"Removed 'source_url' and 'extraction_timestamp' from {original_count} entries")
        return True
    except Exception as e:
        print(f"Error writing to output file: {e}")
        return False

if __name__ == "__main__":
    # Define file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, "kapiolani_courses.json")
    output_file = os.path.join(current_dir, "kapiolani_courses_clean.json")
    
    # Process the file
    start_time = datetime.now()
    success = clean_json_data(input_file, output_file)
    end_time = datetime.now()
    
    if success:
        print(f"Process completed in {end_time - start_time}")
    else:
        print("Process failed.")
