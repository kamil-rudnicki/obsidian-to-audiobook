#!/usr/bin/env python3
"""
Script to convert markdown file to MP3 audio using ElevenLabs API.
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests
import time

# Load environment variables
load_dotenv()


def read_markdown_file(input_file):
    """Read the markdown file content."""
    with open(input_file, 'r', encoding='utf-8') as f:
        return f.read()


def clean_text_for_speech(text):
    """Clean markdown text for speech synthesis."""
    # Remove markdown headers (# symbols)
    lines = []
    for line in text.split('\n'):
        # Remove # from headers but keep the text
        if line.strip().startswith('#'):
            cleaned_line = line.lstrip('#').strip()
            if cleaned_line:
                lines.append(cleaned_line)
        else:
            lines.append(line)
    
    return '\n'.join(lines)


def split_text_into_chunks(text, max_chars=5000):
    """Split text into chunks that respect sentence boundaries."""
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed limit, save current chunk
        if current_chunk and len(current_chunk) + len(paragraph) + 2 > max_chars:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
        
        # If a single paragraph is too long, split by sentences
        if len(current_chunk) > max_chars:
            sentences = current_chunk.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
            temp_chunk = ""
            
            for sentence in sentences:
                if temp_chunk and len(temp_chunk) + len(sentence) > max_chars:
                    chunks.append(temp_chunk.strip())
                    temp_chunk = sentence
                else:
                    temp_chunk += sentence
            
            current_chunk = temp_chunk
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def text_to_speech_elevenlabs(text, api_key, voice_id, output_file):
    """Convert text to speech using ElevenLabs API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=300)
        response.raise_for_status()
        
        # Save audio to file
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling ElevenLabs API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False


def text_to_speech_openai(text, api_key, voice, model, output_file):
    """Convert text to speech using OpenAI API."""
    url = "https://api.openai.com/v1/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "input": text,
        "voice": voice
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=300)
        response.raise_for_status()
        
        # Save audio to file
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenAI API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False


def merge_audio_files(audio_files, output_file):
    """Merge multiple audio files into one using pydub."""
    try:
        from pydub import AudioSegment
        
        print(f"Merging {len(audio_files)} audio files...")
        combined = AudioSegment.empty()
        
        for audio_file in audio_files:
            audio = AudioSegment.from_mp3(audio_file)
            combined += audio
            # Add a small pause between chunks (500ms)
            combined += AudioSegment.silent(duration=500)
        
        combined.export(output_file, format="mp3")
        print(f"✓ Merged audio saved to: {output_file}")
        
        # Clean up temporary files
        for audio_file in audio_files:
            try:
                os.remove(audio_file)
            except:
                pass
        
        return True
        
    except ImportError:
        print("Warning: pydub not installed. Cannot merge audio files.")
        print("Install with: pip install pydub")
        print(f"Individual audio files saved as: {audio_files[0].replace('_chunk_0.mp3', '_chunk_*.mp3')}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert markdown file to MP3 audio using ElevenLabs or OpenAI TTS API.'
    )
    parser.add_argument(
        '--input_file',
        required=True,
        help='Input markdown file path'
    )
    parser.add_argument(
        '--output_file',
        required=True,
        help='Output MP3 file path'
    )
    parser.add_argument(
        '--provider',
        choices=['elevenlabs', 'openai'],
        default='openai',
        help='TTS provider to use (default: openai)'
    )
    parser.add_argument(
        '--voice',
        help='Voice to use (optional, uses env variable if not provided)'
    )
    parser.add_argument(
        '--model',
        help='Model to use for OpenAI (tts-1 or tts-1-hd, optional, uses env variable if not provided)'
    )
    
    args = parser.parse_args()
    
    print(f"Using provider: {args.provider}")
    
    # Get configuration based on provider
    if args.provider == 'elevenlabs':
        api_key = os.getenv('ELEVENLABS_API_KEY')
        voice = args.voice or os.getenv('ELEVENLABS_VOICE_ID')
        max_chunk_size = 5000
        
        if not api_key:
            print("Error: ELEVENLABS_API_KEY not found in environment variables")
            sys.exit(1)
        
        if not voice:
            print("Error: ELEVENLABS_VOICE_ID not found in environment variables or --voice argument")
            print("\nTo find voice IDs, visit: https://api.elevenlabs.io/v1/voices")
            print("Or use a Polish voice like: 'nPczCjzI2devNBz1zQrb' (Adam - Polish)")
            sys.exit(1)
        
        print(f"Using voice ID: {voice}")
        
    else:  # openai
        api_key = os.getenv('OPENAI_API_KEY')
        voice = args.voice or os.getenv('OPENAI_VOICE', 'nova')
        model = args.model or os.getenv('OPENAI_TTS_MODEL', 'tts-1')
        max_chunk_size = 4096  # OpenAI limit
        
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables")
            sys.exit(1)
        
        print(f"Using voice: {voice}")
        print(f"Using model: {model}")
    print(f"Reading input file: {args.input_file}")
    
    # Read markdown file
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    content = read_markdown_file(args.input_file)
    print(f"File has {len(content)} characters")
    
    # Clean text for speech
    cleaned_text = clean_text_for_speech(content)
    print(f"Cleaned text has {len(cleaned_text)} characters")
    
    if not cleaned_text.strip():
        print("Error: No text to convert")
        sys.exit(1)
    
    # Split into chunks if needed
    chunks = split_text_into_chunks(cleaned_text, max_chars=max_chunk_size)
    print(f"Split into {len(chunks)} chunks")
    
    # Convert each chunk to audio
    audio_files = []
    output_base = Path(args.output_file).stem
    output_dir = Path(args.output_file).parent
    
    for idx, chunk in enumerate(chunks):
        print(f"\n[{idx + 1}/{len(chunks)}] Converting chunk to audio...")
        print(f"  Chunk size: {len(chunk)} characters")
        
        if len(chunks) > 1:
            chunk_output = output_dir / f"{output_base}_chunk_{idx}.mp3"
        else:
            chunk_output = args.output_file
        
        # Call appropriate API based on provider
        if args.provider == 'elevenlabs':
            success = text_to_speech_elevenlabs(chunk, api_key, voice, chunk_output)
        else:  # openai
            success = text_to_speech_openai(chunk, api_key, voice, model, chunk_output)
        
        if success:
            file_size = os.path.getsize(chunk_output)
            print(f"  ✓ Audio saved: {chunk_output} ({file_size / 1024:.1f} KB)")
            audio_files.append(str(chunk_output))
        else:
            print(f"  ✗ Failed to convert chunk {idx + 1}")
            sys.exit(1)
        
        # Small delay to avoid rate limiting
        if idx < len(chunks) - 1:
            time.sleep(1)
    
    # Merge chunks if multiple
    if len(audio_files) > 1:
        merge_audio_files(audio_files, args.output_file)
    else:
        print(f"\n✓ Audio saved to: {args.output_file}")


if __name__ == '__main__':
    main()

