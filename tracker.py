"""
Intern Radar

Automatically discovers internships and co-op positions related to:

- Data Science
- Data Engineering
- Analytics
- Machine Learning / AI
- GIS / Geospatial
- Remote Sensing
- Statistics

Jobs come from:
1. Direct company ATS boards (Greenhouse, Ashby, Lever)
2. Broad internship feeds such as Simplify

Matching jobs are stored in jobs.json and displayed in jobs.md.
"""

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import requests


# =========================================================
# FILES
# =========================================================

COMPANIES_FILE = Path("companies.json")
JOBS_FILE = Path("jobs.json")
MARKDOWN_FILE = Path("jobs.md")
TORONTO_TZ = ZoneInfo("America/Toronto")


# =========================================================
# BROAD JOB SOURCES
# =========================================================

SIMPLIFY_LISTINGS_URL = (
    "https://raw.githubusercontent.com/"
    "SimplifyJobs/Summer2027-Internships/"
    "dev/.github/scripts/listings.json"
)


# =========================================================
# CAREER FIELDS
# =========================================================

CAREER_KEYWORDS = {
    "Data Science": [
        "data science",
        "data scientist",
    ],

    "Data Engineering": [
        "data engineer",
        "data engineering",
        "data platform",
        "analytics engineer",
    ],

    "Analytics": [
        "data analyst",
        "analytics",
        "business intelligence",
        "business analytics",
        "product analytics",
        "quantitative analyst",
        "quantitative analytics",
    ],

    "Machine Learning / AI": [
        "machine learning",
        "ml engineer",
        "machine learning engineer",
        "artificial intelligence",
        "ai engineer",
        "ai intern",
        "applied scientist",
        "applied science",
    ],

    "GIS / Geospatial": [
        "gis",
        "geospatial",
        "geomatics",
        "spatial data",
        "spatial analyst",
        "geospatial data",
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


# Actual internship / co-op terms.
#
# Word boundaries prevent "intern" from matching:
# internal
# international
# etc.
EARLY_CAREER_PATTERN = re.compile(
    r"\b("
    r"intern|internship|internships|"
    r"co[- ]?op|"
    r"student|"
    r"summer analyst|"
    r"summer associate|"
    r"apprentice|"
    r"placement"
    r")\b",
    re.IGNORECASE
)

EXCLUDED_TITLE_WORDS = [
    "manager",
    "director",
    "senior manager",
    "staff scientist",
    "principal",
]

PHD_PATTERN = re.compile(
    r"\bph\.?d\.?\b",
    re.IGNORECASE
)


# =========================================================
# GENERAL HELPERS
# =========================================================

def current_time():
    """Return current UTC time."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def clean_text(text):
    """Remove HTML formatting."""

    if not text:
        return ""

    text = html.unescape(
        str(text)
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def create_job_id(
    source,
    company,
    original_id
):
    """
    Create a stable job ID so the same job
    can be recognized on later tracker runs.
    """

    value = (
        f"{source}:"
        f"{company}:"
        f"{original_id}"
    )

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:20]


def load_companies():
    """
    Load priority companies from companies.json.
    """

    if not COMPANIES_FILE.exists():
        return []

    with open(
        COMPANIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# =========================================================
# GREENHOUSE
# =========================================================

def get_greenhouse_jobs(company):
    """
    Retrieve jobs from a company's
    Greenhouse job board.
    """

    slug = company["slug"]

    url = (
        "https://boards-api.greenhouse.io/"
        f"v1/boards/{slug}/jobs"
    )

    response = requests.get(
        url,
        params={
            "content": "true"
        },
        timeout=30
    )

    response.raise_for_status()

    jobs = []

    for job in response.json().get(
        "jobs",
        []
    ):

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
                job.get("location")
                or {}
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


# =========================================================
# ASHBY
# =========================================================

def get_ashby_jobs(company):
    """
    Retrieve jobs from a company's
    Ashby job board.
    """

    slug = company["slug"]

    url = (
        "https://api.ashbyhq.com/"
        f"posting-api/job-board/{slug}"
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    jobs = []

    for job in response.json().get(
        "jobs",
        []
    ):

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

            "location": (
                job.get(
                    "location",
                    ""
                )
                or ""
            ),

            "description": clean_text(
                job.get(
                    "descriptionPlain",
                    ""
                )
            ),

            "employment_type": (
                job.get(
                    "employmentType",
                    ""
                )
                or ""
            ),

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


# =========================================================
# LEVER
# =========================================================

def get_lever_jobs(company):
    """
    Retrieve jobs from a company's
    Lever job board.
    """

    slug = company["slug"]

    url = (
        "https://api.lever.co/"
        f"v0/postings/{slug}"
    )

    response = requests.get(
        url,
        params={
            "mode": "json"
        },
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

            "location": (
                categories.get(
                    "location",
                    ""
                )
                or ""
            ),

            "description": clean_text(
                job.get(
                    "descriptionPlain",
                    ""
                )
            ),

            "employment_type": (
                categories.get(
                    "commitment",
                    ""
                )
                or ""
            ),

            "url": (
                job.get("hostedUrl")
                or job.get("applyUrl")
                or ""
            ),

            "published_at": None,
        })

    return jobs


# =========================================================
# SIMPLIFY BROAD DISCOVERY
# =========================================================

def get_simplify_jobs():
    """
    Retrieve active internships from Simplify's
    Summer 2027 internship repository.

    Unlike companies.json, this discovers jobs
    from companies we did not manually add.
    """

    response = requests.get(
        SIMPLIFY_LISTINGS_URL,
        timeout=60
    )

    response.raise_for_status()

    listings = response.json()

    jobs = []

    for listing in listings:

        # Ignore closed/inactive listings.
        if not listing.get(
            "active",
            False
        ):
            continue

        company = listing.get(
            "company_name",
            ""
        ).strip()

        title = listing.get(
            "title",
            ""
        ).strip()

        locations = listing.get(
            "locations",
            []
        )

        if isinstance(
            locations,
            list
        ):

            location = ", ".join(
                str(item)
                for item in locations
            )

        else:

            location = str(
                locations or ""
            )

        url = listing.get(
            "url",
            ""
        )

        original_id = (
            listing.get("id")
            or url
            or (
                f"{company}:"
                f"{title}:"
                f"{location}"
            )
        )

        jobs.append({
            "id": create_job_id(
                "simplify",
                company,
                original_id
            ),

            "company": company,

            "source": "simplify",

            "title": title,

            "location": location,

            "description": "",

            # Simplify is already an internship feed,
            # so mark the employment type accordingly.
            "employment_type": "internship",

            "url": url,

            "published_at": listing.get(
                "date_posted"
            ),
        })

    return jobs


# =========================================================
# JOB FILTERING
# =========================================================

def analyze_job(job):
    """
    Determine whether a job is:

    1. An internship/co-op/student position
    2. Related to one of our target career fields

    Returns matching categories or None.
    """

    title = (
        job.get(
            "title",
            ""
        )
        .lower()
        .strip()
    )

    # ---------------------------------------------
    # REMOVE OBVIOUSLY IRRELEVANT SENIOR POSITIONS
    # ---------------------------------------------

    if any(
        word in title
        for word in EXCLUDED_TITLE_WORDS
    ):
        return None


    # ---------------------------------------------
    # REMOVE PHD-ONLY INTERNSHIPS
    # ---------------------------------------------

    if PHD_PATTERN.search(title):
        return None


    # ---------------------------------------------
    # REQUIRE AN EARLY-CAREER POSITION
    # ---------------------------------------------

    is_internship = bool(
        EARLY_CAREER_PATTERN.search(
            title
        )
    )

    if not is_internship:
        return None

    categories = []

    # Require career keywords in the TITLE.
    #
    # This keeps irrelevant internships out just
    # because their descriptions mention analytics
    # or machine learning somewhere.
    for (
        category,
        keywords
    ) in CAREER_KEYWORDS.items():

        if any(
            keyword in title
            for keyword in keywords
        ):

            categories.append(
                category
            )

    if not categories:
        return None

    return categories


# =========================================================
# JOB DATABASE
# =========================================================

def load_jobs():
    """
    Load jobs previously discovered.
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
    """
    Save all discovered jobs.
    """

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


# =========================================================
# MARKDOWN HELPERS
# =========================================================

def escape_markdown(text):
    """
    Prevent markdown table formatting
    from breaking.
    """

    return str(
        text
    ).replace(
        "|",
        "\\|"
    )


def is_new_job(job):
    """
    A job is considered NEW for 24 hours
    after Intern Radar first discovers it.
    """

    try:

        first_seen = (
            datetime.fromisoformat(
                job["first_seen"]
            )
        )

        difference = (
            datetime.now(
                timezone.utc
            )
            - first_seen
        )

        return (
            difference.total_seconds()
            <= 86400
        )

    except Exception:

        return False

# =========================================================
# LOCATION PRIORITY
# =========================================================

GTA_LOCATIONS = [
    "toronto",
    "mississauga",
    "brampton",
    "vaughan",
    "markham",
    "richmond hill",
    "scarborough",
    "north york",
    "etobicoke",
    "oakville",
    "pickering",
    "ajax",
    "whitby",
]

ONTARIO_LOCATIONS = [
    "ontario",
    "ottawa",
    "waterloo",
    "kitchener",
    "hamilton",
    "guelph",
    "london, on",
]

CANADA_LOCATIONS = [
    "canada",
    "vancouver",
    "montreal",
    "calgary",
    "edmonton",
    "winnipeg",
    "halifax",
    "victoria",
    "quebec",
    "saskatoon",
    "regina",
]

US_LOCATIONS = [
    "united states",
    "usa",
    "u.s.",
    "new york",
    "san francisco",
    "seattle",
    "boston",
    "chicago",
    "austin",
    "los angeles",
]


def get_location_priority(location):
    """
    Rank locations according to application priority.

    4 = Toronto / GTA
    3 = Ontario
    2 = Canada
    1 = United States
    0 = Other / unknown
    """

    location = str(
        location or ""
    ).lower()

    if any(
        place in location
        for place in GTA_LOCATIONS
    ):
        return 4, "🔥 Toronto / GTA"

    if any(
        place in location
        for place in ONTARIO_LOCATIONS
    ):
        return 3, "🇨🇦 Ontario"

    if any(
        place in location
        for place in CANADA_LOCATIONS
    ):
        return 2, "🇨🇦 Canada"

    if any(
        place in location
        for place in US_LOCATIONS
    ):
        return 1, "🇺🇸 USA"

    return 0, "🌎 Other"


def format_toronto_time(iso_time):
    """
    Convert stored UTC timestamps into Toronto time.
    Automatically switches between EST and EDT.
    """

    try:

        dt = datetime.fromisoformat(
            iso_time
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            TORONTO_TZ
        ).strftime(
            "%Y-%m-%d %I:%M %p %Z"
        )

    except Exception:

        return iso_time


# =========================================================
# DEDUPLICATION
# =========================================================

SOURCE_PRIORITY = {
    # Prefer jobs retrieved directly from the employer.
    "greenhouse": 3,
    "ashby": 3,
    "lever": 3,

    # Use aggregator as a fallback.
    "simplify": 1,
}


def normalize_text(text):
    """
    Normalize text so small punctuation/capitalization
    differences do not create duplicate jobs.
    """

    text = str(text or "").lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return text.strip()


def normalize_url(url):
    """
    Normalize application URLs while removing common
    tracking parameters.

    This helps identify the same application link coming
    from multiple sources.
    """

    if not url:
        return ""

    try:

        parts = urlsplit(
            url.strip()
        )

        query = []

        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True
        ):

            key_lower = key.lower()

            # Remove analytics/tracking parameters,
            # but keep useful identifiers such as gh_jid.
            if key_lower.startswith(
                "utm_"
            ):
                continue

            if key_lower in {
                "source",
                "ref",
                "referrer",
            }:
                continue

            query.append(
                (key, value)
            )

        normalized_query = urlencode(
            sorted(query)
        )

        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                normalized_query,
                ""
            )
        )

    except Exception:

        return url.strip()


