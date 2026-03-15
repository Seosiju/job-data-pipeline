# Repository Guidelines

This repository includes task-specific local briefs under `.claude/agents/`.

These files are repository-local guidance documents. They are not native Codex agents, native roles, or Codex skills. Read them only when the current task directly matches their scope.

## Available Briefs

- `repo-strategist` at `.claude/agents/repo-strategist.md`
  - Use for repository-wide status reviews, implementation progress checks, architectural direction, milestone retrospectives, and prioritized next-step recommendations.
  - Do not use for file-level implementation, parser fixes, or crawler debugging unless the user is explicitly asking for repository-wide coordination or prioritization.

- `jobkorea-scraper-engineer` at `.claude/agents/jobkorea-scraper-engineer.md`
  - Use for crawler implementation, selector fixes, pagination handling, anti-bot issues, HTML parsing, and JobKorea scraping/debugging work.
  - Prefer this brief for source acquisition and extraction issues rather than downstream analytics or reporting.

- `data-pipeline-architect` at `.claude/agents/data-pipeline-architect.md`
  - Use for schema design, ETL pipelines, normalization, deduplication, SQL performance, persistence design, and data-quality work.
  - Prefer this brief for storage and transformation concerns after data has been collected.

- `job-market-analyst` at `.claude/agents/job-market-analyst.md`
  - Use for analytical SQL, job-market reporting, trend analysis, charts, and skill-gap analysis based on stored job data.
  - Do not use this brief for crawler, parser, ingestion, or persistence implementation work.

## Brief Routing Rules

- Read a brief only when the user explicitly names it, references its file, or asks for work that directly falls within its stated scope.
- Read only the minimum relevant brief set. Do not bulk-load all briefs unless the user explicitly asks for cross-cutting synthesis.
- If multiple briefs apply, use the minimum set necessary and state the order briefly.
- If a request only partially matches a brief, use the brief for domain context but keep the live codebase, tests, and current repository architecture authoritative.
- If a brief is missing, stale, or contradicted by the codebase, note the gap briefly and continue with normal repository analysis.

## Repository Hard Rules

- Prefer `pytest tests/ -q` for default verification. Use targeted tests for scoped changes, and use broader verification before finishing risky or cross-cutting work.
- Treat `python main.py`, `python scripts/phase2_smoke_test.py`, `python scripts/manual_test_crawler.py`, and `./scripts/run_crawler.sh` as live or integration actions. Do not run them unless the task explicitly requires live crawling or real database interaction.
- Never put secrets into tracked files. Keep real credentials in `.env`, update `.env.example` only when changing the template, and do not commit `.env`, `log/`, or `output/` artifacts.
- Treat `tests/fixtures/` as regression assets. Change fixtures only when parser or crawler behavior intentionally changes, and keep tests aligned with that change.
- Preserve data-quality semantics when editing persistence code. Do not change dedup keys, lifecycle tracking, or `company_page_url` reuse without explicit intent and verification.
- When adding or moving documentation, follow `docs/README.md` classification so plans, architecture docs, guides, reports, and archived records stay separated.
- If a substantial change would make `main.py`, `parser.py`, or `database.py` materially harder to maintain, extract logic instead of continuing to grow the file.

## Default Working Flow

Use this flow for medium or large changes, cross-cutting work, ambiguous tasks, or risky edits. Do not force it for trivial fixes.

1. Confirm the user goal and success criteria.
2. Inspect the existing implementation and relevant tests before asking follow-up questions when the missing context can be discovered locally.
3. Make a plan when the change is non-trivial, cross-cutting, or risky.
4. Check whether the planned approach is too large for the current goal.
5. Reuse existing code and patterns before introducing new abstractions.
6. Implement the smallest change that fully solves the problem.
7. Review the result against the user goal, architecture, and likely edge cases.
8. Check for regressions, security issues, operational risk, and data-quality issues.
9. Remove dead code or obsolete paths created by the change.
10. Re-review the final diff before considering the work complete.

## Review Priorities

When reviewing changes, prioritize:

1. correctness
2. behavioural regression risk
3. data quality risk
4. security and operational risk
5. maintainability

Passing tests alone is not sufficient. A change is only complete when it is technically correct, aligned with the user-facing goal, and coherent with the repository's current architecture.

## Repository Authority

The current user request takes priority for the task at hand.

When code, tests, docs, and briefs disagree, do not silently follow a fixed source. Note the conflict briefly and resolve it using the current task intent, surrounding code, tests, and repository documentation.

As a default guide, weigh sources in this order:

1. current user request
2. live code and surrounding implementation
3. tests and fixtures
4. current repository documentation
5. `.claude/agents/*.md` briefs

## Reuse Guidance

If a workflow becomes repetitive and stable across turns, prefer turning it into a real Codex skill or another structured repository mechanism instead of expanding this file with more prose.
