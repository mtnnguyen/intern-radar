import requests

GREENHOUSE_COMPANIES = {
    "Datadog": "datadog",
}

KEYWORDS = [
    "data engineer"
    "data engineering"
    "data science",
    "data scientist",
    "data analyst",
    "data",
    "analytics",
    "machine learning",
    "gis",
    "geospatial",
    "remote sensing",
]

INTERNSHIP_WORDS = [
    "intern",
    "internship",
    "co-op",
    "coop",
    "student",
]


def get_greenhouse_jobs(company_name, slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    return response.json()["jobs"]


def relevant_job(job):
    title = job["title"].lower()

    internship = any(
        word in title
        for word in INTERNSHIP_WORDS
    )

    career_match = any(
        word in title
        for word in KEYWORDS
    )

    return internship and career_match


def main():
    matches = []

    for company, slug in GREENHOUSE_COMPANIES.items():

        print(f"Checking {company}...")

        try:
            jobs = get_greenhouse_jobs(
                company,
                slug
            )

        except Exception as error:
            print(
                f"Could not check {company}: "
                f"{error}"
            )
            continue

        print(
            f"Found {len(jobs)} total jobs."
        )

        for job in jobs:

            if relevant_job(job):

                matches.append({
                    "company": company,
                    "title": job["title"],
                    "location": job.get(
                        "location",
                        {}
                    ).get("name", ""),
                    "url": job["absolute_url"],
                })

    print()
    print(
        f"Found {len(matches)} "
        f"relevant internships:"
    )

    for job in matches:
        print()
        print(
            f"{job['company']} - "
            f"{job['title']}"
        )
        print(job["location"])
        print(job["url"])


if __name__ == "__main__":
    main()