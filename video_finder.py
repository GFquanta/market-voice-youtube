"""
=============================================================
STEP 1: VIDEO FINDER  (Step 1A + Step 1B)
=============================================================
What this script does:
  Step 1A — SEARCH PHRASE EXPANDER
    Generates 6 smart YouTube search phrases from your inputs.
    Uses Claude if you have an ANTHROPIC_API_KEY, otherwise
    falls back to simple rule-based phrase templates.

  Step 1B — VIDEO FINDER
    Searches YouTube once per phrase (3-5 videos each).
    Removes duplicate videos.
    Ranks videos that appeared in more searches higher.
    Saves a clean list of the top results to /output.

What you need before running this:
  - A .env file with YOUTUBE_API_KEY (required)
  - ANTHROPIC_API_KEY in .env is optional but improves phrase quality
  - Python packages installed: pip install -r requirements.txt

How to run:
  python video_finder.py
=============================================================
"""

import os
import json
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Import our Step 1A phrase expander
from phrase_expander import expand_search_phrases

# Import Step 2 transcript collector
from transcript_collector import collect_transcripts

# Import Step 3 transcript cleaner
from transcript_cleaner import clean_transcripts

# -------------------------------------------------------
# LOAD SECRET API KEYS
# -------------------------------------------------------
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# How many videos to fetch per search phrase (3-5 is the sweet spot)
VIDEOS_PER_PHRASE = 4


