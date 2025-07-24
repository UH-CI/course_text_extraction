#!/usr/bin/env python3
"""
This script combines all JSON files in the directory and its subdirectories
into a single CSV file. It assumes each JSON file contains an array of course objects
with fields like course_prefix, course_number, course_title, etc.
"""

import os
import json
import csv
import argparse
from pathlib import Path


def find_json_files(directory):
    """Find all JSON files in the given directory and its subdirectories."""
    json_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files


def load_json_data(json_file):
    """Load data from a JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Add source file information to each record
            source_file = os.path.basename(json_file)
            for item in data:
                if isinstance(item, dict):
                    item['source_file'] = source_file
            return data
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {json_file}. Skipping.")
        return []
    except Exception as e:
        print(f"Error reading {json_file}: {str(e)}. Skipping.")
        return []


def get_all_fields(data_list):
    """Extract all unique field names from all records."""
    fields = set()
    for data in data_list:
        for item in data:
            if isinstance(item, dict):
                fields.update(item.keys())
    return sorted(list(fields))


def write_to_csv(data_list, output_file, fields=None):
    """Write combined data to CSV file."""
    if not data_list:
        print("No data to write.")
        return

    # Flatten all data into a single list
    all_items = []
    for data in data_list:
        if isinstance(data, list):
            all_items.extend(data)
        else:
            all_items.append(data)

    # Get all fields if not provided
    if not fields:
        fields = get_all_fields([all_items])

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            
            # Write each item as a row
            for item in all_items:
                if isinstance(item, dict):
                    writer.writerow(item)
                else:
                    print(f"Skipping non-dictionary item: {item}")
    except Exception as e:
        print(f"Error writing to {output_file}: {str(e)}")


def main():
    """Main function to combine JSON files into a CSV."""
    parser = argparse.ArgumentParser(description='Combine JSON files into a single CSV file.')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Directory to search for JSON files (default: current directory)')
    parser.add_argument('--output', '-o', default='combined_courses.csv',
                        help='Output CSV file name (default: combined_courses.csv)')
    parser.add_argument('--recursive', '-r', action='store_true',
                        help='Search recursively in subdirectories')
    
    args = parser.parse_args()
    
    # Convert to Path object for better path handling
    directory = Path(args.directory)
    
    print(f"Searching for JSON files in {directory}...")
    json_files = find_json_files(directory) if args.recursive else [
        str(f) for f in directory.glob('*.json')
    ]
    
    print(f"Found {len(json_files)} JSON files.")
    
    if not json_files:
        print("No JSON files found. Exiting.")
        return
    
    # Load data from all JSON files
    all_data = []
    for json_file in json_files:
        print(f"Loading {json_file}...")
        data = load_json_data(json_file)
        if data:
            all_data.append(data)
    
    # Write combined data to CSV
    output_file = args.output
    print(f"Writing combined data to {output_file}...")
    write_to_csv(all_data, output_file)
    print(f"Done! Combined data written to {output_file}.")


if __name__ == "__main__":
    main()
