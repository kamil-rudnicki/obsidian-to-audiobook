#!/usr/bin/env python3
"""
Script to scan a folder for .md files and create a CSV with file information.
"""

import argparse
import csv
import os
from pathlib import Path


def count_chars_in_file(file_path):
    """Count the number of characters in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return len(content)
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return 0


def scan_markdown_files(source_folder):
    """Scan the source folder for all .md files and collect their information."""
    source_path = Path(source_folder)
    
    if not source_path.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_folder}")
    
    if not source_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_folder}")
    
    markdown_files = []
    
    # Walk through all files in the directory tree
    for md_file in source_path.rglob("*.md"):
        if md_file.is_file():
            file_name = md_file.name
            relative_path = md_file.relative_to(source_path)
            num_chars = count_chars_in_file(md_file)
            
            markdown_files.append({
                'file_name': file_name,
                'relative_path': str(relative_path),
                'number_of_chars': num_chars
            })
    
    return markdown_files


def write_csv(output_file, data):
    """Write the collected data to a CSV file."""
    if not data:
        print("Warning: No markdown files found.")
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['file_name', 'relative_path', 'number_of_chars']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Successfully wrote {len(data)} files to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Scan a folder for .md files and create a CSV with file information.'
    )
    parser.add_argument(
        '--source_folder',
        required=True,
        help='Source folder to scan for .md files'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output CSV file path'
    )
    
    args = parser.parse_args()
    
    print(f"Scanning folder: {args.source_folder}")
    markdown_files = scan_markdown_files(args.source_folder)
    
    print(f"Found {len(markdown_files)} markdown files")
    write_csv(args.output, markdown_files)


if __name__ == '__main__':
    main()

