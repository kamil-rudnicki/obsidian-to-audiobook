#!/usr/bin/env python3
"""
Script to process markdown files and transform them using AI into book-style text.
"""

import argparse
import csv
import os
import random
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests
import time

# Load environment variables
load_dotenv()


def read_csv_and_filter(input_file, column, value):
    """Read CSV file and filter rows based on column and value."""
    filtered_rows = []
    
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Check if column exists
        if column not in reader.fieldnames:
            raise ValueError(f"Column '{column}' not found in CSV. Available columns: {reader.fieldnames}")
        
        for row in reader:
            if row.get(column) == value:
                filtered_rows.append(row)
    
    return filtered_rows


def read_markdown_file(folder, relative_path):
    """Read the content of a markdown file."""
    file_path = Path(folder) / relative_path
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def call_openrouter_api(content, api_key, model, prompt):
    """Call OpenRouter API to transform the content."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "temperature": 1.5,
        "messages": [
            {
                "role": "user",
                "content": f"{prompt}\n\n---\n\n{content}"
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def get_already_processed_files(output_file):
    """Get list of files that have already been processed in the output file."""
    if not Path(output_file).exists():
        return set()
    
    processed_files = set()
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Look for lines starting with "# " which are file headers
                if line.startswith("# "):
                    file_name = line[2:].strip()
                    processed_files.add(file_name)
    except Exception as e:
        print(f"Warning: Could not read output file: {e}")
        return set()
    
    return processed_files


def append_to_output_file(output_file, file_name, ai_response):
    """Append the AI response to the output file."""
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(f"# {file_name}\n\n")
        f.write(ai_response)
        f.write("\n\n")


def main():
    parser = argparse.ArgumentParser(
        description='Process markdown files and transform them using AI into book-style text.'
    )
    parser.add_argument(
        '--input_file',
        required=True,
        help='Input CSV file path'
    )
    parser.add_argument(
        '--folder',
        required=True,
        help='Folder where original notes are located'
    )
    parser.add_argument(
        '--column',
        required=True,
        help='Column name to filter md files'
    )
    parser.add_argument(
        '--value',
        required=True,
        help='Value in that column to filter notes'
    )
    parser.add_argument(
        '--output_file',
        required=True,
        help='Output markdown file path'
    )
    parser.add_argument(
        '--prompt',
        help='Prompt to use for AI transformation'
    )
    parser.add_argument(
        '--randomize',
        action='store_true',
        help='Randomize the order of notes before processing'
    )
    
    args = parser.parse_args()
    
    # Validate prompt is provided
    if not args.prompt or not args.prompt.strip():
        default_prompt = "Can you make a book text from text below? Make random choice about the writing style, from authors starting from greek philosophy to modern day. try to write something about every concept in the text. Write in polish. Don't use any formatting. Only add new lines. Write in engaging and easy way. If possible write stories. Sometimes add narrations and comments. If there is nothing to write about, write nothing."
        print(f"Error: --prompt is required")
        print(f"Suggested prompt: {default_prompt}")
        sys.exit(1)
    
    # Get API key and model from environment
    api_key = os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPENROUTER_MODEL')
    
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment variables")
        sys.exit(1)
    
    if not model:
        print("Error: OPENROUTER_MODEL not found in environment variables")
        sys.exit(1)
    
    print(f"Using model: {model}")
    print(f"Reading CSV file: {args.input_file}")
    
    # Filter CSV rows
    filtered_rows = read_csv_and_filter(args.input_file, args.column, args.value)
    print(f"Found {len(filtered_rows)} files matching {args.column}={args.value}")
    
    if not filtered_rows:
        print("No files to process. Exiting.")
        sys.exit(0)
    
    # Randomize order if requested
    if args.randomize:
        random.shuffle(filtered_rows)
        print("Randomized order of notes")
    
    # Check which files have already been processed
    already_processed = get_already_processed_files(args.output_file)
    if already_processed:
        print(f"Found {len(already_processed)} files already processed in output file")
    
    # Create output file if it doesn't exist
    if not Path(args.output_file).exists():
        Path(args.output_file).write_text('', encoding='utf-8')
    
    print(f"Output will be written to: {args.output_file}")
    
    # Process each file
    for idx, row in enumerate(filtered_rows, 1):
        file_name = row['file_name']
        relative_path = row['relative_path']
        t_start = datetime.now().strftime("%H:%M:%S")
        
        prefix = f"[{t_start}] [{idx}/{len(filtered_rows)}] {file_name}"
        
        # Check if already processed
        if file_name in already_processed:
            print(f"{prefix} | Already processed, skipping")
            continue
        
        try:
            # Read the markdown file
            content = read_markdown_file(args.folder, relative_path)
            
            if not content.strip():
                print(f"{prefix} | Skipping empty file")
                continue
            
            # Print initial status without newline
            print(f"{prefix} ({len(content)} chars) | Sending to AI...", end="", flush=True)
            
            # Call AI API
            ai_response = call_openrouter_api(content, api_key, model, args.prompt)
            
            # Append to output file
            append_to_output_file(args.output_file, file_name, ai_response)
            
            # Finish the line
            print(f" done ({len(ai_response)} chars) ✓")
            
            # Small delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"\n{prefix} ✗ Error processing {file_name}: {e}")
            continue
    
    print(f"\n✓ Processing complete! Output saved to: {args.output_file}")


if __name__ == '__main__':
    main()

