#!/usr/bin/env python3
"""
Script to merge multiple MP3 files into a single file.
"""

import argparse
import os
import sys
from pathlib import Path


def merge_audio_files(input_files, output_file, silence_duration=500):
    """Merge multiple audio files into one using pydub."""
    try:
        from pydub import AudioSegment
    except ImportError:
        print("Error: pydub not installed")
        print("Install with: pip install pydub")
        print("\nAlso install ffmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt-get install ffmpeg")
        sys.exit(1)
    
    print(f"Merging {len(input_files)} audio files...")
    
    # Verify all input files exist
    for file in input_files:
        if not Path(file).exists():
            print(f"Error: File not found: {file}")
            sys.exit(1)
    
    combined = AudioSegment.empty()
    
    for idx, audio_file in enumerate(input_files, 1):
        print(f"  [{idx}/{len(input_files)}] Adding: {audio_file}")
        try:
            audio = AudioSegment.from_mp3(audio_file)
            combined += audio
            
            # Add silence between files (except after the last one)
            if idx < len(input_files) and silence_duration > 0:
                combined += AudioSegment.silent(duration=silence_duration)
                print(f"      Added {silence_duration}ms silence")
                
        except Exception as e:
            print(f"Error loading {audio_file}: {e}")
            sys.exit(1)
    
    # Get total duration
    duration_seconds = len(combined) / 1000
    duration_minutes = duration_seconds / 60
    
    print(f"\nExporting merged audio...")
    print(f"  Total duration: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")
    
    # Export the merged audio
    combined.export(output_file, format="mp3")
    
    # Get file size
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"  File size: {file_size_mb:.2f} MB")
    print(f"\n✓ Merged audio saved to: {output_file}")


def get_files_from_pattern(pattern):
    """Get list of files matching a glob pattern."""
    from glob import glob
    
    # Try the pattern as-is first
    files = sorted(glob(pattern))
    
    # If no files found and pattern doesn't include a path, try current directory
    if not files and '/' not in pattern and '\\' not in pattern:
        # Try with ./ prefix
        files = sorted(glob(f"./{pattern}"))
    
    if not files:
        print(f"Error: No files found matching pattern: {pattern}")
        print(f"Current directory: {os.getcwd()}")
        print("\nTip: Include the directory path in your pattern, e.g.:")
        print(f"  --pattern 'obsidian-to-audiobook/{pattern}'")
        sys.exit(1)
    
    return files


def main():
    parser = argparse.ArgumentParser(
        description='Merge multiple MP3 files into a single file.',
        epilog='''
Examples:
  # Merge specific files
  python 4_merge_mp3.py -i file1.mp3 file2.mp3 file3.mp3 -o output.mp3
  
  # Merge files using glob pattern
  python 4_merge_mp3.py --pattern "book_output_chunk_*.mp3" -o output.mp3
  
  # Merge with custom silence duration
  python 4_merge_mp3.py -i file1.mp3 file2.mp3 -o output.mp3 --silence 1000
  
  # Merge without silence between files
  python 4_merge_mp3.py -i file1.mp3 file2.mp3 -o output.mp3 --silence 0
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-i', '--input',
        nargs='+',
        help='Input MP3 files to merge (space-separated)'
    )
    input_group.add_argument(
        '-p', '--pattern',
        help='Glob pattern to match input files (e.g., "*.mp3" or "chunk_*.mp3")'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output MP3 file path'
    )
    parser.add_argument(
        '-s', '--silence',
        type=int,
        default=500,
        help='Silence duration between files in milliseconds (default: 500ms, use 0 for no silence)'
    )
    parser.add_argument(
        '--delete-input',
        action='store_true',
        help='Delete input files after successful merge'
    )
    
    args = parser.parse_args()
    
    # Get list of input files
    if args.input:
        input_files = args.input
    else:
        input_files = get_files_from_pattern(args.pattern)
    
    print(f"Input files ({len(input_files)}):")
    for file in input_files:
        file_size = os.path.getsize(file) / 1024  # KB
        print(f"  - {file} ({file_size:.1f} KB)")
    print()
    
    # Check if output file already exists
    if Path(args.output).exists():
        response = input(f"Output file '{args.output}' already exists. Overwrite? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            sys.exit(0)
    
    # Merge audio files
    merge_audio_files(input_files, args.output, args.silence)
    
    # Delete input files if requested
    if args.delete_input:
        print(f"\nDeleting {len(input_files)} input files...")
        for file in input_files:
            try:
                os.remove(file)
                print(f"  ✓ Deleted: {file}")
            except Exception as e:
                print(f"  ✗ Could not delete {file}: {e}")


if __name__ == '__main__':
    main()