def job_fallback_key(job):
    """
    Create a text-based backup key when URLs differ.

    Company + title + location must all match after
    normalization.
    """

    company = normalize_text(
        job.get(
            "company",
            ""
        )
    )

    title = normalize_text(
        job.get(
            "title",
            ""
        )
    )

    location = normalize_text(
        job.get(
            "location",
            ""
        )
    )

    return (
        company,
        title,
        location
    )


def choose_better_job(
    existing,
    candidate
):
    """
    Choose which copy of a duplicate job should appear.

    Direct company ATS sources are preferred over Simplify.
    """

    existing_priority = (
        SOURCE_PRIORITY.get(
            existing.get(
                "source",
                ""
            ),
            0
        )
    )

    candidate_priority = (
        SOURCE_PRIORITY.get(
            candidate.get(
                "source",
                ""
            ),
            0
        )
    )

    if (
        candidate_priority
        > existing_priority
    ):
        better = candidate
        other = existing

    else:
        better = existing
        other = candidate

    # Keep the earliest time we discovered the job.
    existing_first = existing.get(
        "first_seen",
        ""
    )

    candidate_first = candidate.get(
        "first_seen",
        ""
    )

    times = [
        time
        for time in [
            existing_first,
            candidate_first
        ]
        if time
    ]

    if times:
        better["first_seen"] = min(
            times
        )

    # Combine categories discovered by both sources.
    categories = list(
        dict.fromkeys(
            existing.get(
                "categories",
                []
            )
            +
            candidate.get(
                "categories",
                []
            )
        )
    )

    better["categories"] = categories

    return better


