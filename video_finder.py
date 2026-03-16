"""
=============================================================
STEP 1: VIDEO FINDER
=============================================================
What this script does:
  - Asks you a few questions about your company and topic
  - Searches YouTube for relevant videos
  - Saves a clean list of candidate videos to a file in /output

What you need before running this:
  - A .env file with your YOUTUBE_API_KEY (see .env.example)
  - Python packages installed (run: pip install -r requirements.txt)

How to run this:
  python video_finder.py
=============================================================
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build

# -------------------------------------------------------
# LOAD YOUR SECRET API KEY
# -------------------------------------------------------
# This reads your YOUTUBE_API_KEY from the .env file
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


# -------------------------------------------------------
# HELPER: BUILD THE SEARCH QUERY
# -------------------------------------------------------
def build_search_query(company, topic, audience_type):
    """
    Combines your inputs into a single YouTube search string.
    Example: 'HubSpot CRM for small business owners'
    """
    query = f"{company} {topic}"
    if audience_type:
        query += f" for {audience_type}"
    return query


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
        return iso_date_string  # If conversion fails, return the original


# -------------------------------------------------------
# HELPER: FIGURE OUT WHY A VIDEO IS RELEVANT
# -------------------------------------------------------
def guess_relevance_reason(video_title, video_description, company, topic):
    """
    Creates a short sentence explaining why this video might be relevant.
    This is a simple keyword-based check — no AI needed at this step.
    """
    title_lower = video_title.lower()
    desc_lower = (video_description or "").lower()
    company_lower = company.lower()
    topic_lower = topic.lower()

    reasons = []

    # Check if the company name appears in the title or description
    if company_lower in title_lower:
        reasons.append(f"mentions '{company}' in the title")
    elif company_lower in desc_lower:
        reasons.append(f"mentions '{company}' in the description")

    # Check if the topic appears in the title or description
    if topic_lower in title_lower:
        reasons.append(f"covers '{topic}' in the title")
    elif topic_lower in desc_lower:
        reasons.append(f"covers '{topic}' in the description")

    # If we found specific matches, join them
    if reasons:
        return "Video " + " and ".join(reasons) + "."

    # Fallback: the search engine returned this as a match
    return f"Returned by YouTube search for '{company} {topic}'."


# -------------------------------------------------------
# MAIN FUNCTION: SEARCH YOUTUBE
# -------------------------------------------------------
def find_videos(company, topic, date_from, date_to, num_videos, audience_type):
    """
    Searches YouTube and returns a list of candidate videos.

    Parameters:
      company       - The company you are researching (e.g. 'HubSpot')
      topic         - The subject to search for (e.g. 'CRM features')
      date_from     - Start of date range, format YYYY-MM-DD (e.g. '2024-01-01')
      date_to       - End of date range, format YYYY-MM-DD (e.g. '2024-12-31')
      num_videos    - How many results you want (e.g. 10)
      audience_type - Who the content is for (e.g. 'small business owners')

    Returns:
      A list of video dictionaries, each with title, channel, url, date, reason.
    """

    # --- 1. Connect to the YouTube API ---
    youtube = build("youtube", "v3", developerKey=API_KEY)

    # --- 2. Build the search query ---
    query = build_search_query(company, topic, audience_type)
    print(f"\n  Searching YouTube for: \"{query}\"")
    print(f"  Date range: {date_from} to {date_to}")
    print(f"  Requesting up to {num_videos} videos...\n")

    # --- 3. Convert date range to the format YouTube expects ---
    # YouTube needs dates in RFC 3339 format: 2024-01-01T00:00:00Z
    published_after  = f"{date_from}T00:00:00Z"
    published_before = f"{date_to}T23:59:59Z"

    # --- 4. Call the YouTube search API ---
    search_response = youtube.search().list(
        q=query,                        # The search query
        part="snippet",                 # "snippet" gives us title, channel, date, description
        type="video",                   # Only return videos (not playlists or channels)
        maxResults=num_videos,          # How many results to fetch
        publishedAfter=published_after,
        publishedBefore=published_before,
        order="relevance",              # Sort by most relevant first
        relevanceLanguage="en",         # Prefer English-language results
    ).execute()

    # --- 5. Extract the information we care about ---
    videos = []
    items = search_response.get("items", [])

    if not items:
        print("  No videos found for that search. Try different keywords or a wider date range.")
        return []

    for item in items:
        snippet     = item["snippet"]
        video_id    = item["id"]["videoId"]
        title       = snippet.get("title", "No title")
        channel     = snippet.get("channelTitle", "Unknown channel")
        published   = snippet.get("publishedAt", "")
        description = snippet.get("description", "")
        url         = f"https://www.youtube.com/watch?v={video_id}"
        pub_date    = format_date(published)
        reason      = guess_relevance_reason(title, description, company, topic)

        videos.append({
            "title":        title,
            "channel":      channel,
            "url":          url,
            "publish_date": pub_date,
            "reason":       reason,
        })

    return videos


# -------------------------------------------------------
# HELPER: SAVE RESULTS TO A FILE
# -------------------------------------------------------
def save_results(videos, company, topic):
    """
    Saves the video list to two files in an /output folder:
      - A JSON file (machine-readable, useful for future steps)
      - A plain text file (easy for humans to read)
    """
    # Create the output folder if it doesn't exist yet
    os.makedirs("output", exist_ok=True)

    # Build a filename using the company and today's date
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = company.replace(" ", "_").lower()
    safe_topic   = topic.replace(" ", "_").lower()
    base_name    = f"output/{safe_company}_{safe_topic}_{timestamp}"

    # --- Save as JSON (for future steps to read) ---
    json_path = f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    # --- Save as plain text (easy to read now) ---
    txt_path = f"{base_name}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"VIDEO FINDER RESULTS\n")
        f.write(f"Company: {company}  |  Topic: {topic}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for i, video in enumerate(videos, start=1):
            f.write(f"{i}. {video['title']}\n")
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
    Asks the user a few simple questions in the terminal.
    Returns all inputs as a dictionary.
    """
    print("\n" + "=" * 60)
    print("  MARKET VOICE — STEP 1: VIDEO FINDER")
    print("=" * 60)
    print("  Answer the questions below. Press Enter after each one.\n")

    company      = input("  Company name (e.g. HubSpot): ").strip()
    topic        = input("  Topic to search (e.g. CRM features): ").strip()
    date_from    = input("  Start date (YYYY-MM-DD, e.g. 2024-01-01): ").strip()
    date_to      = input("  End date   (YYYY-MM-DD, e.g. 2024-12-31): ").strip()
    num_str      = input("  Number of videos to find (e.g. 10): ").strip()
    audience     = input("  Audience type (e.g. small business owners) [optional, press Enter to skip]: ").strip()

    # Convert number of videos to an integer, defaulting to 10 if invalid
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
# ENTRY POINT: RUN THE SCRIPT
# -------------------------------------------------------
if __name__ == "__main__":

    # --- Check that the API key is set ---
    if not API_KEY or API_KEY == "YOUR_KEY_HERE":
        print("\n  ERROR: No YouTube API key found.")
        print("  Please:")
        print("    1. Copy .env.example to a new file called  .env")
        print("    2. Open .env and replace YOUR_KEY_HERE with your real API key")
        print("    3. Run this script again\n")
        exit(1)

    # --- Collect inputs ---
    inputs = get_user_inputs()

    # --- Search YouTube ---
    videos = find_videos(
        company       = inputs["company"],
        topic         = inputs["topic"],
        date_from     = inputs["date_from"],
        date_to       = inputs["date_to"],
        num_videos    = inputs["num_videos"],
        audience_type = inputs["audience_type"],
    )

    # --- Show and save results ---
    if videos:
        print(f"  Found {len(videos)} video(s).\n")
        print("  " + "-" * 56)

        for i, v in enumerate(videos, start=1):
            print(f"\n  {i}. {v['title']}")
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
    else:
        print("\n  No results to save. Try adjusting your inputs.\n")
