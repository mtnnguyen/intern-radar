"""
Intern Radar

Automatically searches company job boards for internships and co-op
positions related to data science, analytics, machine learning,
GIS/geospatial, statistics, and related fields.

Matching jobs are stored in jobs.json and displayed in jobs.md.
"""

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


COMPANIES_FILE = Path("companies.json")
JOBS_FILE = Path("jobs.json")
MARKDOWN_FILE = Path("jobs.md")


# Career fields that we want the tracker to find.
CAREER_KEYWORDS = {
    "Data Science": [
        "data science",
        "data scientist",
    ],

    "Analytics": [
        "data analyst",
        "analytics",
        "business intelligence",
        "business analytics",
        "product analytics",
        "quantitative analyst",
    ],

    "Machine Learning": [
        "machine learning",
        "ml engineer",
        "machine learning engineer",
        "artificial intelligence",
        "applied scientist",
    ],

    "GIS / Geospatial": [
        "gis",
        "geospatial",
        "geomatics",
        "spatial data",
        "spatial analyst",
        "remote sensing",
        "earth observation",
        "geographic information system",
    ],

    "Statistics": [
        "statistics",
        "statistical analyst",
        "statistician",
    ],
}


# Words that suggest a position is meant for students.
INTERNSHIP_WORDS = [
    "intern",
    "internship",
    "co-op",
    "coop",
    "student",
]


def current_time():
    """Return the current UTC time."""

    return datetime.now(timezone.utc).isoformat()


def clean_text(text):
    """Remove simple HTML formatting from job descriptions."""

    if not text:
        return ""

    text = html.unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def create_job_id(source, company, original_id):
    """
    Create a stable ID so the tracker can recognize
    the same job during future runs.
    """

    value = f"{source}:{company}:{original_id}"

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:20]


