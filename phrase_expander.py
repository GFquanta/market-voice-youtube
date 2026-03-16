"""
=============================================================
STEP 1A: SEARCH PHRASE EXPANDER
=============================================================
What this module does:
  - Takes your inputs (company, topic, audience, date range)
  - Generates 6 smart YouTube search phrases (max 8)
  - If you have an ANTHROPIC_API_KEY in your .env, it uses
    Claude to generate intelligent, varied phrases
  - If not, it falls back to simple rule-based templates
    that still work well

This module is called automatically by video_finder.py.
You do not run this file directly.
=============================================================
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Which Claude model to use — configurable in your .env file.
# Defaults to claude-haiku-4-5 (fast and low-cost).
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

# How many phrases to generate
DEFAULT_PHRASE_COUNT = 6
MAX_PHRASE_COUNT     = 8


# -------------------------------------------------------
# FALLBACK: RULE-BASED PHRASE GENERATOR
# -------------------------------------------------------
def generate_phrases_rule_based(company, topic, audience_type):
    """
    Generates search phrases using simple templates.
    Used when no Anthropic API key is available.

    If company is blank, generates topic-only phrases.
    If company is provided, combines company + topic.
    """
    # Choose the right prefix depending on whether we have a company
    if company:
        base = f"{company} {topic}"
    else:
        base = topic

    # Build a list of template phrases
    templates = [
        f"{base} review",
        f"{base} problems",
        f"{base} walkthrough",
        f"{base} experience",
        f"{base} pros and cons",
        f"{base} tutorial",
        f"{base} guide",
        f"{base} tips",
    ]

    # Add audience-specific phrase if provided
    if audience_type and company:
        templates.insert(0, f"{company} {topic} for {audience_type}")
    elif audience_type:
        templates.insert(0, f"{topic} for {audience_type}")

    # Return only up to MAX_PHRASE_COUNT phrases
    return templates[:MAX_PHRASE_COUNT]


# -------------------------------------------------------
# MAIN: CLAUDE-POWERED PHRASE GENERATOR
# -------------------------------------------------------
def generate_phrases_with_claude(company, topic, audience_type, date_from, date_to):
    """
    Uses the Claude API to generate smart, varied YouTube search phrases.
    Called only when ANTHROPIC_API_KEY is set in .env.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Build the context string that Claude will use
    if company:
        context = f"Company: {company}\nTopic: {topic}"
    else:
        context = f"Topic: {topic}"

    if audience_type:
        context += f"\nTarget audience: {audience_type}"

    context += f"\nDate range of interest: {date_from} to {date_to}"

    # Instructions for Claude
    prompt = f"""You are helping someone find relevant YouTube videos.

Given these inputs:
{context}

Generate exactly {DEFAULT_PHRASE_COUNT} YouTube search phrases that someone would use to find videos on this topic.

Rules:
- Each phrase should be specific and search-ready (not a sentence, just a search phrase)
- Vary the angle: include reviews, tutorials, comparisons, walkthroughs, honest opinions
- Keep phrases tight and relevant — do NOT be broad or generic
- If a company is provided, most phrases should include it
- If no company is provided, focus on the topic only
- Do NOT include dates in the phrases
- Return ONLY the phrases, one per line, with no numbering, bullets, or extra text
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,   # Phrases are short — 300 tokens is plenty
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Extract the text response
    raw_text = response.content[0].text.strip()

    # Split into individual phrases, clean up blank lines
    phrases = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Cap at MAX_PHRASE_COUNT just in case Claude returns more
    return phrases[:MAX_PHRASE_COUNT]


# -------------------------------------------------------
# PUBLIC FUNCTION: CALLED BY video_finder.py
# -------------------------------------------------------
def expand_search_phrases(company, topic, audience_type, date_from, date_to):
    """
    Main entry point for phrase expansion.
    Automatically picks Claude or rule-based depending on your .env setup.

    Returns a list of search phrase strings.
    """
    if ANTHROPIC_API_KEY:
        print(f"  [Step 1A] Generating search phrases using Claude ({CLAUDE_MODEL})...")
        try:
            phrases = generate_phrases_with_claude(
                company, topic, audience_type, date_from, date_to
            )
            print(f"  [Step 1A] Claude generated {len(phrases)} phrases.\n")
            return phrases
        except Exception as e:
            # If Claude call fails for any reason, fall back gracefully
            print(f"  [Step 1A] Claude call failed ({e}). Falling back to rule-based phrases.\n")
            return generate_phrases_rule_based(company, topic, audience_type)
    else:
        print("  [Step 1A] No ANTHROPIC_API_KEY found — using rule-based phrase templates.\n")
        return generate_phrases_rule_based(company, topic, audience_type)
