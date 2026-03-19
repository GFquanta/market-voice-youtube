#!/usr/bin/env python3
"""
Job Scanner — Market Voice Module

Pulls recent job postings directly from company career sites.
No LinkedIn or Indeed API needed — uses Workday's undocumented JSON API,
which powers most large enterprise career pages.

Works with any company that uses Workday for hiring, including:
  Fiserv, FIS, Global Payments, PayPal, Block/Square, JPMorgan, etc.

Usage:
  python job_scanner.py

  Or with command-line args:
  python job_scanner.py --config companies.json

How it works:
  Workday career sites expose a hidden JSON API at /wday/cxs/{tenant}/{site}/jobs.
  This script POSTs to that endpoint with optional date filters (posted in last 7 days),
  collects structured job data (title, location, posting date, department), and
  produces a report highlighting hiring patterns and signals.

No API key required. No login required. 100% public data.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# Company registry — Workday career site configs
# ---------------------------------------------------------------------------
# To add a company:
#   1. Go to their careers page
#   2. Open browser DevTools → Network tab
#   3. Look for XHR requests to /wday/cxs/...
#   4. Note the base URL, tenant, and site path
#
# Or just look at the career site URL — it usually follows the pattern:
#   https://{tenant}.{wd_instance}.myworkdayjobs.com/{site}
# The API endpoint is:
#   https://{tenant}.{wd_instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

DEFAULT_COMPANIES = {
    "Fiserv": {
        "base_url": "https://fiserv.wd5.myworkdayjobs.com",
        "tenant": "fiserv",
        "site": "EXT",
    },
    "FIS": {
        "base_url": "https://careers-fisglobal.wd5.myworkdayjobs.com",
        "tenant": "careers-fisglobal",
        "site": "FISExternalCareerSite",
    },
    "Global Payments": {
        "base_url": "https://tsys.wd5.myworkdayjobs.com",
        "tenant": "tsys",
        "site": "GlobalPaymentsCareers",
    },
    "PayPal": {
        "base_url": "https://paypal.wd1.myworkdayjobs.com",
        "tenant": "paypal",
        "site": "jobs",
    },
    "Block (Square)": {
        "base_url": "https://block.wd1.myworkdayjobs.com",
        "tenant": "block",
        "site": "block",
    },
    "Adyen": {
        "base_url": "https://adyen.wd3.myworkdayjobs.com",
        "tenant": "adyen",
        "site": "Careers",
    },
}

# Posting date filter values that Workday accepts in appliedFacets
# (maps to the "Date Posted" facet on career sites)
DATE_FILTERS = {
    "24h": "1",      # Last 24 hours
    "7d": "7",       # Last 7 days
    "30d": "30",     # Last 30 days
    "all": None,     # No filter
}

# Max pages to fetch per company (safety limit)
MAX_PAGES = 10
PAGE_SIZE = 20


# ---------------------------------------------------------------------------
# Workday API
# ---------------------------------------------------------------------------

def build_api_url(company_config):
    """Build the Workday /wday/cxs/.../jobs endpoint URL."""
    base = company_config["base_url"].rstrip("/")
    tenant = company_config["tenant"]
    site = company_config["site"]
    return f"{base}/wday/cxs/{tenant}/{site}/jobs"


def build_job_url(company_config, external_path):
    """Build the full URL for a specific job posting."""
    base = company_config["base_url"].rstrip("/")
    site = company_config["site"]
    # external_path usually looks like /job/Location/Title/JR-12345
    return f"{base}/{site}{external_path}"


def fetch_jobs(company_name, company_config, date_filter="7d", search_text=""):
    """
    Fetch job postings from a company's Workday career site.

    Args:
        company_name: Display name for logging
        company_config: Dict with base_url, tenant, site
        date_filter: One of "24h", "7d", "30d", "all"
        search_text: Optional keyword filter

    Returns:
        List of job posting dicts
    """
    api_url = build_api_url(company_config)

    # Build the request payload
    applied_facets = {}
    filter_val = DATE_FILTERS.get(date_filter)
    if filter_val:
        # Workday uses "timeType" facet for posting date
        applied_facets["timeType"] = [filter_val]

    all_jobs = []
    offset = 0

    print(f"\n  --- {company_name} ---")
    print(f"  API: {api_url}")
    print(f"  Filter: posted in last {date_filter}")

    for page in range(MAX_PAGES):
        payload = {
            "appliedFacets": applied_facets,
            "limit": PAGE_SIZE,
            "offset": offset,
            "searchText": search_text,
        }

        try:
            resp = requests.post(
                api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=20,
            )
        except requests.exceptions.ConnectionError:
            print(f"  ERROR: Could not connect to {company_name}'s career site.")
            print(f"  The Workday URL may have changed. Check: {company_config['base_url']}")
            return all_jobs
        except requests.exceptions.RequestException as e:
            print(f"  ERROR: Request failed: {e}")
            return all_jobs

        if resp.status_code == 404:
            print(f"  ERROR: Endpoint not found (404). The site path may have changed.")
            print(f"  Try visiting {company_config['base_url']} in a browser to find the current path.")
            return all_jobs

        if resp.status_code != 200:
            print(f"  ERROR: Got status {resp.status_code}")
            try:
                print(f"  Body: {resp.text[:300]}")
            except Exception:
                pass
            return all_jobs

        try:
            data = resp.json()
        except json.JSONDecodeError:
            print(f"  ERROR: Response was not JSON. Site may require browser rendering.")
            return all_jobs

        postings = data.get("jobPostings", [])
        total = data.get("total", 0)

        if page == 0:
            print(f"  Total matching jobs: {total}")

        for posting in postings:
            job = {
                "title": posting.get("title", "N/A"),
                "posted_on": posting.get("postedOn", "N/A"),
                "location": posting.get("locationsText", "N/A"),
                "bullet_fields": posting.get("bulletFields", []),
                "external_path": posting.get("externalPath", ""),
            }
            job["url"] = build_job_url(company_config, job["external_path"])
            all_jobs.append(job)

        if len(all_jobs) >= total or len(postings) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.3)  # Be polite

    print(f"  Collected {len(all_jobs)} postings")
    return all_jobs


def fetch_job_detail(company_config, external_path):
    """
    Fetch full details for a single job posting (description, qualifications, etc.).
    Optional — use this for deeper analysis on specific roles.
    """
    base = company_config["base_url"].rstrip("/")
    tenant = company_config["tenant"]
    site = company_config["site"]
    url = f"{base}/wday/cxs/{tenant}/{site}{external_path}"

    try:
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException:
        pass

    return None


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def categorize_jobs(jobs):
    """Group jobs into rough functional categories based on title keywords."""
    categories = {
        "Engineering / Tech": [],
        "AI / Data Science / ML": [],
        "Product": [],
        "Sales / Business Dev": [],
        "Customer Success / Support": [],
        "Marketing": [],
        "Finance / Accounting": [],
        "Legal / Compliance / Risk": [],
        "HR / People": [],
        "Operations": [],
        "Design / UX": [],
        "Other": [],
    }

    keyword_map = {
        "Engineering / Tech": [
            "engineer", "developer", "software", "devops", "cloud", "platform",
            "infrastructure", "architect", "sre", "backend", "frontend", "fullstack",
            "full stack", "qa ", "quality assurance", "test engineer", "technical lead",
        ],
        "AI / Data Science / ML": [
            "ai ", "artificial intelligence", "machine learning", " ml ", "data scien",
            "data engineer", "data analy", "analytics", "nlp", "deep learning",
        ],
        "Product": [
            "product manager", "product owner", "product lead", "product director",
            "scrum", "agile", "program manager",
        ],
        "Sales / Business Dev": [
            "sales", "business develop", "account exec", "account manager",
            "revenue", "commercial", "partnerships",
        ],
        "Customer Success / Support": [
            "customer success", "client success", "support engineer", "support spec",
            "help desk", "client servic", "customer service", "client relation",
        ],
        "Marketing": [
            "marketing", "brand", "content", "communications", "public relation",
            "demand gen", "growth",
        ],
        "Finance / Accounting": [
            "finance", "financial", "accounting", "controller", "treasury", "audit",
            "tax ", "cfo", "fp&a",
        ],
        "Legal / Compliance / Risk": [
            "legal", "compliance", "regulatory", "risk ", "fraud", "aml ",
            "kyc ", "bsa ", "counsel",
        ],
        "HR / People": [
            "human resource", "people", "talent", "recruiting", "recruiter",
            "hris", "compensation", "benefits",
        ],
        "Operations": [
            "operations", "supply chain", "logistics", "procurement",
            "facilities", "warehouse",
        ],
        "Design / UX": [
            "design", "ux ", "ui ", "user experience", "user interface",
            "visual design", "interaction design",
        ],
    }

    for job in jobs:
        title_lower = job["title"].lower()
        categorized = False
        for category, keywords in keyword_map.items():
            if any(kw in title_lower for kw in keywords):
                categories[category].append(job)
                categorized = True
                break
        if not categorized:
            categories["Other"].append(job)

    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def location_summary(jobs):
    """Count jobs by location."""
    locs = {}
    for job in jobs:
        loc = job.get("location", "Unknown")
        locs[loc] = locs.get(loc, 0) + 1
    return dict(sorted(locs.items(), key=lambda x: x[1], reverse=True))


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_text_report(results, date_filter):
    """Generate a human-readable report across all companies."""
    lines = []
    lines.append("=" * 70)
    lines.append("JOB SCANNER — MARKET VOICE")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Report date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Date filter:   Posted in last {date_filter}")
    lines.append(f"  Companies:     {len(results)}")
    lines.append("")

    total_all = sum(len(r["jobs"]) for r in results)
    lines.append(f"  Total postings across all companies: {total_all}")
    lines.append("")
    lines.append("-" * 70)

    for result in results:
        company = result["company"]
        jobs = result["jobs"]
        categories = categorize_jobs(jobs)
        locations = location_summary(jobs)

        lines.append("")
        lines.append(f"  {'='*50}")
        lines.append(f"  {company.upper()}   ({len(jobs)} postings)")
        lines.append(f"  {'='*50}")

        if not jobs:
            lines.append(f"  No postings found (or could not connect).")
            lines.append("")
            continue

        # Category breakdown
        lines.append("")
        lines.append("  HIRING BY FUNCTION:")
        for cat, cat_jobs in sorted(categories.items(), key=lambda x: -len(x[1])):
            bar = "#" * min(len(cat_jobs), 30)
            lines.append(f"    {cat:<35} {len(cat_jobs):>4}  {bar}")

        # Top locations
        lines.append("")
        lines.append("  TOP LOCATIONS:")
        for loc, count in list(locations.items())[:10]:
            lines.append(f"    {loc:<45} {count:>4}")

        # Signal detection
        lines.append("")
        lines.append("  SIGNALS:")
        ai_count = len(categories.get("AI / Data Science / ML", []))
        eng_count = len(categories.get("Engineering / Tech", []))
        sales_count = len(categories.get("Sales / Business Dev", []))
        compliance_count = len(categories.get("Legal / Compliance / Risk", []))

        if ai_count >= 3:
            lines.append(f"    >> AI/ML hiring surge: {ai_count} open roles. Likely building or expanding AI capabilities.")
        if eng_count >= 10:
            lines.append(f"    >> Heavy engineering hiring: {eng_count} roles. Major build/platform investment underway.")
        if sales_count >= 5:
            lines.append(f"    >> Sales push: {sales_count} roles. Expansion or new market push.")
        if compliance_count >= 3:
            lines.append(f"    >> Compliance build-up: {compliance_count} roles. Possible regulatory pressure or new market entry.")
        if len(jobs) < 5:
            lines.append(f"    >> Very few postings ({len(jobs)}). Could signal hiring freeze or cost-cutting mode.")

        # Sample job titles
        lines.append("")
        lines.append("  NOTABLE TITLES (sample):")
        for job in jobs[:15]:
            posted = job.get("posted_on", "")
            lines.append(f"    - {job['title']}")
            if posted:
                lines.append(f"      {posted} | {job.get('location', '')}")

        if len(jobs) > 15:
            lines.append(f"    ... and {len(jobs) - 15} more")

        lines.append("")

    lines.append("-" * 70)

    # Cross-company comparison
    lines.append("")
    lines.append("  CROSS-COMPANY COMPARISON:")
    lines.append(f"  {'Company':<25} {'Total':>6} {'Eng':>6} {'AI/ML':>6} {'Sales':>6} {'Compl':>6}")
    lines.append(f"  {'-'*25} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")

    for result in results:
        cats = categorize_jobs(result["jobs"])
        lines.append(
            f"  {result['company']:<25} "
            f"{len(result['jobs']):>6} "
            f"{len(cats.get('Engineering / Tech', [])):>6} "
            f"{len(cats.get('AI / Data Science / ML', [])):>6} "
            f"{len(cats.get('Sales / Business Dev', [])):>6} "
            f"{len(cats.get('Legal / Compliance / Risk', [])):>6}"
        )

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_company_config(config_path=None):
    """Load company configurations from file or use defaults."""
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_COMPANIES


def get_inputs():
    """Get parameters from user or command-line."""
    parser = argparse.ArgumentParser(description="Job Scanner — Market Voice")
    parser.add_argument("--config", type=str, help="Path to companies config JSON")
    parser.add_argument("--companies", type=str, nargs="*",
                        help="Company names to scan (must be in registry)")
    parser.add_argument("--date-filter", type=str, default="7d",
                        choices=["24h", "7d", "30d", "all"],
                        help="How recent the postings should be (default: 7d)")
    parser.add_argument("--search", type=str, default="",
                        help="Optional keyword to filter job titles")

    args = parser.parse_args()

    companies = load_company_config(args.config)

    # Filter to specific companies if requested
    if args.companies:
        filtered = {}
        for name in args.companies:
            # Case-insensitive match
            for key in companies:
                if key.lower() == name.lower():
                    filtered[key] = companies[key]
                    break
            else:
                print(f"  WARNING: '{name}' not found in company registry. Skipping.")
        companies = filtered

    if not companies:
        print("  ERROR: No companies to scan.")
        print(f"  Available companies: {', '.join(DEFAULT_COMPANIES.keys())}")
        sys.exit(1)

    return companies, args.date_filter, args.search


def main():
    companies, date_filter, search_text = get_inputs()

    print("\n  JOB SCANNER — Market Voice")
    print("  " + "=" * 40)
    print(f"  Scanning {len(companies)} companies...")
    print(f"  Date filter: {date_filter}")
    if search_text:
        print(f"  Keyword filter: {search_text}")
    print()

    results = []

    for company_name, config in companies.items():
        jobs = fetch_jobs(company_name, config, date_filter, search_text)
        results.append({
            "company": company_name,
            "config": config,
            "jobs": jobs,
        })

    # Generate reports
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Text report
    txt_path = os.path.join("output", f"jobs_{timestamp}.txt")
    report = generate_text_report(results, date_filter)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report)

    # JSON data
    json_path = os.path.join("output", f"jobs_{timestamp}.json")
    json_output = {
        "metadata": {
            "scan_date": datetime.now().isoformat(),
            "date_filter": date_filter,
            "search_text": search_text,
            "companies_scanned": list(companies.keys()),
        },
        "results": [
            {
                "company": r["company"],
                "total_postings": len(r["jobs"]),
                "jobs": r["jobs"],
            }
            for r in results
        ],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved: {txt_path}")
    print(f"  Saved: {json_path}")

    # Print the text report to terminal too
    print()
    print(report)


if __name__ == "__main__":
    main()