def load_companies():
    """Load the companies we want to monitor."""

    with open(
        COMPANIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ---------------------------------------------------------
# GREENHOUSE
# ---------------------------------------------------------

def get_greenhouse_jobs(company):
    """Retrieve jobs from a Greenhouse job board."""

    slug = company["slug"]

    url = (
        f"https://boards-api.greenhouse.io/"
        f"v1/boards/{slug}/jobs"
    )

    response = requests.get(
        url,
        params={"content": "true"},
        timeout=30
    )

    response.raise_for_status()

    jobs = []

    for job in response.json().get("jobs", []):

        jobs.append({
            "id": create_job_id(
                "greenhouse",
                company["name"],
                job["id"]
            ),

            "company": company["name"],
            "source": "greenhouse",

            "title": job.get(
                "title",
                ""
            ),

            "location": (
                job.get("location") or {}
            ).get(
                "name",
                ""
            ),

            "description": clean_text(
                job.get(
                    "content",
                    ""
                )
            ),

            "employment_type": "",

            "url": job.get(
                "absolute_url",
                ""
            ),

            "published_at": job.get(
                "updated_at"
            ),
        })

    return jobs


# ---------------------------------------------------------
# ASHBY
# ---------------------------------------------------------

def get_ashby_jobs(company):
    """Retrieve jobs from an Ashby job board."""

    slug = company["slug"]

    url = (
        f"https://api.ashbyhq.com/"
        f"posting-api/job-board/{slug}"
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    jobs = []

    for job in response.json().get("jobs", []):

        original_id = (
            job.get("id")
            or job.get("jobUrl")
            or job.get("applyUrl")
            or job.get("title")
        )

        jobs.append({
            "id": create_job_id(
                "ashby",
                company["name"],
                original_id
            ),

            "company": company["name"],
            "source": "ashby",

            "title": job.get(
                "title",
                ""
            ),

            "location": job.get(
                "location",
                ""
            ) or "",

            "description": clean_text(
                job.get(
                    "descriptionPlain",
                    ""
                )
            ),

            "employment_type": job.get(
                "employmentType",
                ""
            ) or "",

            "url": (
                job.get("jobUrl")
                or job.get("applyUrl")
                or ""
            ),

            "published_at": job.get(
                "publishedAt"
            ),
        })

    return jobs


# ---------------------------------------------------------
# LEVER
# ---------------------------------------------------------

def get_lever_jobs(company):
    """Retrieve jobs from a Lever job board."""

    slug = company["slug"]

    url = (
        f"https://api.lever.co/"
        f"v0/postings/{slug}"
    )

    response = requests.get(
        url,
        params={"mode": "json"},
        timeout=30
    )

    response.raise_for_status()

    jobs = []

    for job in response.json():

        categories = (
            job.get("categories")
            or {}
        )

        jobs.append({
            "id": create_job_id(
                "lever",
                company["name"],
                job["id"]
            ),

            "company": company["name"],
            "source": "lever",

            "title": job.get(
                "text",
                ""
            ),

            "location": categories.get(
                "location",
                ""
            ) or "",

            "description": clean_text(
                job.get(
                    "descriptionPlain",
                    ""
                )
            ),

            "employment_type": categories.get(
                "commitment",
                ""
            ) or "",

            "url": (
                job.get("hostedUrl")
                or job.get("applyUrl")
                or ""
            ),

            "published_at": None,
        })

    return jobs


# ---------------------------------------------------------
# FILTER JOBS
# ---------------------------------------------------------

def analyze_job(job):
    """
    Check whether a job is an internship/co-op
    related to one of our target fields.
    """

    title = job["title"].lower()

    description = job[
        "description"
    ].lower()

    employment_type = job[
        "employment_type"
    ].lower()

    internship_text = (
        title
        + " "
        + employment_type
    )

    # Determine whether this is a student position.
    is_internship = any(
        word in internship_text
        for word in INTERNSHIP_WORDS
    )

    if not is_internship:
        return None
    
    career_text = (
        title
        + " "
        + description
    )

    categories = []

    # Determine which career categories match.
    for category, keywords in CAREER_KEYWORDS.items():

        if any(
            keyword in career_text
            for keyword in keywords
        ):

            categories.append(
                category
            )
            
    if not categories:
        return None

    return categories


# ---------------------------------------------------------
# JOB DATABASE
# ---------------------------------------------------------

def load_jobs():
    """
    Load jobs that the tracker has already seen.
    """

    if not JOBS_FILE.exists():
        return {}

    with open(
        JOBS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        jobs = json.load(file)

    return {
        job["id"]: job
        for job in jobs
    }


def save_jobs(database):
    """Save all known jobs into jobs.json."""

    jobs = list(
        database.values()
    )

    jobs.sort(
        key=lambda job: job.get(
            "first_seen",
            ""
        ),
        reverse=True
    )

    with open(
        JOBS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            jobs,
            file,
            indent=2,
            ensure_ascii=False
        )


# ---------------------------------------------------------
# CREATE jobs.md
# ---------------------------------------------------------

def escape_markdown(text):
    """Prevent table formatting from breaking."""

    return str(text).replace(
        "|",
        "\\|"
    )


def is_new_job(job):
    """
    Mark jobs detected within the last 24 hours as NEW.
    """

    try:

        first_seen = datetime.fromisoformat(
            job["first_seen"]
        )

        difference = (
            datetime.now(timezone.utc)
            - first_seen
        )

        return (
            difference.total_seconds()
            <= 86400
        )

    except Exception:

        return False


def create_markdown(database):
    """
    Generate a readable GitHub page containing
    all currently active matching internships.
    """

    open_jobs = [
        job
        for job in database.values()
        if job.get("status") == "open"
    ]

    open_jobs.sort(
        key=lambda job: job.get(
            "first_seen",
            ""
        ),
        reverse=True
    )

    updated = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    lines = [
        "# 🎯 Intern Radar",
        "",
        (
            "Automatically tracks internships and co-op "
            "positions related to data science, analytics, "
            "machine learning, GIS/geospatial and statistics."
        ),
        "",
        f"**Last updated:** {updated}",
        "",
        f"**Active matching jobs:** {len(open_jobs)}",
        "",
        "| New | Company | Position | Category | Location | First Detected | Apply |",
        "|---|---|---|---|---|---|---|",
    ]

    for job in open_jobs:

        new_marker = (
            "🔥 NEW"
            if is_new_job(job)
            else ""
        )

        categories = ", ".join(
            job.get(
                "categories",
                []
            )
        )

        first_seen = (
            job.get(
                "first_seen",
                ""
            )
            .replace(
                "T",
                " "
            )[:16]
        )

        lines.append(
            "| "
            f"{new_marker} | "
            f"{escape_markdown(job['company'])} | "
            f"{escape_markdown(job['title'])} | "
            f"{escape_markdown(categories)} | "
            f"{escape_markdown(job['location'])} | "
            f"{first_seen} UTC | "
            f"[Apply]({job['url']}) |"
        )

    MARKDOWN_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    companies = load_companies()

    database = load_jobs()

    current_job_ids = set()

    successful_companies = set()

    new_jobs = 0

    matching_jobs = 0

    for company in companies:

        print(
            f"\nChecking "
            f"{company['name']} "
            f"({company['ats']})..."
        )

        try:

            if company["ats"] == "greenhouse":

                jobs = get_greenhouse_jobs(
                    company
                )

            elif company["ats"] == "ashby":

                jobs = get_ashby_jobs(
                    company
                )

            elif company["ats"] == "lever":

                jobs = get_lever_jobs(
                    company
                )

            else:

                print(
                    "Unsupported ATS:",
                    company["ats"]
                )

                continue

            successful_companies.add(
                (
                    company["name"],
                    company["ats"]
                )
            )

        except Exception as error:

            print(
                f"Could not check "
                f"{company['name']}: "
                f"{error}"
            )

            continue

        print(
            f"Found {len(jobs)} "
            f"total jobs."
        )

        for job in jobs:

            categories = analyze_job(
                job
            )

            if not categories:
                continue

            matching_jobs += 1

            job_id = job["id"]

            current_job_ids.add(
                job_id
            )

            # Preserve the original date when we first
            # discovered the job.
            if job_id in database:

                first_seen = database[
                    job_id
                ]["first_seen"]

            else:

                first_seen = current_time()

                new_jobs += 1

                print(
                    "NEW:",
                    job["company"],
                    "-",
                    job["title"]
                )

            job["categories"] = categories

            job["first_seen"] = first_seen

            job["last_seen"] = current_time()

            job["status"] = "open"

            database[job_id] = job


    # If a previously known job disappears from a
    # successfully checked company, mark it closed.
    for job_id, job in database.items():

        company_key = (
            job["company"],
            job["source"]
        )

        if (
            company_key in successful_companies
            and job_id not in current_job_ids
        ):

            job["status"] = "closed"


    save_jobs(
        database
    )

    create_markdown(
        database
    )

    print()
    print("=" * 60)

    print(
        f"Matching open jobs found: "
        f"{matching_jobs}"
    )

    print(
        f"New jobs detected: "
        f"{new_jobs}"
    )

    print(
        "Updated jobs.json and jobs.md"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()