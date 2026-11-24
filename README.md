# Intern Radar

A Python tracker that collects internship and co-op listings from configured employer job boards and the Simplify internship feed. It filters for data science, analytics, machine learning, statistics, and geospatial roles, then writes a local JSON database and a Markdown job board.

## Setup

Requires Python 3.9+ (with `zoneinfo`) and internet access when fetching live listings.

```bash
python -m pip install -r requirements.txt
python tracker.py
```

The script reads `companies.json` and updates `jobs.json` and `jobs.md`. Run it from the repository root. Job listings are not applications: verify requirements, location, deadlines, and availability on the employer's own page before applying.

## Test

```bash
python -m unittest discover -s tests -v
```

The new `listing_safety.py` module prevents untrusted job-board fields from breaking Markdown table rows and permits only ordinary HTTP(S) application links without embedded credentials or whitespace. Invalid links display **Unavailable** instead of a clickable application button. The test suite uses synthetic examples and does not call external job boards.

## Known limits

- ATS data can be stale or incomplete, and some listings may require work authorization not captured here.
- Job categories are matched from titles, so relevant positions with unusual titles may be missed.
- The source data can contain duplicate listings or missing locations.
- The tracker does not submit job applications.
- Job links are syntax-validated, **not checked for employer authenticity**. Review destinations before submitting personal information.

## Development notes

See [DESIGN_NOTES.md](DESIGN_NOTES.md) for the latest quality improvement and verification details.
