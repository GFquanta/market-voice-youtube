"""
=============================================================
STEP 2: TRANSCRIPT COLLECTOR
=============================================================
What this script does:
  Reads the video list JSON produced by Step 1.
  Downloads the transcript (captions) for each video.
  Saves one .txt file per video into a /transcripts folder.

What you need before running this:
  - A JSON file in /output produced by Step 1
  - youtube-transcript-api installed (included in requirements.txt)

How to run:
  This script runs automatically after Step 1 completes.
  You can also run it on its own: python transcript_collector.py
=============================================================
"""

import os
import json
import glob

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


# -------------------------------------------------------
# HELPER: FIND THE MOST RECENT JSON FILE IN /output
# -------------------------------------------------------
def find_latest_json():
    """
    Looks in the /output folder for the most recently created .json file.
    Returns the file path, or None if no file is found.
    """
    # glob.glob returns a list of file paths matching the pattern
    json_files = glob.glob(os.path.join("output", "*.json"))

    if not json_files:
        return None

    # Sort by file modification time, most recent last, then take the last one
    latest = max(json_files, key=os.path.getmtime)
    return latest


# -------------------------------------------------------
# HELPER: EXTRACT VIDEO ID FROM A YOUTUBE URL
# -------------------------------------------------------
def extract_video_id(url):
    """
    Pulls the video ID out of a YouTube URL.
    Example: 'https://www.youtube.com/watch?v=abc123xyz' → 'abc123xyz'
    Returns None if it can't find the ID.
    """
    # The video ID always follows 'v=' in the URL
    if "v=" in url:
        # Split on 'v=' and take everything after it, then stop at '&' if present
        video_id = url.split("v=")[-1].split("&")[0]
        return video_id
    return None


# -------------------------------------------------------
# HELPER: DOWNLOAD TRANSCRIPT FOR ONE VIDEO
# -------------------------------------------------------
def get_transcript(video_id):
    """
    Downloads the transcript (captions) for a YouTube video.
    Returns the full transcript as a single string, or None if unavailable.

    youtube-transcript-api returns a list of segments like:
      [{"text": "Hello world", "start": 0.0, "duration": 1.5}, ...]
    We join all the text segments into one readable block.
    """
    try:
        # Fetch transcript — tries English first, then falls back to auto-generated
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])

        # Join all text segments with a space to form one continuous block of text
        full_text = " ".join(segment["text"] for segment in segments)
        return full_text

    except TranscriptsDisabled:
        # The video owner has turned off captions entirely
        return None

    except NoTranscriptFound:
        # No English transcript exists (might be in another language or none at all)
        return None

    except Exception as e:
        # Catch any other unexpected error (network issue, private video, etc.)
        print(f"      Unexpected error fetching transcript: {e}")
        return None


# -------------------------------------------------------
# HELPER: SAVE ONE TRANSCRIPT TO A .txt FILE
# -------------------------------------------------------
def save_transcript(video, transcript_text, transcripts_folder):
    """
    Saves a single transcript as a .txt file.
    The filename is built from the video title (spaces replaced with underscores).

    File format:
      Title
      Channel
      URL
      Publish Date
      ----
      TRANSCRIPT TEXT
    """
    # Build a safe filename from the video title
    safe_title = video["title"].replace(" ", "_")

    # Remove characters that are not allowed in file names on Windows or Mac
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        safe_title = safe_title.replace(char, "")

    # Trim to 80 characters so filenames don't get too long
    safe_title = safe_title[:80]

    file_path = os.path.join(transcripts_folder, f"{safe_title}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Title:        {video['title']}\n")
        f.write(f"Channel:      {video['channel']}\n")
        f.write(f"URL:          {video['url']}\n")
        f.write(f"Publish Date: {video['publish_date']}\n")
        f.write("-" * 60 + "\n\n")
        f.write(transcript_text)
        f.write("\n")

    return file_path


# -------------------------------------------------------
# MAIN FUNCTION: COLLECT ALL TRANSCRIPTS
# -------------------------------------------------------
def collect_transcripts(json_path=None):
    """
    Orchestrates the full Step 2 process:
      1. Reads the video list from the JSON file
      2. Loops through each video
      3. Downloads the transcript
      4. Saves it to /transcripts
      5. Prints a summary at the end

    If json_path is not provided, it finds the latest JSON in /output automatically.
    """

    print("\n" + "=" * 60)
    print("  MARKET VOICE — STEP 2: TRANSCRIPT COLLECTOR")
    print("=" * 60)

    # --- Find the input JSON file ---
    if json_path is None:
        json_path = find_latest_json()

    if json_path is None:
        print("\n  ERROR: No JSON file found in the /output folder.")
        print("  Please run Step 1 first to generate a video list.\n")
        return

    print(f"\n  Reading video list from: {json_path}")

    # --- Load the video list ---
    with open(json_path, "r", encoding="utf-8") as f:
        videos = json.load(f)

    if not videos:
        print("\n  The video list is empty. Nothing to collect.\n")
        return

    print(f"  Found {len(videos)} video(s) to process.\n")

    # --- Create the /transcripts folder if it doesn't exist ---
    transcripts_folder = "transcripts"
    os.makedirs(transcripts_folder, exist_ok=True)

    # --- Track results for the summary ---
    total_attempted  = 0
    total_saved      = 0
    total_failed     = 0

    # --- Loop through each video ---
    for i, video in enumerate(videos, start=1):
        title = video.get("title", "Unknown title")
        url   = video.get("url", "")

        print(f"  [{i}/{len(videos)}] {title}")

        total_attempted += 1

        # Extract the video ID from the URL
        video_id = extract_video_id(url)

        if not video_id:
            print(f"      Skipped — could not extract video ID from URL: {url}")
            total_failed += 1
            continue

        # Attempt to download the transcript
        transcript_text = get_transcript(video_id)

        if transcript_text is None:
            print(f"      Skipped — no transcript available for this video.")
            total_failed += 1
            continue

        # Save the transcript to a file
        saved_path = save_transcript(video, transcript_text, transcripts_folder)
        print(f"      Saved → {saved_path}")
        total_saved += 1

    # --- Print the summary ---
    print("\n  " + "=" * 56)
    print("  STEP 2 COMPLETE — SUMMARY")
    print("  " + "-" * 56)
    print(f"  Videos attempted:           {total_attempted}")
    print(f"  Transcripts saved:          {total_saved}")
    print(f"  Skipped (no transcript):    {total_failed}")
    print(f"  Transcripts saved to:       {os.path.abspath(transcripts_folder)}")
    print("  " + "=" * 56 + "\n")


# -------------------------------------------------------
# ENTRY POINT (when run directly)
# -------------------------------------------------------
if __name__ == "__main__":
    collect_transcripts()
