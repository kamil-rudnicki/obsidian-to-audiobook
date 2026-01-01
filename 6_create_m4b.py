#!/usr/bin/env python3
"""
Script to combine audio files into an M4B audiobook with chapters.
Requires ffmpeg and ffprobe to be installed.
"""

import argparse
import os
import sys
import subprocess
import re
from pathlib import Path
from datetime import datetime

def check_dependencies():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(['ffprobe', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg or ffprobe not found.")
        print("Please install ffmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt-get install ffmpeg")
        return False

def get_audio_duration(file_path):
    """Get duration of audio file in seconds using ffprobe."""
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        str(file_path)
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        return 0

def clean_title(filename):
    """Convert filename to clean title."""
    # Remove extension
    name = Path(filename).stem
    
    # Remove ordering numbers (e.g., "01_Chapter" -> "Chapter")
    # But only if it looks like an index (starts with digits followed by separator)
    name = re.sub(r'^\d+[\s_-]+', '', name)
    
    # Replace underscores/dashes with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    
    # Capitalize words
    return name.title()

def generate_ffmpeg_metadata(chapters, title, author):
    """Generate FFMETADATA1 content."""
    content = [";FFMETADATA1"]
    if title:
        content.append(f"title={title}")
    if author:
        content.append(f"artist={author}")
        content.append(f"album_artist={author}")
    
    content.append(f"album={title or 'Audiobook'}")
    content.append("genre=Audiobook")
    content.append(f"date={datetime.now().year}")
    content.append("")

    for chapter in chapters:
        content.append("[CHAPTER]")
        content.append("TIMEBASE=1/1000") # Milliseconds
        content.append(f"START={int(chapter['start'] * 1000)}")
        content.append(f"END={int(chapter['end'] * 1000)}")
        content.append(f"title={chapter['title']}")
        content.append("")
        
    return "\n".join(content)

def create_m4b(input_files, output_file, title=None, author=None, cover_image=None, bitrate='64k'):
    """Create M4B file from input files."""
    
    if not input_files:
        print("No input files provided.")
        return False

    print(f"Processing {len(input_files)} files...")
    
    # 1. Analyze files and build chapters
    chapters = []
    current_time = 0.0
    concat_list_path = Path("concat_list.txt")
    
    # Create concat list file
    with open(concat_list_path, 'w', encoding='utf-8') as f:
        for file_path in input_files:
            # Escape single quotes for ffmpeg concat demuxer
            safe_path = str(file_path).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
            
            duration = get_audio_duration(file_path)
            
            chapter_title = clean_title(file_path.name)
            
            chapters.append({
                'title': chapter_title,
                'start': current_time,
                'end': current_time + duration
            })
            
            print(f"  - {file_path.name} ({duration:.1f}s) -> {chapter_title}")
            current_time += duration

    total_duration = current_time
    print(f"\nTotal duration: {total_duration/60:.2f} minutes")

    # 2. Create metadata file
    metadata_path = Path("metadata.txt")
    metadata_content = generate_ffmpeg_metadata(chapters, title, author)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(metadata_content)

    # 3. Build ffmpeg command
    # Basic command: concat audio, map metadata, convert to AAC
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_list_path),
        '-i', str(metadata_path)
    ]

    # Add cover image if provided
    map_audio_index = 0
    if cover_image and Path(cover_image).exists():
        cmd.extend(['-i', str(cover_image)])
        cmd.extend(['-map', '0:a', '-map', '2:v'])
        cmd.extend(['-c:v', 'copy', '-disposition:v', 'attached_pic'])
        print(f"Adding cover image: {cover_image}")
    else:
        cmd.extend(['-map', '0:a'])
    
    cmd.extend(['-map_metadata', '1'])
    
    # Encoding settings
    # AAC codec, .m4b extension (usually requires aac codec)
    cmd.extend(['-c:a', 'aac', '-b:a', bitrate])
    
    # Overwrite output
    cmd.extend(['-y', str(output_file)])

    print("\nRunning ffmpeg...")
    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Created audiobook: {output_file}")
        success = True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error running ffmpeg: {e}")
        success = False
    finally:
        # Cleanup temp files
        if concat_list_path.exists():
            os.remove(concat_list_path)
        if metadata_path.exists():
            os.remove(metadata_path)

    return success

def get_files_from_pattern(pattern):
    """Get list of files matching a glob pattern."""
    from glob import glob
    
    # Try the pattern as-is first
    files = sorted(glob(pattern))
    
    # If no files found and pattern doesn't include a path, try current directory
    if not files and '/' not in pattern and '\\' not in pattern:
        files = sorted(glob(f"./{pattern}"))
    
    return [Path(f) for f in files]

def main():
    parser = argparse.ArgumentParser(
        description='Combine audio files into an M4B audiobook with chapters.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Simple usage
  python 6_create_m4b.py -i audio_files/*.mp3 -o my_book.m4b

  # With metadata
  python 6_create_m4b.py -i audio/*.mp3 -o book.m4b --title "My Book" --author "John Doe" --cover cover.jpg
        '''
    )
    
    parser.add_argument('-i', '--input', nargs='+', help='Input files or glob pattern (e.g. "*.mp3")')
    parser.add_argument('-o', '--output', required=True, help='Output M4B file')
    parser.add_argument('--title', help='Audiobook title')
    parser.add_argument('--author', help='Audiobook author')
    parser.add_argument('--cover', help='Cover image file (jpg/png)')
    parser.add_argument('--bitrate', default='64k', help='Audio bitrate (default: 64k)')
    
    args = parser.parse_args()
    
    if not check_dependencies():
        sys.exit(1)

    # Collect input files
    input_files = []
    if args.input:
        for item in args.input:
            if any(char in item for char in ['*', '?']):
                input_files.extend(get_files_from_pattern(item))
            else:
                p = Path(item)
                if p.is_dir():
                    # If directory, get all audio files
                    for ext in ['*.mp3', '*.m4a', '*.wav', '*.aac']:
                        input_files.extend(sorted(p.glob(ext)))
                else:
                    if p.exists():
                        input_files.append(p)
                    else:
                        print(f"Warning: File not found: {item}")

    # Remove duplicates and sort
    input_files = sorted(list(dict.fromkeys(input_files)))
    
    if not input_files:
        print("Error: No input files found.")
        sys.exit(1)
        
    create_m4b(
        input_files, 
        args.output, 
        title=args.title, 
        author=args.author, 
        cover_image=args.cover,
        bitrate=args.bitrate
    )

if __name__ == '__main__':
    main()

