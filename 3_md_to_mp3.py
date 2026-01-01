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
import re

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


def split_markdown_by_headers(text):
    """Split markdown text into sections based on headers."""
    sections = []
    lines = text.split('\n')
    current_title = "preamble"
    current_content = []
    
    for line in lines:
        if line.strip().startswith('#'):
            # Save previous section if it has content
            if current_content:
                sections.append((current_title, '\n'.join(current_content)))
            
            # Start new section
            # Extract title for filename
            raw_title = line.lstrip('#').strip()
            if raw_title:
                current_title = raw_title
            else:
                current_title = "section"
                
            # Start content with this line so it gets spoken (clean_text_for_speech handles # removal)
            current_content = [line]
            
        else:
            current_content.append(line)
            
    # Add last section
    if current_content:
        sections.append((current_title, '\n'.join(current_content)))
        
    return sections


def extract_title_from_markdown(text):
    """Extract the first header from markdown as title."""
    for line in text.split('\n'):
        if line.strip().startswith('#'):
            # Extract text from '# My Title' or '## My Title'
            title = line.lstrip('#').strip()
            if title:
                # Remove characters that aren't allowed in filenames
                clean_title = re.sub(r'[^\w\s-]', '', title).strip()
                # Replace spaces with underscores or hyphens
                clean_title = re.sub(r'[-\s]+', '_', clean_title)
                return clean_title
    return None


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


def text_to_speech_google(text, voice_name, language_code, output_file):
    """Convert text to speech using Google Cloud TTS API."""
    try:
        from google.cloud import texttospeech
        
        # Initialize the client
        client = texttospeech.TextToSpeechClient()
        
        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        # The response's audio_content is binary.
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
            
        return True
        
    except ImportError:
        print("Error: google-cloud-texttospeech not installed.")
        print("Install with: pip install google-cloud-texttospeech")
        return False
    except Exception as e:
        print(f"Error calling Google Cloud TTS API: {e}")
        return False


