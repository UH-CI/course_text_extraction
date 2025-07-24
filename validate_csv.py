#!/usr/bin/env python3
"""
This script validates the combined CSV file and runs statistics on it
to ensure it was correctly created.
"""

import pandas as pd
import sys
import os
from collections import Counter

def validate_csv(csv_file):
    """Validate that the CSV file can be read properly and generate statistics."""
    try:
        print(f"Reading CSV file: {csv_file}")
        df = pd.read_csv(csv_file, low_memory=False)
        print(f"✅ CSV file is valid and can be properly read.")
        return df
    except Exception as e:
        print(f"❌ Error reading CSV file: {str(e)}")
        return None

def general_stats(df):
    """Generate general statistics about the CSV."""
    print("\n===== GENERAL STATISTICS =====")
    print(f"Total records: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Column names: {', '.join(df.columns)}")

def column_stats(df):
    """Generate statistics for each column."""
    print("\n===== COLUMN STATISTICS =====")
    for column in df.columns:
        null_count = df[column].isnull().sum()
        null_percentage = (null_count / len(df)) * 100
        
        print(f"\nColumn: {column}")
        print(f"  - Non-null values: {len(df) - null_count} ({100 - null_percentage:.2f}%)")
        print(f"  - Null values: {null_count} ({null_percentage:.2f}%)")
        
        # For non-text columns with fewer than 30 unique values, show value distribution
        if df[column].dtype != 'object' or (len(df[column].unique()) < 30):
            value_counts = df[column].value_counts().head(10)
            if not value_counts.empty:
                print("  - Top values:")
                for val, count in value_counts.items():
                    print(f"      {val}: {count} ({count/len(df)*100:.2f}%)")

def source_file_stats(df):
    """Generate statistics about source files."""
    if 'source_file' not in df.columns:
        print("\n❌ No 'source_file' column found.")
        return
        
    print("\n===== SOURCE FILE STATISTICS =====")
    source_counts = df['source_file'].value_counts()
    total_records = len(df)
    
    print(f"Total source files: {len(source_counts)}")
    for source, count in source_counts.items():
        print(f"  - {source}: {count} records ({count/total_records*100:.2f}%)")

def course_stats(df):
    """Generate statistics specific to course data."""
    print("\n===== COURSE DATA STATISTICS =====")
    
    # Check for course_prefix
    if 'course_prefix' in df.columns:
        prefix_counts = df['course_prefix'].value_counts().head(15)
        print(f"Top 15 course prefixes:")
        for prefix, count in prefix_counts.items():
            print(f"  - {prefix}: {count} courses")
    
    # Check for dept_name
    if 'dept_name' in df.columns:
        dept_counts = df['dept_name'].value_counts().head(15)
        print(f"\nTop 15 departments:")
        for dept, count in dept_counts.items():
            print(f"  - {dept}: {count} courses")
    
    # Check for inst_ipeds
    if 'inst_ipeds' in df.columns:
        inst_counts = df['inst_ipeds'].value_counts()
        print(f"\nInstitution IPEDS distribution:")
        for inst, count in inst_counts.items():
            print(f"  - {inst}: {count} courses ({count/len(df)*100:.2f}%)")

def main():
    """Main function to validate CSV and run statistics."""
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = 'combined_courses.csv'
    
    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        return
    
    df = validate_csv(csv_file)
    if df is None:
        return
    
    general_stats(df)
    column_stats(df)
    source_file_stats(df)
    course_stats(df)
    
    print("\nValidation complete!")

if __name__ == "__main__":
    main()
