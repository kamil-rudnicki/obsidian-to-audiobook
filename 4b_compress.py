#!/usr/bin/env python3
"""
Script to compress audio files in a directory to a specified format and bitrate.
Supported formats: MP3, AAC (m4a)
"""

import argparse
import os
import sys
from pathlib import Path
import time

def check_dependencies():
    """Check if pydub and ffmpeg are available."""
    try:
        from pydub import AudioSegment
        return True
    except ImportError:
        print("Error: pydub not installed")
        print("Install with: pip install pydub")
        print("\nAlso ensure ffmpeg is installed:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt-get install ffmpeg")
        return False

def get_supported_extensions():
    """Return list of supported audio extensions."""
    return ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac']

def compress_audio(input_path, output_path, format_name, bitrate):
    """Compress a single audio file."""
    from pydub import AudioSegment
    
    print(f"Processing: {input_path.name}")
    
    try:
        # Load audio file
        # pydub attempts to auto-detect format, but we can be explicit if needed
        audio = AudioSegment.from_file(str(input_path))
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare export parameters
        export_params = {
            "format": format_name,
            "bitrate": bitrate
        }
        
        # Start compression
        start_time = time.time()
        
        # Export
        audio.export(str(output_path), **export_params)
        
        duration = time.time() - start_time
        
        # Calculate size reduction
        orig_size = input_path.stat().st_size / (1024 * 1024)
        new_size = output_path.stat().st_size / (1024 * 1024)
        reduction = (1 - (new_size / orig_size)) * 100 if orig_size > 0 else 0
        
        print(f"  -> Saved to: {output_path.name}")
        print(f"  -> Time: {duration:.2f}s")
        print(f"  -> Size: {orig_size:.2f}MB -> {new_size:.2f}MB ({reduction:.1f}% reduction)")
        return True
        
    except Exception as e:
        print(f"  -> Error compressing {input_path.name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Compress audio files in a directory.")
    
    parser.add_argument("--input_folder", required=True, help="Directory containing audio files to compress")
    parser.add_argument("--output_folder", required=True, help="Directory to save compressed files")
    
    parser.add_argument(
        "--format", 
        choices=['mp3', 'aac', 'm4a'], 
        default='mp3',
        help="Output format (default: mp3). Note: 'aac' will use .m4a container."
    )
    
    parser.add_argument(
        "--bitrate", 
        default=None,
        help="Target bitrate (e.g., '320k', '256k', '192k'). Defaults: 320k for MP3, 256k for AAC."
    )
    
    args = parser.parse_args()
    
    if not check_dependencies():
        sys.exit(1)
        
    # Handle defaults logic
    format_map = {
        'mp3': 'mp3',
        'aac': 'adts', # 'adts' is often used for raw aac, but usually we want m4a container for aac audio
        'm4a': 'ipod'  # pydub/ffmpeg often uses 'ipod' or 'mp4' for m4a
    }
    
    # For pydub export, format 'mp3' is standard. 
    # For AAC, we usually export as 'mp4' or 'ipod' (m4a) container with aac codec, 
    # or strictly 'adts' for .aac files.
    # The user asked for "AAC", usually implying .m4a or .aac. Let's stick to .m4a for better compatibility if they choose AAC.
    
    output_ext = f".{args.format}"
    if args.format == 'aac':
        output_ext = '.m4a' # AAC audio in M4A container is most common
        export_format = 'ipod' # ffmpeg format for m4a
    elif args.format == 'm4a':
        output_ext = '.m4a'
        export_format = 'ipod'
    else:
        output_ext = '.mp3'
        export_format = 'mp3'

    # Set default bitrates if not provided
    if args.bitrate is None:
        if 'mp3' in args.format:
            args.bitrate = '320k'
        else:
            args.bitrate = '256k'
            
    # Normalize bitrate string (ensure it ends with 'k' if it's just a number)
    if args.bitrate.isdigit():
        args.bitrate = f"{args.bitrate}k"
        
    print(f"Configuration:")
    print(f"  Input Directory:  {args.input_folder}")
    print(f"  Output Directory: {args.output_folder}")
    print(f"  Format:           {args.format} ({export_format})")
    print(f"  Bitrate:          {args.bitrate}")
    print("-" * 50)
    
    input_path = Path(args.input_folder)
    output_path = Path(args.output_folder)
    
    if not input_path.exists():
        print(f"Error: Input directory '{args.input_folder}' does not exist.")
        sys.exit(1)
        
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    supported_exts = get_supported_extensions()
    files_processed = 0
    errors = 0
    
    # Walk through input directory
    files_to_process = [
        f for f in input_path.iterdir() 
        if f.is_file() and f.suffix.lower() in supported_exts
    ]
    
    if not files_to_process:
        print(f"No supported audio files found in {args.input_folder}")
        print(f"Supported extensions: {', '.join(supported_exts)}")
        sys.exit(0)
        
    print(f"Found {len(files_to_process)} files to process.")
    
    for file_path in files_to_process:
        target_file = output_path / (file_path.stem + output_ext)
        
        success = compress_audio(
            file_path, 
            target_file, 
            export_format, 
            args.bitrate
        )
        
        if success:
            files_processed += 1
        else:
            errors += 1
            
    print("-" * 50)
    print(f"Completed! Processed: {files_processed}, Errors: {errors}")

if __name__ == "__main__":
    main()