# -------------------------------------------------------
# HELPER: CONVERT ISO DATE TO A READABLE FORMAT
# -------------------------------------------------------
def format_date(iso_date_string):
    """
    YouTube returns dates like '2024-03-15T12:00:00Z'.
    This converts that to '2024-03-15' which is easier to read.
    """
    try:
        dt = datetime.fromisoformat(iso_date_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_date_string


# -------------------------------------------------------
# HELPER: FIGURE OUT WHY A VIDEO IS RELEVANT
# -------------------------------------------------------
def guess_relevance_reason(video_title, video_description, company, topic, matched_phrases):
    """
    Creates a short sentence explaining why this video is relevant.
    Also notes how many different search phrases found it.
    """
    title_lower = video_title.lower()
    desc_lower  = (video_description or "").lower()
    reasons     = []

    if company:
        company_lower = company.lower()
        if company_lower in title_lower:
            reasons.append(f"mentions '{company}' in the title")
        elif company_lower in desc_lower:
            reasons.append(f"mentions '{company}' in the description")

    topic_lower = topic.lower()
    if topic_lower in title_lower:
        reasons.append(f"covers '{topic}' in the title")
    elif topic_lower in desc_lower:
        reasons.append(f"covers '{topic}' in the description")

    # Note if multiple phrases found this video — a strong signal of relevance
    if matched_phrases > 1:
        reasons.append(f"found by {matched_phrases} different search phrases")

    if reasons:
        return "Video " + " and ".join(reasons) + "."

    base = f"{company} {topic}" if company else topic
    return f"Returned by YouTube search for '{base}'."


# -------------------------------------------------------
# STEP 1B: SEARCH YOUTUBE FOR ONE PHRASE
# -------------------------------------------------------
def search_one_phrase(youtube, phrase, date_from, date_to):
    """
    Runs a single YouTube search for the given phrase.
    Returns a list of raw result items from the API.
    """
    published_after  = f"{date_from}T00:00:00Z"
    published_before = f"{date_to}T23:59:59Z"

    try:
        response = youtube.search().list(
            q=phrase,
            part="snippet",
            type="video",
            maxResults=VIDEOS_PER_PHRASE,
            publishedAfter=published_after,
            publishedBefore=published_before,
            order="relevance",
            relevanceLanguage="en",
        ).execute()
        return response.get("items", [])
    except Exception as e:
        print(f"    Warning: search failed for phrase '{phrase}': {e}")
        return []


# -------------------------------------------------------
# MAIN FUNCTION: RUN ALL SEARCHES AND COMBINE RESULTS
# -------------------------------------------------------
def find_videos(company, topic, date_from, date_to, num_videos, audience_type):
    """
    Orchestrates Step 1A (phrase expansion) and Step 1B (YouTube searches).

    1. Generates search phrases via phrase_expander.py
    2. Runs one YouTube search per phrase
    3. Deduplicates by video ID
    4. Ranks by how many phrases found each video
    5. Returns the top num_videos results
    """

    # --- Step 1A: Generate search phrases ---
    phrases = expand_search_phrases(company, topic, audience_type, date_from, date_to)

    print("  Search phrases that will be used:")
    for i, p in enumerate(phrases, 1):
        print(f"    {i}. {p}")
    print()

    # --- Step 1B: Connect to YouTube and run all searches ---
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    print(f"  [Step 1B] Searching YouTube with {len(phrases)} phrase(s)...")
    print(f"  Date range: {date_from} to {date_to}\n")

    # We track each video by its ID so we can deduplicate.
    # video_data    — stores the raw info for each unique video ID
    # phrase_hits   — counts how many phrases found each video ID
    video_data  = {}
    phrase_hits = defaultdict(int)

    for phrase in phrases:
        print(f"    Searching: \"{phrase}\"")
        items = search_one_phrase(youtube, phrase, date_from, date_to)

        for item in items:
            video_id = item["id"]["videoId"]
            phrase_hits[video_id] += 1        # Increment hit count each time a phrase finds it

            # Only store the video data once (first time we see it)
            if video_id not in video_data:
                video_data[video_id] = item

    print(f"\n  Found {len(video_data)} unique video(s) across all searches.")

    if not video_data:
        print("  No videos found. Try different keywords or a wider date range.")
        return []

    # --- Rank: videos found by more phrases rank higher ---
    # Sort descending by phrase_hits count, then by publish date (newest first)
    def rank_key(video_id):
        hits      = phrase_hits[video_id]
        snippet   = video_data[video_id]["snippet"]
        pub_date  = snippet.get("publishedAt", "")
        return (hits, pub_date)

    ranked_ids = sorted(video_data.keys(), key=rank_key, reverse=True)

    # --- Build the final output list ---
    videos = []
    for video_id in ranked_ids[:num_videos]:
        item        = video_data[video_id]
        snippet     = item["snippet"]
        title       = snippet.get("title", "No title")
        channel     = snippet.get("channelTitle", "Unknown channel")
        published   = snippet.get("publishedAt", "")
        description = snippet.get("description", "")
        url         = f"https://www.youtube.com/watch?v={video_id}"
        pub_date    = format_date(published)
        hits        = phrase_hits[video_id]
        reason      = guess_relevance_reason(title, description, company, topic, hits)

        videos.append({
            "title":          title,
            "channel":        channel,
            "url":            url,
            "publish_date":   pub_date,
            "phrase_matches": hits,      # How many phrases surfaced this video
            "reason":         reason,
        })

    return videos


# -------------------------------------------------------
# HELPER: SAVE RESULTS TO /output
# -------------------------------------------------------
def save_results(videos, company, topic):
    """
    Saves the video list to two files in an /output folder:
      - A .txt file  — easy for humans to read
      - A .json file — structured data for future steps
    """
    os.makedirs("output", exist_ok=True)

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = (company or "no_company").replace(" ", "_").lower()
    safe_topic   = topic.replace(" ", "_").lower()
    base_name    = f"output/{safe_company}_{safe_topic}_{timestamp}"

    # --- JSON file ---
    json_path = f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    # --- Plain text file ---
    txt_path = f"{base_name}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("VIDEO FINDER RESULTS\n")
        f.write(f"Company: {company or '(none)'}  |  Topic: {topic}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for i, video in enumerate(videos, start=1):
            matches = video.get("phrase_matches", 1)
            match_note = f" [found by {matches} search phrase(s)]" if matches > 1 else ""
            f.write(f"{i}. {video['title']}{match_note}\n")
            f.write(f"   Channel:  {video['channel']}\n")
            f.write(f"   URL:      {video['url']}\n")
            f.write(f"   Date:     {video['publish_date']}\n")
            f.write(f"   Why:      {video['reason']}\n")
            f.write("\n")

    return txt_path, json_path


# -------------------------------------------------------
# COLLECT INPUTS FROM THE USER
# -------------------------------------------------------
def get_user_inputs():
    """
    Asks you a few simple questions in the terminal.
    Returns all inputs as a dictionary.
    """
    print("\n" + "=" * 60)
    print("  MARKET VOICE — STEP 1: VIDEO FINDER")
    print("  (Step 1A: phrase expansion + Step 1B: YouTube search)")
    print("=" * 60)
    print("  Answer the questions below. Press Enter after each one.\n")

    company   = input("  Company name (optional — press Enter to skip): ").strip()
    topic     = input("  Topic to search (e.g. CRM features): ").strip()
    date_from = input("  Start date (YYYY-MM-DD, e.g. 2024-01-01): ").strip()
    date_to   = input("  End date   (YYYY-MM-DD, e.g. 2024-12-31): ").strip()
    num_str   = input("  Number of videos to find (e.g. 10): ").strip()
    audience  = input("  Audience type (e.g. small business owners) [optional, press Enter to skip]: ").strip()

    try:
        num_videos = int(num_str)
        if num_videos < 1 or num_videos > 50:
            print("  (Capping video count between 1 and 50. Using 10.)")
            num_videos = 10
    except ValueError:
        print("  (Could not read that number. Defaulting to 10 videos.)")
        num_videos = 10

    return {
        "company":       company,
        "topic":         topic,
        "date_from":     date_from,
        "date_to":       date_to,
        "num_videos":    num_videos,
        "audience_type": audience,
    }


# -------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------
if __name__ == "__main__":

    # Check that YouTube API key is present
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "YOUR_KEY_HERE":
        print("\n  ERROR: No YouTube API key found.")
        print("  Please:")
        print("    1. Copy .env.example to a new file called .env")
        print("    2. Open .env and replace YOUR_KEY_HERE with your real YouTube API key")
        print("    3. Run this script again\n")
        exit(1)

    # Collect inputs
    inputs = get_user_inputs()

    # Run Steps 1A + 1B
    videos = find_videos(
        company       = inputs["company"],
        topic         = inputs["topic"],
        date_from     = inputs["date_from"],
        date_to       = inputs["date_to"],
        num_videos    = inputs["num_videos"],
        audience_type = inputs["audience_type"],
    )

    # Display and save results
    if videos:
        print(f"\n  Top {len(videos)} video(s) after deduplication and ranking:\n")
        print("  " + "-" * 56)

        for i, v in enumerate(videos, start=1):
            matches = v.get("phrase_matches", 1)
            match_note = f"  ★ found by {matches} phrases" if matches > 1 else ""
            print(f"\n  {i}. {v['title']}{match_note}")
            print(f"     Channel: {v['channel']}")
            print(f"     URL:     {v['url']}")
            print(f"     Date:    {v['publish_date']}")
            print(f"     Why:     {v['reason']}")

        txt_file, json_file = save_results(
            videos,
            inputs["company"],
            inputs["topic"],
        )

        print("\n  " + "=" * 56)
        print("  RESULTS SAVED TO:")
        print(f"    Readable text:  {txt_file}")
        print(f"    Machine JSON:   {json_file}")
        print("  " + "=" * 56 + "\n")

        # --- Run Step 2: collect transcripts for all found videos ---
        collect_transcripts(json_path=json_file)

        # --- Run Step 3: clean and chunk all transcripts ---
        clean_transcripts()

    else:
        print("\n  No results to save. Try adjusting your inputs.\n")
