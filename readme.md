# Obsidian .md notes to Audiobook

🎙️ Transform your Obsidian knowledge vault into professionally narrated audiobooks. This tool uses AI to weave your markdown notes into engaging narratives with customizable writing styles - from ancient philosophy to modern storytelling. Features multiple TTS providers (OpenAI, ElevenLabs), batch processing, and intelligent content organization.

1. Create `.env` and install `brew install ffmpeg` and `pip install -r requirements.txt`

```bash
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=google/gemini-3-flash-preview

# Either OpenAI or ElevenLabs

OPENAI_API_KEY=your_openai_api_key
OPENAI_VOICE=nova # `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
OPENAI_TTS_MODEL=gpt-4o-mini-tts # Models: `tts-1` (faster) or `tts-1-hd` (higher quality)

ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=nPczCjzI2devNBz1zQrb
```

2. Create csv file with all your notes:

```sh
python 1_create_csv.py \
  --source_folder 'path/to/your/obsidian/notes' \
  --output obsidian_files.csv
```

Next, open the CSV file (using Google Sheets or similar software), create a new column called "list" (or any name you prefer), and categorize your notes by entering labels such as "personal" for each row. This categorization will allow you to filter and organize your notes later.
Then download this CSV and name it `obsidian_files_redacted.csv`.

3. Write book using AI:

```sh
python obsidian-to-audiobook/2_write_book_using_ai.py \
  --input_file obsidian_files_redacted.csv \
  --folder 'path/to/your/obsidian/notes' \
  --column list \
  --value personal \
  --output_file book_output.md \
  --randomize \
  --prompt "Can you make a book text from text below? Make random choice about the writing style, from authors starting from greek philosophy to modern day. try to write something about every concept in the text. Write in polish. Don't use any formatting. Only add new lines. Write in engaging and easy way. If possible write stories. Sometimes add narrations and comments. If there is nothing to write about, write nothing, vary character response from short lik 200 characters to 4000."
```

4. Create MP3 chunks:

```sh
python 3_md_to_mp3.py \
  --input_file book_output.md \
  --output_file book_output.mp3 \
  --provider openai

python 3_md_to_mp3.py \
  --input_file book_output.md \
  --output_file book_output.mp3 \
  --provider elevenlabs
```

5. Merge chunks into single MP3 file (optional):

```sh
# Merge specific files
python 4_merge_mp3.py \
  -i file1.mp3 file2.mp3 file3.mp3 \
  -o merged_output.mp3

# Merge files using glob pattern
python 4_merge_mp3.py \
  --pattern "book_output_chunk_*.mp3" \
  -o merged_output.mp3

# Merge with custom silence duration (in milliseconds)
python 4_merge_mp3.py \
  -i file1.mp3 file2.mp3 \
  -o merged_output.mp3 \
  --silence 1000

# Merge and delete input files after
python 4_merge_mp3.py \
  --pattern "book_output_chunk_*.mp3" \
  -o merged_output.mp3 \
  --delete-input
```