def deduplicate_jobs(jobs):
    """
    Remove duplicate listings collected from multiple sources.

    First tries application URL matching.
    Then falls back to matching company + title + location.
    """

    unique_jobs = []

    url_index = {}
    fallback_index = {}

    for job in jobs:

        normalized_job_url = normalize_url(
            job.get(
                "url",
                ""
            )
        )

        fallback_key = job_fallback_key(
            job
        )

        duplicate_index = None

        # Best duplicate signal:
        # the same application URL.
        if (
            normalized_job_url
            and normalized_job_url
            in url_index
        ):

            duplicate_index = (
                url_index[
                    normalized_job_url
                ]
            )

        # Backup signal:
        # same company + title + location.
        elif (
            fallback_key
            in fallback_index
        ):

            duplicate_index = (
                fallback_index[
                    fallback_key
                ]
            )


        if duplicate_index is not None:

            existing = unique_jobs[
                duplicate_index
            ]

            better = choose_better_job(
                existing,
                job
            )

            unique_jobs[
                duplicate_index
            ] = better

            # Make both keys point to the same
            # canonical job.
            better_url = normalize_url(
                better.get(
                    "url",
                    ""
                )
            )

            if better_url:
                url_index[
                    better_url
                ] = duplicate_index

            fallback_index[
                job_fallback_key(
                    better
                )
            ] = duplicate_index

            continue


        # This is a completely new unique job.
        new_index = len(
            unique_jobs
        )

        unique_jobs.append(
            job
        )

        if normalized_job_url:

            url_index[
                normalized_job_url
            ] = new_index

        fallback_index[
            fallback_key
        ] = new_index


    return unique_jobs
    

