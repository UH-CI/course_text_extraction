#!/usr/bin/env python3
"""
This script converts each JSON file in the directory and its subdirectories
into individual CSV files in the data/individual directory.
"""

import os
import json
import csv
import argparse
from pathlib import Path


def find_json_files(directory, recursive=True):
    """Find all JSON files in the given directory and optionally its subdirectories."""
    json_files = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            if file.endswith('.json'):
                json_files.append(os.path.join(directory, file))
    return json_files


def load_json_data(json_file):
    """Load data from a JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {json_file}. Skipping.")
        return []
    except Exception as e:
        print(f"Error reading {json_file}: {str(e)}. Skipping.")
        return []


def get_all_fields(data):
    """Extract all unique field names from all records."""
    fields = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                fields.update(item.keys())
    return sorted(list(fields))


def convert_json_to_csv(json_file, output_dir):
    """Convert a JSON file to CSV and save it to the output directory."""
    # Create output filename
    base_name = os.path.splitext(os.path.basename(json_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}.csv")
    
    # Load JSON data
    data = load_json_data(json_file)
    
    if not data:
        print(f"No data found in {json_file}. Skipping.")
        return
    
    # Get all fields
    fields = get_all_fields(data)
    
    if not fields:
        print(f"No fields found in {json_file}. Skipping.")
        return
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            
            # Write each item as a row
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        writer.writerow(item)
                    else:
                        print(f"Skipping non-dictionary item: {item}")
            else:
                print(f"Data in {json_file} is not a list. Skipping.")
        
        print(f"Converted {json_file} to {output_file}")
        return True
    except Exception as e:
        print(f"Error writing to {output_file}: {str(e)}")
        return False


def ensure_directory_exists(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")


def main():
    """Main function to convert JSON files to CSV files."""
    parser = argparse.ArgumentParser(description='Convert individual JSON files to CSV files.')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Directory to search for JSON files (default: current directory)')
    parser.add_argument('--output', '-o', default='data/individual',
                        help='Output directory for CSV files (default: data/individual)')
    parser.add_argument('--recursive', '-r', action='store_true', default=True,
                        help='Search recursively in subdirectories (default: True)')
    
    args = parser.parse_args()
    
    # Convert to Path objects for better path handling
    input_directory = Path(args.directory)
    output_directory = Path(args.output)
    
    # Ensure output directory exists
    ensure_directory_exists(output_directory)
    
    print(f"Searching for JSON files in {input_directory}...")
    json_files = find_json_files(input_directory, args.recursive)
    
    print(f"Found {len(json_files)} JSON files.")
    
    if not json_files:
        print("No JSON files found. Exiting.")
        return
    
    # Convert each JSON file to CSV
    success_count = 0
    for json_file in json_files:
        print(f"Converting {json_file}...")
        if convert_json_to_csv(json_file, output_directory):
            success_count += 1
    
    print(f"Done! Successfully converted {success_count} out of {len(json_files)} JSON files to CSV format.")
    print(f"CSV files are saved in {output_directory}")


if __name__ == "__main__":
    main()
