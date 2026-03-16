# Market Voice — Step 1: Video Finder

This is **Step 1** of the Market Voice project. Its only job is to find relevant YouTube videos about a company and topic, and give you a clean list to review.

No transcripts. No summaries. Just a list of videos. That comes in later steps.

---

## What Files Were Created

| File | What It Does |
|------|-------------|
| `video_finder.py` | The main script. You run this to search YouTube. |
| `requirements.txt` | A list of Python packages this project needs. You install these once. |
| `.env.example` | A template showing where to put your YouTube API key. You copy this and rename it to `.env`. |
| `.gitignore` | Tells git which files to ignore (like your private `.env` file). |
| `README.md` | This file. Explains everything. |

When you run the script, it will create an `output/` folder and save your results there.

---

## Before You Run This — One-Time Setup

You only need to do these steps once.

### Step A: Make sure Python is installed

Open your Terminal (Mac) or Command Prompt (Windows) and type:

```
python --version
```

If you see something like `Python 3.9.x` or higher, you're good.
If you get an error, download Python from [https://www.python.org/downloads/](https://www.python.org/downloads/) and install it.

---

### Step B: Install the required packages

In your Terminal, go to this project folder and run:

```
pip install -r requirements.txt
```

This installs two small packages that let Python talk to YouTube.

---

### Step C: Get a free YouTube API key

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/) and sign in with a Google account
2. Click **"Select a project"** at the top → then **"New Project"**
3. Name it anything (e.g. `market-voice`) and click **Create**
4. In the search bar at the top, type `YouTube Data API v3` and click on it
5. Click the blue **"Enable"** button
6. In the left menu, go to **APIs & Services → Credentials**
7. Click **"+ Create Credentials"** → choose **"API key"**
8. Copy the key that appears (it looks like a long string of letters and numbers)

This API key is **free**. Google gives you 10,000 search units per day at no cost, which is more than enough.

---

### Step D: Add your API key to the project

1. Find the file called `.env.example` in this folder
2. Make a **copy** of it
3. Rename the copy to just `.env` (remove the word "example")
4. Open `.env` in any text editor (Notepad works fine)
5. Replace `YOUR_KEY_HERE` with the API key you copied in Step C
6. Save the file

Your `.env` file should look like this (with your real key):

```
YOUTUBE_API_KEY=AIzaSyD_your_actual_key_here
```

> **Important:** Never share this file or post it publicly. It is your private key.

---

## How to Run Step 1

Once the setup is done, running the script is simple.

1. Open your Terminal
2. Navigate to this project folder. For example:
   ```
   cd /path/to/market-voice-youtube
   ```
3. Run the script:
   ```
   python video_finder.py
   ```
4. The script will ask you a few questions — just type your answers and press Enter:

   ```
   Company name: HubSpot
   Topic to search: CRM features
   Start date (YYYY-MM-DD): 2024-01-01
   End date (YYYY-MM-DD): 2024-12-31
   Number of videos to find: 10
   Audience type (optional): small business owners
   ```

5. It will search YouTube and print the results in your Terminal

---

## Where to See the Output

After running the script, two files are saved in a folder called `output/` inside your project:

| File type | What it is |
|-----------|-----------|
| `.txt` file | A plain, readable list of videos — open this to review results |
| `.json` file | The same data in a structured format — used by future steps |

The filename includes your company name and the date/time you ran it. For example:

```
output/hubspot_crm_features_20240315_143022.txt
output/hubspot_crm_features_20240315_143022.json
```

Open the `.txt` file in any text editor to see your video list. Each entry looks like this:

```
1. HubSpot CRM Full Tutorial 2024 | Everything You Need to Know
   Channel:  HubSpot
   URL:      https://www.youtube.com/watch?v=abc123xyz
   Date:     2024-03-10
   Why:      Video mentions 'HubSpot' in the title and covers 'CRM features' in the title.
```

---

## Tips

- **Date range:** Narrower date ranges return fewer but more timely results. Start with 3–6 months.
- **Number of videos:** 10–20 is a good starting point. YouTube allows up to 50 per search.
- **Topic:** Be specific. `CRM onboarding` returns better results than just `software`.
- **Audience type:** This is optional. Adding it (e.g. `enterprise sales teams`) refines the search.

---

## What Comes Next (Future Steps)

This is only Step 1. Here is how the full workflow will grow:

| Step | What It Does |
|------|-------------|
| **Step 1 (this)** | Find relevant YouTube videos |
| Step 2 | Collect transcripts from those videos |
| Step 3 | Summarize what people are saying |
| Step 4 | Extract key insights by audience and topic |
| Step 5 | Generate a Market Voice report |

Each step builds on the output from the previous one. The `.json` file you generate in Step 1 will be the input for Step 2.

---

## Need Help?

If something isn't working:
- Double-check that your `.env` file exists and has a real API key (not `YOUR_KEY_HERE`)
- Make sure you ran `pip install -r requirements.txt`
- Make sure your date format is `YYYY-MM-DD` (e.g. `2024-01-01`)
- Make sure you have an internet connection when you run the script