# =========================================================
# GENERATE jobs.md
# =========================================================

def create_markdown(database):
    """
    Generate the public GitHub job board.
    """

    open_jobs = [
        job
        for job in database.values()
        if job.get(
            "status"
        ) == "open"
    ]
    # Remove duplicate listings that appeared
    # through multiple sources.
    open_jobs = deduplicate_jobs(
        open_jobs
    )

    open_jobs.sort(
    key=lambda job: (
        get_location_priority(
            job.get(
                "location",
                ""
            )
        )[0],

        job.get(
            "first_seen",
            ""
        )
    ),
    reverse=True
    )
    
    new_count = sum(
        1
        for job in open_jobs
        if is_new_job(job)
    )

    lines = [
        "# 🎯 Intern Radar",
        "",
        (
            "Automatically discovers internships and co-op "
            "positions related to data science, data engineering, "
            "analytics, machine learning, AI, GIS/geospatial "
            "and statistics."
        ),
        "",
        "**Scheduled checks:** Every 5 minutes (Toronto time)",
        "",
        f"**Active matching jobs:** {len(open_jobs)}",
        "",
        f"**New in the last 24 hours:** {new_count}",
        "",
        (
            "| Priority | New | Company | Position | Category | "
            "Location | Source | First Detected | Apply |"
        ),
        (
            "|---|---|---|---|---|---|---|---|---|"
        ),
    ]

    for job in open_jobs:

        priority_score, priority_label = (
            get_location_priority(
                job.get(
                    "location",
                    ""
                )
            )
        )

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

        first_seen = format_toronto_time(
            job.get(
                "first_seen",
                ""
            )

        )

        source = job.get(
            "source",
            ""
        )

        lines.append(
            "| "
            f"{priority_label} | "
            f"{new_marker} | "
            f"{escape_markdown(job['company'])} | "
            f"{escape_markdown(job['title'])} | "
            f"{escape_markdown(categories)} | "
            f"{escape_markdown(job['location'])} | "
            f"{escape_markdown(source)} | "
            f"{first_seen} | "
            f"[Apply]({job['url']}) |"
        )

    MARKDOWN_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


