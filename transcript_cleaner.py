"""
=============================================================
STEP 3: TRANSCRIPT CLEANER
=============================================================
What this script does:
  Reads every .txt transcript file from the /transcripts folder.
  Cleans the transcript text (removes extra spaces, repeated blank
  lines, and formatting noise) WITHOUT removing any real content.
  Splits the cleaned text into chunks of ~1200-1500 words so that
  a future AI step can process each chunk separately.

  For each video it saves two files into /cleaned_transcripts:
    video_name.txt        — the cleaned full transcript (human-readable)
    video_name_chunks.json — the same text split into numbered chunks

What you need before running this:
  - Transcript .txt files in /transcripts (produced by Step 2)

How to run:
  This script runs automatically after Step 2 completes.
  You can also run it on its own: python transcript_cleaner.py
=============================================================
"""

import os
import re
import json
import glob


# -------------------------------------------------------
# SETTINGS
# -------------------------------------------------------

# Target number of words per chunk.
# Keeping this around 1200-1500 words lets an AI model read
# one chunk at a time without hitting context-length limits.
CHUNK_SIZE = 1400


# -------------------------------------------------------
# HELPER: CLEAN TRANSCRIPT TEXT
# -------------------------------------------------------
def clean_text(text):
    """
    Cleans up raw transcript text without removing any real content.

    What it fixes:
      - Windows-style line endings (CRLF) converted to Unix (LF)
      - Runs of spaces or tabs collapsed to a single space
      - More than two blank lines in a row collapsed to one blank line
      - Leading and trailing whitespace removed from each line
      - Any stray control characters removed

    What it does NOT do:
      - Does not remove words or sentences
      - Does not summarise or paraphrase
      - Does not change capitalisation
    """

    # 1. Normalise line endings (Windows CRLF → LF)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Remove stray control characters (keep normal newlines and tabs)
    #    \x00-\x08 and \x0b-\x1f covers control chars but leaves \n (0x0a) and \t (0x09)
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)

    # 3. Collapse multiple spaces or tabs on a single line into one space
    #    We process line by line so we don't accidentally collapse intentional blank lines
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Replace any run of whitespace characters (except newline) with a single space
        line = re.sub(r"[ \t]+", " ", line)
        # Remove leading and trailing spaces from the line
        line = line.strip()
        cleaned_lines.append(line)

    # 4. Collapse runs of more than 2 consecutive blank lines into a single blank line
    #    Join back, then use a regex to squash repeated blank lines
    rejoined = "\n".join(cleaned_lines)
    rejoined = re.sub(r"\n{3,}", "\n\n", rejoined)

    # 5. Remove any leading/trailing blank space from the whole block
    rejoined = rejoined.strip()

    return rejoined


# -------------------------------------------------------
# HELPER: SPLIT TEXT INTO CHUNKS
# -------------------------------------------------------
def chunk_text(text, video_title):
    """
    Splits a block of text into chunks of roughly CHUNK_SIZE words each.

    Why chunking?
      Transcripts can be very long. Later AI analysis works better when
      it reads one focused section at a time rather than the entire text.

    How it works:
      1. Split the text into individual words.
      2. Accumulate words until we hit CHUNK_SIZE.
      3. When we hit the limit, save the current chunk and start a new one.
      4. Return a list of dicts, one per chunk.

    Returns a list like:
      [
        {"video_title": "...", "chunk_id": 1, "text": "first 1400 words..."},
        {"video_title": "...", "chunk_id": 2, "text": "next 1400 words..."},
        ...
      ]
    """
    words = text.split()

    # If the transcript is very short, return it as a single chunk
    if len(words) <= CHUNK_SIZE:
        return [{"video_title": video_title, "chunk_id": 1, "text": text.strip()}]

    chunks = []
    chunk_id = 1
    current_words = []

    for word in words:
        current_words.append(word)

        # When we've accumulated enough words, save this chunk
        if len(current_words) >= CHUNK_SIZE:
            chunk_text_block = " ".join(current_words).strip()
            chunks.append({
                "video_title": video_title,
                "chunk_id":    chunk_id,
                "text":        chunk_text_block,
            })
            chunk_id += 1
            current_words = []

    # Don't forget any leftover words that didn't fill a full chunk
    if current_words:
        chunk_text_block = " ".join(current_words).strip()
        chunks.append({
            "video_title": video_title,
            "chunk_id":    chunk_id,
            "text":        chunk_text_block,
        })

    return chunks


# -------------------------------------------------------
# HELPER: PARSE A TRANSCRIPT .txt FILE
# -------------------------------------------------------
def parse_transcript_file(file_path):
    """
    Reads a transcript .txt file and separates it into two parts:
      - header_lines: the metadata block at the top (Title, Channel, URL, etc.)
      - body_text:    everything after the separator line (the actual transcript)

    The separator is the line of dashes: '----...'

    Returns (header_lines, body_text).
    If no separator is found, treats the whole file as body_text.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The header is separated from the transcript by a line of dashes
    # We split on the first occurrence only
    separator = "-" * 60

    if separator in content:
        # Split into two parts at the first separator line
        parts = content.split(separator, maxsplit=1)
        header_block = parts[0]   # Everything before the dashes
        body_text    = parts[1]   # Everything after the dashes
    else:
        # No separator found — treat everything as body text
        header_block = ""
        body_text    = content

    # Split the header block into individual lines, strip blanks
    header_lines = [line for line in header_block.splitlines() if line.strip()]

    return header_lines, body_text


# -------------------------------------------------------
# HELPER: SAVE THE CLEANED .txt FILE
# -------------------------------------------------------
def save_cleaned_txt(header_lines, cleaned_body, output_path):
    """
    Writes the cleaned transcript back to a .txt file.
    Keeps the original metadata header, then the cleaned body.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        # Write the header lines back as they were
        for line in header_lines:
            f.write(line + "\n")

        # Write the separator
        f.write("-" * 60 + "\n\n")

        # Write the cleaned transcript body
        f.write(cleaned_body)
        f.write("\n")


