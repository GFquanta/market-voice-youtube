# Market Voice — Step 1: Video Finder

This is **Step 1** of the Market Voice project. Its only job is to find relevant YouTube videos about a company and topic, and give you a clean ranked list to review.

Step 1 now has two sub-steps that run automatically back to back:

- **Step 1A — Search Phrase Expander:** Generates 6 smart YouTube search phrases from your inputs
- **Step 1B — Video Finder:** Searches YouTube once per phrase, removes duplicates, and ranks results

No transcripts. No summaries. Just a list of videos. That comes in later steps.

---

## What Files Were Created

| File | What It Does |
|------|-------------|
| `video_finder.py` | The main script. You run this. It handles both Step 1A and Step 1B automatically. |
| `phrase_expander.py` | Step 1A logic. Generates search phrases. Called by `video_finder.py` — you don't run this directly. |
| `requirements.txt` | A list of Python packages this project needs. You install these once. |
| `.env.example` | A template showing where to put your API keys. You copy this and rename it to `.env`. |
| `.gitignore` | Tells git which files to ignore (like your private `.env` file). |
| `README.md` | This file. |

When you run the script, it creates an `output/` folder and saves your results there.

---

## How Step 1 Now Works (Plain English)

**Before this upgrade**, the script built one search phrase from your inputs (e.g. `HubSpot CRM features`) and searched YouTube once.

**Now**, it works like this:

1. You answer the same 6 questions as before
2. **Step 1A** generates 6 search phrases from your inputs, for example:
   - `HubSpot CRM honest review 2024`
   - `HubSpot CRM pros and cons`
   - `HubSpot CRM walkthrough tutorial`
   - `HubSpot CRM for small business owners`
   - `HubSpot CRM problems experience`
   - `HubSpot vs competitors CRM`
3. **Step 1B** searches YouTube once for each phrase, collecting ~4 videos per search
4. Duplicates are removed (the same video appearing in multiple searches is kept once)
5. Videos found by more than one phrase are ranked higher — that's a strong signal of relevance
6. The final list is trimmed to your requested count and saved

This catches videos that a single search would miss, without any extra work from you.

---

## Smart Mode vs. Fallback Mode

### Smart mode (with Claude)
If you add an `ANTHROPIC_API_KEY` to your `.env`, Step 1A uses Claude to generate phrases that are varied, specific, and intelligent.

### Fallback mode (no Claude key)
If you skip the Anthropic key, Step 1A uses simple templates:
- `{company} {topic} review`
- `{company} {topic} problems`
- `{company} {topic} walkthrough`
- `{company} {topic} experience`
- `{company} {topic} pros and cons`
- `{company} {topic} tutorial`

**The script works either way.** Claude just makes the phrases smarter.

---

## Before You Run This — One-Time Setup

You only need to do these steps once.

### Step A: Make sure Python is installed

Open your Terminal (Mac) or Command Prompt (Windows) and type:

```
python --version
```

If you see `Python 3.9.x` or higher, you're good. If not, download it from [https://www.python.org/downloads/](https://www.python.org/downloads/).

---

### Step B: Install the required packages

```
pip install -r requirements.txt
```

---

### Step C: Get a free YouTube API key (required)

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/) and sign in
2. Click **"Select a project"** → **"New Project"** → name it anything → click **Create**
3. In the search bar, type `YouTube Data API v3` and click on it
4. Click the blue **"Enable"** button
5. Go to **APIs & Services → Credentials → + Create Credentials → API key**
6. Copy the key that appears

---

### Step D: Get an Anthropic API key (optional but recommended)

This enables smarter phrase generation. Skip it if you want to keep things simple for now.

1. Go to [https://console.anthropic.com/](https://console.anthropic.com/) and sign up
2. Go to **API Keys → Create Key**
3. Copy the key

---

### Step E: Create your `.env` file

1. Find the file called `.env.example` in this folder
2. Make a copy of it and rename the copy to `.env`
3. Open `.env` in any text editor
4. Fill in your keys:

```
YOUTUBE_API_KEY=your_youtube_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here   ← optional, delete this line if skipping
CLAUDE_MODEL=claude-haiku-4-5               ← optional, controls which Claude model is used
```

> **Important:** Never share your `.env` file. It contains private keys.

---

## How to Run Step 1

```
python video_finder.py
```

Answer the prompts:

```
  Company name (optional): HubSpot
  Topic to search: CRM features
  Start date (YYYY-MM-DD): 2024-01-01
  End date (YYYY-MM-DD): 2024-12-31
  Number of videos to find: 15
  Audience type (optional): small business owners
```

The script will show you:
1. The 6 search phrases it generated (Step 1A)
2. Each YouTube search as it runs (Step 1B)
3. The final ranked video list in your terminal

---

## Where to See the Output

After running, two files are saved in `output/`:

| File type | What it is |
|-----------|-----------|
| `.txt` file | A plain, readable list of videos — open this to review results |
| `.json` file | The same data in a structured format — used by future steps |

Example filename:
```
output/hubspot_crm_features_20240315_143022.txt
```

Each entry in the `.txt` file looks like this:

```
1. HubSpot CRM Full Tutorial 2024 [found by 3 search phrases]
   Channel:  HubSpot
   URL:      https://www.youtube.com/watch?v=abc123xyz
   Date:     2024-03-10
   Why:      Video mentions 'HubSpot' in the title and found by 3 different search phrases.
```

The `[found by X search phrases]` note means that video was returned by multiple different searches — a good signal that it's highly relevant.

---

## Configuring the Claude Model

If you're using the Anthropic API, you can control which Claude model is used by setting `CLAUDE_MODEL` in your `.env` file:

| Setting | Speed | Cost | Best for |
|---------|-------|------|----------|
| `claude-haiku-4-5` (default) | Fast | Lowest | Everyday use |
| `claude-sonnet-4-6` | Medium | Moderate | Better phrase quality |
| `claude-opus-4-6` | Slower | Higher | Maximum quality |

For phrase generation, the default (`claude-haiku-4-5`) is more than good enough.

---

## Tips

- **Date range:** 3–6 months gives focused, timely results
- **Number of videos:** 10–20 is a good starting point
- **Topic:** Be specific. `CRM onboarding` beats `software`
- **Company is optional:** Leave it blank to search by topic only
- **Audience type:** Optional but helps Claude generate more targeted phrases

---

## What Comes Next (Future Steps)

| Step | What It Does |
|------|-------------|
| **Step 1 (this)** | Find relevant YouTube videos |
| Step 2 | Collect transcripts from those videos |
| Step 3 | Summarize what people are saying |
| Step 4 | Extract key insights by audience and topic |
| Step 5 | Generate a Market Voice report |

The `.json` file you generate in Step 1 will be the input for Step 2.

---

## Need Help?

If something isn't working:
- Make sure your `.env` file exists (not `.env.example`) and has a real YouTube API key
- Make sure you ran `pip install -r requirements.txt`
- Make sure dates are in `YYYY-MM-DD` format (e.g. `2024-01-01`)
- Make sure you have an internet connection when you run the script
- If Claude phrase generation fails, the script automatically falls back to rule-based phrases — check the terminal output for a notice
