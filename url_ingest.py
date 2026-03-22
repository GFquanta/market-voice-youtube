"""
=============================================================
URL INGEST — Bring Your Own URLs
=============================================================
What this script does:
  Skip the video search (Step 1) entirely.
  You already have YouTube URLs — just paste them in.
  This script fetches the video metadata, then kicks off
  the same Steps 2 + 3 pipeline (transcript download → clean/chunk).

Three ways to provide URLs:
  1. Interactive:   python url_ingest.py
                    (paste URLs one per line, blank line to finish)

  2. From a file:   python url_ingest.py --file my_urls.txt
                    (one URL per line, # comments and blank lines ignored)

  3. Inline:        python url_ingest.py URL1 URL2 URL3

What you need:
  - YOUTUBE_API_KEY in .env (to fetch video metadata)
  - Packages from requirements.txt installed

The output is the same JSON format as video_finder.py,
so Steps 2 + 3 work identically.
=============================================================
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime

from dotenv import load_dotenv
from googleapiclient.discovery import build

from transcript_collector import collect_transcripts
from transcript_cleaner import clean_transcripts

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# YouTube API allows up to 50 video IDs per request
BATCH_SIZE = 50


# -------------------------------------------------------
# EXTRACT VIDEO ID FROM ANY YOUTUBE URL FORMAT
# -------------------------------------------------------
def extract_video_id(url):
    """
    Handles all common YouTube URL formats:
      - https://www.youtube.com/watch?v=abc123
      - https://youtu.be/abc123
      - https://www.youtube.com/embed/abc123
      - https://www.youtube.com/v/abc123
      - Just a bare video ID (11 chars)
    """
    url = url.strip()

    # youtu.be short links
    match = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # Standard ?v= parameter
    match = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # /embed/ or /v/ paths
    match = re.search(r"/(?:embed|v)/([A-Za-z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # Bare video ID (exactly 11 chars, alphanumeric + _ -)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    return None


# -------------------------------------------------------
# FETCH VIDEO METADATA IN BATCHES
# -------------------------------------------------------
def fetch_video_metadata(video_ids):
    """
    Uses the YouTube Data API (videos.list) to get metadata for a list of video IDs.
    This is a single API call per batch of 50, so it's very quota-efficient.

    Returns a list of dicts matching video_finder.py's output format.
    """
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    videos = []

    for i in range(0, len(video_ids), BATCH_SIZE):
        batch = video_ids[i:i + BATCH_SIZE]
        ids_str = ",".join(batch)

        try:
            response = youtube.videos().list(
                id=ids_str,
                part="snippet",
            ).execute()
        except Exception as e:
            print(f"  ERROR: YouTube API call failed: {e}")
            continue

        for item in response.get("items", []):
            snippet = item["snippet"]
            vid_id = item["id"]
            pub_date = snippet.get("publishedAt", "")

            # Format the date to match video_finder output
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                pub_date_clean = dt.strftime("%Y-%m-%d")
            except Exception:
                pub_date_clean = pub_date

            videos.append({
                "title": snippet.get("title", "Unknown title"),
                "channel": snippet.get("channelTitle", "Unknown channel"),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "publish_date": pub_date_clean,
                "phrase_matches": 0,    # Not applicable for manual URLs
                "reason": "Manually provided URL",
            })

    return videos


# -------------------------------------------------------
# READ URLS FROM A TEXT FILE
# -------------------------------------------------------
def read_urls_from_file(file_path):
    """
    Reads URLs from a text file.
    Skips blank lines and lines starting with #.
    """
    urls = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


# -------------------------------------------------------
# READ URLS INTERACTIVELY
# -------------------------------------------------------
def read_urls_interactive():
    """
    Lets user paste URLs one per line.
    Blank line (just press Enter) finishes input.
    """
    print("\n  Paste YouTube URLs below, one per line.")
    print("  Press Enter on a blank line when done.\n")

    urls = []
    while True:
        try:
            line = input("  URL: ").strip()
        except EOFError:
            break
        if not line:
            break
        urls.append(line)

    return urls


# -------------------------------------------------------
# SAVE — same format as video_finder.py
# -------------------------------------------------------
def save_results(videos, label="manual"):
    """Save the video list to /output as JSON + TXT, same format as Step 1."""
    os.makedirs("output", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^a-z0-9_]", "_", label.lower())[:40]
    base_name = f"output/{safe_label}_{timestamp}"

    # JSON
    json_path = f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    # Text
    txt_path = f"{base_name}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("URL INGEST RESULTS (manually provided URLs)\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for i, video in enumerate(videos, start=1):
            f.write(f"{i}. {video['title']}\n")
            f.write(f"   Channel:  {video['channel']}\n")
            f.write(f"   URL:      {video['url']}\n")
            f.write(f"   Date:     {video['publish_date']}\n")
            f.write("\n")

    return txt_path, json_path


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="URL Ingest — skip video search, bring your own YouTube URLs"
    )
    parser.add_argument("urls", nargs="*", help="YouTube URLs (inline)")
    parser.add_argument("--file", "-f", type=str,
                        help="Path to a text file with one URL per line")
    parser.add_argument("--label", "-l", type=str, default="manual",
                        help="Label for this batch (used in output filenames)")
    parser.add_argument("--skip-transcripts", action="store_true",
                        help="Only fetch metadata, don't download transcripts")

    args = parser.parse_args()

    # ---- Check API key ----
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "YOUR_KEY_HERE":
        print("\n  ERROR: No YouTube API key found.")
        print("  Set YOUTUBE_API_KEY in your .env file.\n")
        sys.exit(1)

    # ---- Collect URLs ----
    urls = []

    if args.file:
        urls = read_urls_from_file(args.file)
        print(f"\n  Read {len(urls)} URL(s) from {args.file}")
    elif args.urls:
        urls = args.urls
    else:
        urls = read_urls_interactive()

    if not urls:
        print("\n  No URLs provided. Nothing to do.\n")
        sys.exit(0)

    # ---- Extract video IDs ----
    print(f"\n  {'=' * 56}")
    print(f"  URL INGEST — Processing {len(urls)} URL(s)")
    print(f"  {'=' * 56}\n")

    video_ids = []
    skipped = []

    for url in urls:
        vid_id = extract_video_id(url)
        if vid_id:
            video_ids.append(vid_id)
            print(f"    ✓ {vid_id}  ←  {url[:60]}")
        else:
            skipped.append(url)
            print(f"    ✗ Could not extract video ID: {url[:60]}")

    if skipped:
        print(f"\n  Skipped {len(skipped)} invalid URL(s).")

    if not video_ids:
        print("\n  No valid video IDs found. Nothing to do.\n")
        sys.exit(0)

    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for vid in video_ids:
        if vid not in seen:
            seen.add(vid)
            unique_ids.append(vid)

    if len(unique_ids) < len(video_ids):
        print(f"\n  Removed {len(video_ids) - len(unique_ids)} duplicate(s).")

    # ---- Fetch metadata from YouTube ----
    print(f"\n  Fetching metadata for {len(unique_ids)} video(s) from YouTube API...")
    videos = fetch_video_metadata(unique_ids)

    if not videos:
        print("\n  ERROR: Could not fetch metadata for any video. Check your API key.\n")
        sys.exit(1)

    print(f"  Got metadata for {len(videos)} video(s).\n")

    # ---- Display ----
    for i, v in enumerate(videos, 1):
        print(f"  {i}. {v['title']}")
        print(f"     {v['channel']}  |  {v['publish_date']}")
        print(f"     {v['url']}")
        print()

    # ---- Save ----
    txt_file, json_file = save_results(videos, label=args.label)

    print(f"  {'=' * 56}")
    print(f"  SAVED:")
    print(f"    Text:  {txt_file}")
    print(f"    JSON:  {json_file}")
    print(f"  {'=' * 56}\n")

    # ---- Run Steps 2 + 3 ----
    if not args.skip_transcripts:
        print("  Now running Step 2 (transcript download)...")
        collect_transcripts(json_path=json_file)

        print("  Now running Step 3 (clean + chunk)...")
        clean_transcripts()

        print(f"\n  {'=' * 56}")
        print(f"  DONE — Full pipeline complete.")
        print(f"  {'=' * 56}\n")
    else:
        print("  --skip-transcripts flag set. Stopping after metadata fetch.\n")


if __name__ == "__main__":
    main()