def merge_audio_files(audio_files, output_file):
    """Merge multiple audio files into one using pydub."""
    try:
        from pydub import AudioSegment
        
        print(f"Merging {len(audio_files)} audio files...")
        combined = AudioSegment.empty()
        
        for audio_file in audio_files:
            audio = AudioSegment.from_file(audio_file)
            combined += audio
            # Add a small pause between chunks (500ms)
            combined += AudioSegment.silent(duration=500)
        
        # Determine format from output file extension
        output_format = "mp3"
        if str(output_file).lower().endswith(".wav"):
            output_format = "wav"
            
        combined.export(output_file, format=output_format)
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
        '--output_folder',
        required=True,
        help='Output folder for the MP3 file'
    )
    parser.add_argument(
        '--provider',
        choices=['elevenlabs', 'openai', 'google'],
        default='openai',
        help='TTS provider to use (default: openai)'
    )
    parser.add_argument(
        '--voice',
        help='Voice to use (required for ElevenLabs, defaults to "nova" for OpenAI)'
    )
    parser.add_argument(
        '--language',
        help='Language code for Google TTS (e.g., pl-PL, en-US, optional)'
    )
    parser.add_argument(
        '--model',
        help='Model to use for OpenAI (defaults to "tts-1")'
    )
    
    args = parser.parse_args()
    
    print(f"Using provider: {args.provider}")
    
    # Determine file extension based on provider
    file_extension = 'mp3'
    if args.provider == 'google':
        file_extension = 'wav'

    # Get configuration based on provider
    if args.provider == 'elevenlabs':
        api_key = os.getenv('ELEVENLABS_API_KEY')
        voice = args.voice
        max_chunk_size = 5000
        
        if not api_key:
            print("Error: ELEVENLABS_API_KEY not found in environment variables")
            sys.exit(1)
        
        if not voice:
            print("Error: --voice argument is required for ElevenLabs provider")
            print("\nTo find voice IDs, visit: https://api.elevenlabs.io/v1/voices")
            print("Or use a Polish voice like: 'nPczCjzI2devNBz1zQrb' (Adam - Polish)")
            sys.exit(1)
        
        print(f"Using voice ID: {voice}")
        
    elif args.provider == 'google':
        voice = args.voice or os.getenv('GOOGLE_VOICE', 'pl-PL-Chirp3-HD-Iapetus')
        language = args.language or os.getenv('GOOGLE_LANGUAGE', 'pl-PL')
        # Reduced from 5000 to 2500 to stay under the 5000-byte limit for multi-byte characters
        max_chunk_size = 4000 
        
        # Check for Google Application Credentials
        if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            print("Warning: GOOGLE_APPLICATION_CREDENTIALS not found in environment variables.")
            print("Google TTS requires a service account JSON file.")
        
        print(f"Using Google voice: {voice}")
        print(f"Using Google language: {language}")

    else:  # openai
        api_key = os.getenv('OPENAI_API_KEY')
        voice = args.voice or 'nova'
        model = args.model or 'tts-1'
        max_chunk_size = 4096  # OpenAI limit
        
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables")
            sys.exit(1)
        
        print(f"Using voice: {voice}")
        print(f"Using model: {model}")
    
    # Set up paths
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
        
    output_dir = Path(args.output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read markdown file
    content = read_markdown_file(input_path)
    print(f"File has {len(content)} characters")
    
    # Split content by headers
    sections = split_markdown_by_headers(content)
    print(f"Found {len(sections)} sections/chapters")
    
    for section_idx, (section_title, section_content) in enumerate(sections):
        print(f"\n--- Processing Section {section_idx + 1}/{len(sections)}: {section_title} ---")
        
        # Determine output filename for this section
        if section_title == "preamble":
            # If it's the preamble, use input filename + preamble
            # Or if it's the only section, use input filename
            if len(sections) == 1:
                safe_title = input_path.stem
            else:
                safe_title = f"{input_path.stem}_preamble"
        else:
            # Clean title for filename
            clean_title = re.sub(r'[^\w\s-]', '', section_title).strip()
            clean_title = re.sub(r'[-\s]+', '_', clean_title)
            safe_title = clean_title
            
        # Remove trailing 'md' if present
        if safe_title.lower().endswith('md'):
            safe_title = safe_title[:-2]
            
        # Clean up any trailing separators
        safe_title = safe_title.rstrip('_-')
            
        output_file = output_dir / f"{safe_title}.{file_extension}"
        print(f"Target file: {output_file}")
        
        if output_file.exists():
            print(f"Skipping {output_file} - already exists")
            continue
    
        # Clean text for speech
        cleaned_text = clean_text_for_speech(section_content)
        print(f"Cleaned section text has {len(cleaned_text)} characters")
        
        if not cleaned_text.strip():
            print("Skipping empty section")
            continue
        
        # Split into chunks if needed
        chunks = split_text_into_chunks(cleaned_text, max_chars=max_chunk_size)
        print(f"Split into {len(chunks)} chunks")
        
        # Convert each chunk to audio
        audio_files = []
        output_base = output_file.stem
        
        for idx, chunk in enumerate(chunks):
            print(f"\n  [{idx + 1}/{len(chunks)}] Converting chunk to audio...")
            print(f"    Chunk size: {len(chunk)} characters")
            
            if len(chunks) > 1:
                chunk_output = output_dir / f"{output_base}_chunk_{idx}.{file_extension}"
            else:
                chunk_output = output_file
            
            # Call appropriate API based on provider
            if args.provider == 'elevenlabs':
                success = text_to_speech_elevenlabs(chunk, api_key, voice, chunk_output)
            elif args.provider == 'google':
                success = text_to_speech_google(chunk, voice, language, chunk_output)
            else:  # openai
                success = text_to_speech_openai(chunk, api_key, voice, model, chunk_output)
            
            if success:
                file_size = os.path.getsize(chunk_output)
                print(f"    ✓ Audio saved: {chunk_output} ({file_size / 1024:.1f} KB)")
                audio_files.append(str(chunk_output))
            else:
                print(f"    ✗ Failed to convert chunk {idx + 1}")
                sys.exit(1)
            
            # Small delay to avoid rate limiting
            if idx < len(chunks) - 1:
                time.sleep(1)
        
        # Merge chunks if multiple
        if len(audio_files) > 1:
            merge_audio_files(audio_files, str(output_file))
        else:
            print(f"\n  ✓ Section audio saved to: {output_file}")



if __name__ == '__main__':
    main()

