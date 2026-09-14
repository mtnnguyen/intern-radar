"""
Intern Radar:
Searches company job boards for internships and co-op positions
related to data science, analytics, GIS, geospatial data,
machine learning, statistics, and related fields.
"""

import json
import requests

# -------------------------------------------------------
# CAREER FIELDS I ARE INTERESTED IN
# -------------------------------------------------------

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
    ],

    "Machine Learning": [
        "machine learning",
        "ml engineer",
        "artificial intelligence",
        "applied scientist",
    ],

    "GIS / Geospatial": [
        "gis",
        "geospatial",
        "geomatics",
        "spatial data",
        "remote sensing",
        "earth observation",
    ],

    "Statistics": [
        "statistics",
        "statistical analyst",
        "statistician",
    ]
}


# Words that indicate the role is intended for students.
INTERNSHIP_WORDS = [
    "intern",
    "internship",
    "co-op",
    "coop",
    "student",
]


# -------------------------------------------------------
# LOAD COMPANY LIST
# -------------------------------------------------------

def load_companies():
    """
    Read all companies from companies.json.
    """

    with open("companies.json", "r", encoding="utf-8") as file:
        return json.load(file)


# -------------------------------------------------------
# GREENHOUSE
# -------------------------------------------------------

def get_greenhouse_jobs(company):
    """
    Retrieve jobs from a Greenhouse job board.
    """
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
            "company": company["name"],
            "title": job.get("title", ""),
            "location": job.get(
                "location", {}
            ).get("name", ""),
            "description": job.get("content", ""),
            "employment_type": "",
            "url": job.get("absolute_url", "")
        })

    return jobs


# -------------------------------------------------------
# ASHBY
# -------------------------------------------------------

def get_ashby_jobs(company):
    """
    Retrieve jobs from an Ashby job board.
    """

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

        jobs.append({
            "company": company["name"],
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "description": job.get(
                "descriptionPlain", ""
            ),
            "employment_type": job.get(
                "employmentType", ""
            ),
            "url": (
                job.get("jobUrl")
                or job.get("applyUrl", "")
            )
        })

    return jobs


# -------------------------------------------------------
# LEVER
# -------------------------------------------------------

def get_lever_jobs(company):
    """
    Retrieve jobs from a Lever job board.
    """

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

        categories = job.get("categories", {})

        jobs.append({
            "company": company["name"],
            "title": job.get("text", ""),
            "location": categories.get(
                "location", ""
            ),
            "description": job.get(
                "descriptionPlain", ""
            ),
            "employment_type": categories.get(
                "commitment", ""
            ),
            "url": (
                job.get("hostedUrl")
                or job.get("applyUrl", "")
            )
        })

    return jobs


# -------------------------------------------------------
# FILTERING
# -------------------------------------------------------

def analyze_job(job):
    """
    Determine whether a job is:
    1. an internship/co-op/student position
    2. related to one of our target career fields
    """

    title = job["title"].lower()
    description = job["description"].lower()
    employment_type = job["employment_type"].lower()

    internship_text = (
        title + " " + employment_type
    )

    # Check whether this is an internship or student role.
    is_internship = any(
        word in internship_text
        for word in INTERNSHIP_WORDS
    )

    if not is_internship:
        return None

    # Search both the title AND the job description.
    career_text = (
        title + " " + description
    )

    categories = []

    for category, keywords in CAREER_KEYWORDS.items():

        if any(
            keyword in career_text
            for keyword in keywords
        ):
            categories.append(category)

    # Reject internship if it has nothing to do
    # with our target career fields.
    if not categories:
        return None

    return categories


# -------------------------------------------------------
# MAIN PROGRAM
# -------------------------------------------------------

def main():

    companies = load_companies()

    matches = []

    for company in companies:

        print(
            f"\nChecking {company['name']} "
            f"({company['ats']})..."
        )

        try:

            if company["ats"] == "greenhouse":
                jobs = get_greenhouse_jobs(company)

            elif company["ats"] == "ashby":
                jobs = get_ashby_jobs(company)

            elif company["ats"] == "lever":
                jobs = get_lever_jobs(company)

            else:
                print(
                    f"Unknown ATS: {company['ats']}"
                )
                continue

        except Exception as error:

            print(
                f"Could not check "
                f"{company['name']}: {error}"
            )

            continue

        print(
            f"Found {len(jobs)} total jobs."
        )

        for job in jobs:

            categories = analyze_job(job)

            if categories:

                job["categories"] = categories

                matches.append(job)


    # ---------------------------------------------------
    # DISPLAY RESULTS
    # ---------------------------------------------------

    print("\n")
    print("=" * 60)
    print(
        f"FOUND {len(matches)} "
        f"RELEVANT INTERNSHIPS"
    )
    print("=" * 60)


    for job in matches:

        print()

        print(
            f"{job['company']} - "
            f"{job['title']}"
        )

        print(
            "Category:",
            ", ".join(job["categories"])
        )

        print(
            "Location:",
            job["location"]
        )

        print(
            "Apply:",
            job["url"]
        )

        print("-" * 60)


if __name__ == "__main__":
    main()