#!/usr/bin/env python3
"""
Patent Scanner — Market Voice Module

Searches USPTO patents for a given company and date range.
Uses the PatentsView API (free, requires API key registration).
Also generates Google Patents links for visual cross-reference.

PatentsView API key registration (free):
  https://patentsview.org/apis/keyrequest

Usage:
  python patent_scanner.py

  Or with command-line args:
  python patent_scanner.py --company "Fiserv" --start 2026-02-01 --end 2026-02-28

Output:
  output/patents_fiserv_20260301_143022.txt   (human-readable report)
  output/patents_fiserv_20260301_143022.json  (structured data)
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv()

PATENTSVIEW_API_BASE = "https://search.patentsview.org/api/v1"
PATENTSVIEW_API_KEY = os.getenv("PATENTSVIEW_API_KEY", "")

# Fields to retrieve for granted patents
PATENT_FIELDS = [
    "patent_id",
    "patent_title",
    "patent_date",
    "patent_abstract",
    "patent_type",
    "assignees.assignee_organization",
    "assignees.assignee_country",
    "inventors.inventor_name_first",
    "inventors.inventor_name_last",
    "cpc_current.cpc_group_id",
    "cpc_current.cpc_group_title",
    "application.filing_date",
]

# Fields for published applications (pre-grant)
APPLICATION_FIELDS = [
    "patent_id",
    "patent_title",
    "patent_date",
    "patent_abstract",
    "patent_type",
    "assignees.assignee_organization",
    "inventors.inventor_name_first",
    "inventors.inventor_name_last",
    "application.filing_date",
]

# How many results per page (max 1000)
PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# PatentsView API helpers
# ---------------------------------------------------------------------------

def build_query(company_name, start_date, end_date):
    """Build a PatentsView query JSON for a company + date range."""
    return {
        "_and": [
            {"_contains": {"assignees.assignee_organization": company_name.lower()}},
            {"_gte": {"patent_date": start_date}},
            {"_lte": {"patent_date": end_date}},
        ]
    }


def query_patentsview(endpoint, query, fields, page_size=PAGE_SIZE):
    """
    Query the PatentsView API and handle pagination.
    Returns a list of patent records.
    """
    url = f"{PATENTSVIEW_API_BASE}/{endpoint}/"

    headers = {"Accept": "application/json"}
    if PATENTSVIEW_API_KEY:
        headers["X-Api-Key"] = PATENTSVIEW_API_KEY

    all_results = []
    offset = 0

    while True:
        params = {
            "q": json.dumps(query),
            "f": json.dumps(fields),
            "s": json.dumps([{"patent_date": "desc"}]),
            "o": json.dumps({"size": page_size, "offset": offset}),
        }

        print(f"  Querying {endpoint} (offset {offset})...")

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"  ERROR: Network request failed: {e}")
            break

        if resp.status_code == 401:
            print("\n  ERROR: API key is missing or invalid.")
            print("  Register for a free key at: https://patentsview.org/apis/keyrequest")
            print("  Then add PATENTSVIEW_API_KEY=your_key to your .env file.\n")
            sys.exit(1)

        if resp.status_code == 429:
            print("  Rate limited. Waiting 10 seconds...")
            time.sleep(10)
            continue

        if resp.status_code != 200:
            print(f"  ERROR: API returned status {resp.status_code}")
            try:
                print(f"  Response: {resp.text[:500]}")
            except Exception:
                pass
            break

        data = resp.json()

        # The API returns {"patents": [...], "count": N, "total_patent_count": N}
        patents = data.get("patents", [])
        if not patents:
            break

        all_results.extend(patents)
        total = data.get("total_patent_count", len(all_results))

        print(f"  Got {len(patents)} results (total available: {total})")

        if len(all_results) >= total or len(patents) < page_size:
            break

        offset += page_size
        time.sleep(0.5)  # Be polite to the API

    return all_results


# ---------------------------------------------------------------------------
# Google Patents URL generator
# ---------------------------------------------------------------------------

def google_patents_search_url(company_name, start_date, end_date):
    """Generate a Google Patents search URL for the same query."""
    # Google Patents date format: YYYYMMDD
    start_gp = start_date.replace("-", "")
    end_gp = end_date.replace("-", "")

    params = {
        "assignee": company_name,
        "after": f"priority:{start_gp}",
        "before": f"priority:{end_gp}",
        "type": "PATENT",
        "language": "ENGLISH",
    }
    return "https://patents.google.com/?" + urllib.parse.urlencode(params)


def google_patents_link(patent_id):
    """Generate a direct Google Patents link for a single patent."""
    # PatentsView IDs look like "12345678" — Google Patents wants "US12345678"
    clean_id = patent_id.replace(",", "")
    if not clean_id.startswith("US"):
        clean_id = f"US{clean_id}"
    return f"https://patents.google.com/patent/{clean_id}"


# ---------------------------------------------------------------------------
# Data processing
# ---------------------------------------------------------------------------

def extract_patent_info(patent):
    """Extract clean info from a PatentsView patent record."""
    patent_id = patent.get("patent_id", "N/A")

    # Inventors
    inventors = []
    for inv in patent.get("inventors", []):
        first = inv.get("inventor_name_first", "")
        last = inv.get("inventor_name_last", "")
        name = f"{first} {last}".strip()
        if name:
            inventors.append(name)

    # Assignees
    assignees = []
    for a in patent.get("assignees", []):
        org = a.get("assignee_organization", "")
        if org:
            assignees.append(org)

    # CPC classifications
    cpcs = []
    for c in patent.get("cpc_current", []):
        group_id = c.get("cpc_group_id", "")
        group_title = c.get("cpc_group_title", "")
        if group_id:
            cpcs.append({"code": group_id, "title": group_title})

    # Filing date
    app = patent.get("application", {})
    filing_date = app.get("filing_date", "N/A") if app else "N/A"

    return {
        "patent_id": patent_id,
        "title": patent.get("patent_title", "N/A"),
        "grant_date": patent.get("patent_date", "N/A"),
        "filing_date": filing_date,
        "type": patent.get("patent_type", "N/A"),
        "abstract": patent.get("patent_abstract", "N/A"),
        "inventors": inventors,
        "assignees": assignees,
        "cpc_classifications": cpcs,
        "google_patents_url": google_patents_link(patent_id),
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_text_report(company, start_date, end_date, patents_data, google_url):
    """Generate a human-readable .txt report."""
    lines = []
    lines.append("=" * 70)
    lines.append("PATENT SCANNER — MARKET VOICE")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Company:       {company}")
    lines.append(f"  Date range:    {start_date} to {end_date}")
    lines.append(f"  Patents found: {len(patents_data)}")
    lines.append(f"  Report date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"  Google Patents cross-reference:")
    lines.append(f"  {google_url}")
    lines.append("")
    lines.append("-" * 70)

    if not patents_data:
        lines.append("")
        lines.append("  No patents found for this company in the specified date range.")
        lines.append("")
        lines.append("  This could mean:")
        lines.append("  - No patents were granted in this period (check applications)")
        lines.append("  - The company name may differ on filings (subsidiaries, etc.)")
        lines.append("  - Try broadening the date range")
        lines.append("")
    else:
        for i, p in enumerate(patents_data, 1):
            lines.append("")
            lines.append(f"{i}. {p['title']}")
            lines.append(f"   Patent #:    {p['patent_id']}")
            lines.append(f"   Type:        {p['type']}")
            lines.append(f"   Grant date:  {p['grant_date']}")
            lines.append(f"   Filed:       {p['filing_date']}")
            lines.append(f"   Assignee(s): {', '.join(p['assignees']) if p['assignees'] else 'N/A'}")
            lines.append(f"   Inventor(s): {', '.join(p['inventors']) if p['inventors'] else 'N/A'}")

            # CPC classifications (show top 3)
            if p.get("cpc_classifications"):
                cpcs = p["cpc_classifications"][:3]
                lines.append(f"   Tech areas:  {'; '.join(c['title'] or c['code'] for c in cpcs)}")

            lines.append(f"   Google:      {p['google_patents_url']}")

            # Abstract (truncated for readability)
            abstract = p.get("abstract", "")
            if abstract and abstract != "N/A":
                if len(abstract) > 300:
                    abstract = abstract[:300] + "..."
                lines.append(f"   Abstract:    {abstract}")

            lines.append("")
            lines.append("   " + "-" * 60)

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def get_inputs():
    """Get search parameters from user or command-line args."""
    parser = argparse.ArgumentParser(description="Patent Scanner — Market Voice")
    parser.add_argument("--company", type=str, help="Company name to search")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--also-search", type=str, nargs="*",
                        help="Additional company names / subsidiaries to include")

    args = parser.parse_args()

    # Interactive mode if no args
    if not args.company:
        print("\n  PATENT SCANNER — Market Voice")
        print("  " + "-" * 40)
        company = input("  Company name: ").strip()
        start_date = input("  Start date (YYYY-MM-DD): ").strip()
        end_date = input("  End date (YYYY-MM-DD): ").strip()

        also = input("  Also search subsidiaries/brands (comma-separated, or Enter to skip): ").strip()
        also_search = [s.strip() for s in also.split(",") if s.strip()] if also else []
    else:
        company = args.company
        start_date = args.start
        end_date = args.end
        also_search = args.also_search or []

    if not company or not start_date or not end_date:
        print("  ERROR: Company name, start date, and end date are all required.")
        sys.exit(1)

    return company, start_date, end_date, also_search


def main():
    company, start_date, end_date, also_search = get_inputs()

    # Combine company names to search
    search_names = [company] + also_search

    print(f"\n  Searching patents for: {', '.join(search_names)}")
    print(f"  Date range: {start_date} to {end_date}")
    print()

    # Check for API key
    if not PATENTSVIEW_API_KEY:
        print("  WARNING: No PATENTSVIEW_API_KEY found in .env file.")
        print("  The API may reject requests without a key.")
        print("  Register for free at: https://patentsview.org/apis/keyrequest")
        print()

    # Query for each company name
    all_raw_patents = []
    seen_ids = set()

    for name in search_names:
        print(f"  --- Searching: {name} ---")
        query = build_query(name, start_date, end_date)
        results = query_patentsview("patent", query, PATENT_FIELDS)

        for p in results:
            pid = p.get("patent_id", "")
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_raw_patents.append(p)

        print(f"  Found {len(results)} patents for '{name}' ({len(seen_ids)} unique total)")
        print()

    # Process into clean format
    patents_data = [extract_patent_info(p) for p in all_raw_patents]

    # Sort by grant date descending
    patents_data.sort(key=lambda x: x.get("grant_date", ""), reverse=True)

    # Generate Google Patents URL for cross-reference
    google_url = google_patents_search_url(company, start_date, end_date)

    # Print summary
    print("  " + "=" * 50)
    print(f"  PATENT SCAN COMPLETE")
    print(f"  Patents found: {len(patents_data)}")
    print(f"  Google Patents: {google_url}")
    print("  " + "=" * 50)
    print()

    # Create output directory
    os.makedirs("output", exist_ok=True)

    # Generate filenames
    slug = company.lower().replace(" ", "_").replace(",", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"patents_{slug}_{timestamp}"

    txt_path = os.path.join("output", f"{base_name}.txt")
    json_path = os.path.join("output", f"{base_name}.json")

    # Write text report
    report = generate_text_report(company, start_date, end_date, patents_data, google_url)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Write JSON data
    json_output = {
        "metadata": {
            "company": company,
            "also_searched": also_search,
            "start_date": start_date,
            "end_date": end_date,
            "total_patents": len(patents_data),
            "scan_date": datetime.now().isoformat(),
            "google_patents_url": google_url,
        },
        "patents": patents_data,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {txt_path}")
    print(f"  Saved: {json_path}")
    print()

    # Print quick preview of first 5
    if patents_data:
        print("  PREVIEW (first 5):")
        print("  " + "-" * 50)
        for i, p in enumerate(patents_data[:5], 1):
            print(f"  {i}. {p['title'][:70]}")
            print(f"     Patent #{p['patent_id']} | Granted {p['grant_date']}")
            print()


if __name__ == "__main__":
    main()