# -------------------------------------------------------
# HELPER: SAVE THE CHUNKS .json FILE
# -------------------------------------------------------
def save_chunks_json(chunks, output_path):
    """
    Saves the list of chunk dicts to a JSON file.

    Format:
      [
        {"video_title": "...", "chunk_id": 1, "text": "..."},
        {"video_title": "...", "chunk_id": 2, "text": "..."},
        ...
      ]
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)


# -------------------------------------------------------
# HELPER: BUILD THE OUTPUT FILE STEM FROM INPUT FILENAME
# -------------------------------------------------------
def make_output_stem(input_filename):
    """
    Strips the .txt extension from the input filename to get a base name.
    Example: 'HubSpot_CRM_Tutorial.txt' → 'HubSpot_CRM_Tutorial'
    """
    return os.path.splitext(input_filename)[0]


# -------------------------------------------------------
# HELPER: EXTRACT VIDEO TITLE FROM HEADER LINES
# -------------------------------------------------------
def extract_title_from_header(header_lines):
    """
    Looks for the 'Title:' line in the header and returns its value.
    Falls back to 'Unknown Title' if not found.
    """
    for line in header_lines:
        if line.startswith("Title:"):
            # Everything after 'Title:' and any whitespace
            return line[len("Title:"):].strip()
    return "Unknown Title"


# -------------------------------------------------------
# MAIN FUNCTION: CLEAN ALL TRANSCRIPTS
# -------------------------------------------------------
def clean_transcripts(transcripts_folder="transcripts"):
    """
    Orchestrates the full Step 3 process:
      1. Finds all .txt files in /transcripts
      2. For each file:
         a. Reads and separates the header from the transcript body
         b. Cleans the body text
         c. Splits the body into chunks
         d. Saves a cleaned .txt file to /cleaned_transcripts
         e. Saves a chunked .json file to /cleaned_transcripts
      3. Prints a summary

    The transcripts_folder argument lets you point at a different
    folder if needed, but the default is 'transcripts'.
    """

    print("\n" + "=" * 60)
    print("  MARKET VOICE — STEP 3: TRANSCRIPT CLEANER")
    print("=" * 60)

    # --- Find all .txt files in the transcripts folder ---
    pattern = os.path.join(transcripts_folder, "*.txt")
    transcript_files = glob.glob(pattern)

    if not transcript_files:
        print(f"\n  No .txt files found in /{transcripts_folder}.")
        print("  Please run Step 2 first to download transcripts.\n")
        return

    print(f"\n  Found {len(transcript_files)} transcript file(s) to process.\n")

    # --- Create the output folder if it doesn't exist ---
    output_folder = "cleaned_transcripts"
    os.makedirs(output_folder, exist_ok=True)

    # --- Track results ---
    total_processed = 0
    total_failed    = 0

    # --- Process each transcript file ---
    for i, file_path in enumerate(sorted(transcript_files), start=1):
        filename = os.path.basename(file_path)
        print(f"  [{i}/{len(transcript_files)}] {filename}")

        try:
            # Step 3a: Read and split header from body
            header_lines, raw_body = parse_transcript_file(file_path)

            # Step 3b: Clean the body text
            cleaned_body = clean_text(raw_body)

            # Step 3c: Extract the video title for use in chunk dicts
            video_title = extract_title_from_header(header_lines)

            # Step 3d: Split cleaned body into chunks
            chunks = chunk_text(cleaned_body, video_title)

            # Step 3e: Build output file paths
            stem           = make_output_stem(filename)
            txt_out_path   = os.path.join(output_folder, f"{stem}.txt")
            json_out_path  = os.path.join(output_folder, f"{stem}_chunks.json")

            # Step 3f: Save the cleaned .txt file
            save_cleaned_txt(header_lines, cleaned_body, txt_out_path)

            # Step 3g: Save the chunks .json file
            save_chunks_json(chunks, json_out_path)

            print(f"      Cleaned text  → {txt_out_path}")
            print(f"      Chunks ({len(chunks)})     → {json_out_path}")

            total_processed += 1

        except Exception as e:
            print(f"      ERROR processing file: {e}")
            total_failed += 1

    # --- Print the summary ---
    print("\n  " + "=" * 56)
    print("  STEP 3 COMPLETE — SUMMARY")
    print("  " + "-" * 56)
    print(f"  Transcripts processed:      {total_processed}")
    print(f"  Errors:                     {total_failed}")
    print(f"  Output saved to:            {os.path.abspath(output_folder)}")
    print("  " + "=" * 56 + "\n")


# -------------------------------------------------------
# ENTRY POINT (when run directly)
# -------------------------------------------------------
if __name__ == "__main__":
    clean_transcripts()
