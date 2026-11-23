# Design notes — 2026-11-23

## Why improve this project

Intern Radar publishes third-party listing titles, locations, and application links into a Markdown table. The original renderer escaped only pipe characters and inserted URLs directly into `[Apply](...)`. Newlines, HTML, and crafted URLs could disrupt the board or create misleading clickable links. Because this board is public, trustworthy rendering matters more than adding another source.

## Scope

- Centralize plain-text table-cell escaping in `listing_safety.py`.
- Reject non-HTTP(S), malformed, credential-bearing, whitespace-containing, and oversized URLs.
- Percent-encode Markdown-sensitive URL parentheses; show `Unavailable` when a link is rejected.
- Add synthetic regression tests for both valid and adversarial input.
- Document the boundaries: syntactic safety is not employer authenticity verification.

## Alternatives considered

- A full HTML templating engine: unnecessary dependency for a Markdown-only output.
- Drop every record without a safe URL: loses useful job-discovery information; keeping the listing with `Unavailable` is more transparent.
- Resolve every URL over the network: too slow, prone to rate limits, and still cannot prove a job is legitimate.

## Verification

Local isolated module tests: `python -m unittest discover -s tests -v` — **13 passed** after correcting one initially failing test for URLs containing spaces. `python -m compileall -q listing_safety.py tests` — passed. The module and tests were authored and tested locally before being committed. The full tracker against live ATS APIs was not executed in this run; no real listings were modified.

## Follow-up

Add fixture-driven integration tests for `create_markdown` to verify the full generated table, then address incomplete or stale job listings and employer-domain verification.

## Lessons

Treat external listing text as untrusted, even in static Markdown. Prefer an explicit non-clickable state over a potentially unsafe link.