# =========================================================
# PROCESS JOB
# =========================================================

def process_job(
    job,
    database,
    current_job_ids
):
    """
    Filter a job and store it if relevant.

    Returns:
    (matched, new)
    """

    categories = analyze_job(
        job
    )

    if not categories:
        return False, False

    job_id = job["id"]

    current_job_ids.add(
        job_id
    )

    is_new = (
        job_id not in database
    )

    if is_new:

        first_seen = current_time()

        print(
            "NEW:",
            job["company"],
            "-",
            job["title"]
        )

    else:

        first_seen = database[
            job_id
        ]["first_seen"]

    job["categories"] = categories

    job["first_seen"] = first_seen

    job["status"] = "open"

    database[job_id] = job

    return True, is_new


# =========================================================
# MAIN
# =========================================================

def main():

    companies = load_companies()

    database = load_jobs()

    current_job_ids = set()

    successful_companies = set()

    simplify_success = False

    new_jobs = 0

    matching_jobs = 0


    # =====================================================
    # DIRECT PRIORITY COMPANY CHECKS
    # =====================================================

    for company in companies:

        print(
            f"\nChecking "
            f"{company['name']} "
            f"({company['ats']})..."
        )

        try:

            if (
                company["ats"]
                == "greenhouse"
            ):

                jobs = (
                    get_greenhouse_jobs(
                        company
                    )
                )

            elif (
                company["ats"]
                == "ashby"
            ):

                jobs = (
                    get_ashby_jobs(
                        company
                    )
                )

            elif (
                company["ats"]
                == "lever"
            ):

                jobs = (
                    get_lever_jobs(
                        company
                    )
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
            f"Found "
            f"{len(jobs)} "
            f"total jobs."
        )

        for job in jobs:

            (
                matched,
                is_new
            ) = process_job(
                job,
                database,
                current_job_ids
            )

            if matched:
                matching_jobs += 1

            if is_new:
                new_jobs += 1


    # =====================================================
    # BROAD DISCOVERY
    # =====================================================

    print()
    print(
        "Checking Simplify broad "
        "internship feed..."
    )

    try:

        simplify_jobs = (
            get_simplify_jobs()
        )

        simplify_success = True

        print(
            f"Found "
            f"{len(simplify_jobs)} "
            f"active internships "
            f"in broad feed."
        )

        for job in simplify_jobs:

            (
                matched,
                is_new
            ) = process_job(
                job,
                database,
                current_job_ids
            )

            if matched:
                matching_jobs += 1

            if is_new:
                new_jobs += 1

    except Exception as error:

        print(
            "Could not check "
            "Simplify feed:",
            error
        )


    # =====================================================
    # MARK CLOSED JOBS
    # =====================================================

    for (
        job_id,
        job
    ) in database.items():

        source = job.get(
            "source",
            ""
        )

        # Broad Simplify jobs
        if source == "simplify":

            if (
                simplify_success
                and job_id
                not in current_job_ids
            ):

                job["status"] = (
                    "closed"
                )

            continue


        # Direct company jobs
        company_key = (
            job.get(
                "company",
                ""
            ),
            source
        )

        if (
            company_key
            in successful_companies
            and job_id
            not in current_job_ids
        ):

            job["status"] = "closed"


    # =====================================================
    # SAVE EVERYTHING
    # =====================================================

    save_jobs(
        database
    )

    create_markdown(
        database
    )


    # =====================================================
    # TERMINAL SUMMARY
    # =====================================================

    print()
    print(
        "=" * 60
    )

    print(
        f"Matching jobs found: "
        f"{matching_jobs}"
    )

    print(
        f"New jobs detected: "
        f"{new_jobs}"
    )

    print(
        "Updated jobs.json "
        "and jobs.md"
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()