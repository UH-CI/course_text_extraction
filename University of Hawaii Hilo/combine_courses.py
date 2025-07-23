#!/usr/bin/env python3
"""
Script to combine UH Hilo graduate and undergraduate course JSON files
and remove source_url and extraction_timestamp fields.
"""

import json
import os

def load_json_file(filepath):
    """Load JSON data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found - {filepath}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath} - {e}")
        return []
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def clean_course_data(courses):
    """Remove source_url and extraction_timestamp from course records."""
    cleaned_courses = []
    for course in courses:
        # Create a copy of the course without the unwanted fields
        cleaned_course = {k: v for k, v in course.items() 
                         if k not in ['source_url', 'extraction_timestamp']}
        cleaned_courses.append(cleaned_course)
    return cleaned_courses

def save_json_file(data, filepath):
    """Save data to JSON file with proper formatting."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(data)} records to {filepath}")
        return True
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")
        return False

def main():
    # Define file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    graduate_file = os.path.join(script_dir, 'hilo_courses_graduate.json')
    undergraduate_file = os.path.join(script_dir, 'hilo_courses_undergraduate.json')
    output_file = os.path.join(script_dir, 'hilo_courses_combined.json')
    
    print("UH Hilo Course Data Combiner")
    print("=" * 40)
    
    # Load graduate courses
    print(f"Loading graduate courses from: {graduate_file}")
    graduate_courses = load_json_file(graduate_file)
    print(f"Loaded {len(graduate_courses)} graduate courses")
    
    # Load undergraduate courses
    print(f"Loading undergraduate courses from: {undergraduate_file}")
    undergraduate_courses = load_json_file(undergraduate_file)
    print(f"Loaded {len(undergraduate_courses)} undergraduate courses")
    
    # Check if files were loaded successfully
    if not graduate_courses and not undergraduate_courses:
        print("Error: No course data loaded. Exiting.")
        return
    
    # Clean the data (remove source_url and extraction_timestamp)
    print("\nCleaning course data...")
    cleaned_graduate = clean_course_data(graduate_courses)
    cleaned_undergraduate = clean_course_data(undergraduate_courses)
    
    # Combine the courses
    print("Combining course data...")
    combined_courses = cleaned_graduate + cleaned_undergraduate
    
    # Sort by course prefix and number for better organization
    print("Sorting combined data...")
    combined_courses.sort(key=lambda x: (x.get('course_prefix', ''), x.get('course_number', '')))
    
    # Save combined data
    print(f"\nSaving combined data to: {output_file}")
    if save_json_file(combined_courses, output_file):
        print(f"\n✅ Success! Combined {len(combined_courses)} total courses:")
        print(f"   - Graduate courses: {len(cleaned_graduate)}")
        print(f"   - Undergraduate courses: {len(cleaned_undergraduate)}")
        print(f"   - Output file: {output_file}")
    else:
        print("❌ Failed to save combined data")

if __name__ == "__main__":
    main()
