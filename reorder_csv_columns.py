#!/usr/bin/env python3
"""
Script to reorder columns in CSV files to a standardized format.

Target column order:
course_prefix, course_number, course_title, course_desc, num_units, dept_name, inst_ipeds, metadata
"""

import csv
import os
import glob
import pandas as pd


def reorder_csv_columns(input_file, output_file=None):
    """
    Reorder columns in a CSV file to the standardized format.
    If output_file is not provided, the input file will be overwritten.
    """
    # Define the desired column order
    desired_order = [
        'course_prefix',
        'course_number',
        'course_title',
        'course_desc',
        'num_units',
        'dept_name',
        'inst_ipeds',
        'metadata'
    ]
    
    # Read the CSV file with pandas
    df = pd.read_csv(input_file, quotechar='"', escapechar='\\')
    
    # Ensure all expected columns are present
    missing_cols = set(desired_order) - set(df.columns)
    if missing_cols:
        raise ValueError(f"File {input_file} is missing columns: {missing_cols}")
    
    # Reorder the columns
    df = df[desired_order]
    
    # Determine output path
    output_path = output_file if output_file else input_file
    
    # Save the reordered CSV
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_MINIMAL)
    
    print(f"Processed {input_file} -> {output_path}")


def main():
    """
    Main function to process all CSV files in the specified directories.
    """
    # Base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to combined CSV
    combined_csv_path = os.path.join(base_dir, 'data', 'combined_courses.csv')
    
    # Path to individual CSVs directory
    individual_dir = os.path.join(base_dir, 'data', 'individual')
    
    # Process combined CSV
    if os.path.exists(combined_csv_path):
        print(f"Processing combined CSV file: {combined_csv_path}")
        reorder_csv_columns(combined_csv_path)
    else:
        print(f"Warning: Combined CSV file not found at {combined_csv_path}")
    
    # Process individual CSVs
    individual_csv_files = glob.glob(os.path.join(individual_dir, '*.csv'))
    
    if individual_csv_files:
        print(f"Processing {len(individual_csv_files)} individual CSV files...")
        for csv_file in individual_csv_files:
            reorder_csv_columns(csv_file)
    else:
        print(f"Warning: No individual CSV files found in {individual_dir}")

    print("All CSV files have been processed.")


if __name__ == "__main__":
    main()
