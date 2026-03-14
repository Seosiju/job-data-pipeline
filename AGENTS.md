# Repository Agents

This repository contains local agent briefs under `.claude/agents/`.
When a user names one of these agents, references one of these files, or asks for work that clearly matches an agent's scope, read the relevant file first and follow its guidance for that turn.

## Available local agents

- `repo-strategist` (`.claude/agents/repo-strategist.md`)
  - Use for repository-wide status reviews, implementation progress checks, architectural direction, milestone retrospectives, and prioritized next-step recommendations.

- `jobkorea-scraper-engineer` (`.claude/agents/jobkorea-scraper-engineer.md`)
  - Use for crawler implementation, selector fixes, pagination handling, anti-bot issues, HTML parsing, and JobKorea scraping/debugging work.

- `data-pipeline-architect` (`.claude/agents/data-pipeline-architect.md`)
  - Use for schema design, ETL pipelines, normalization, deduplication, SQL performance, and data quality work.

- `job-market-analyst` (`.claude/agents/job-market-analyst.md`)
  - Use for analytical SQL, job-market reporting, trend analysis, charts, and skill-gap analysis based on stored job data.

## Usage rules

- Read only the relevant agent file(s); do not bulk-load all files unless the user explicitly asks for a cross-agent synthesis.
- If multiple agents apply, use the minimal set and state the order briefly.
- If the request only partially matches an agent, use the agent's domain guidance but keep the repository's existing code and conventions authoritative.
- If an agent file is missing or outdated, continue with normal repository analysis and note the gap briefly.

## Working Agreement

When executing implementation work in this repository, prefer the following default flow unless the user explicitly asks for something narrower:

1. Clarify the target change and write or refine the plan first.
2. Critically review the plan before implementation.
3. Check whether the plan is over-engineered for the current stage.
4. Implement the change.
5. Review whether the implementation actually matches the goal.
6. Review for bugs, regressions, security issues, side effects, and user-flow problems.
7. Reuse or integrate existing code where possible instead of duplicating logic.
8. Split very large files or functions when the change would otherwise make them harder to maintain.
9. Remove dead code or outdated paths created by the change.
10. Re-review the full diff before considering the work complete.

## Review Standard

By default, review comments should prioritize:

1. correctness
2. behavioural regression risk
3. data quality risk
4. security and operational risk
5. maintainability

A change is not considered complete just because tests pass. The implementation should also be coherent with the user-facing goal and the repository's current architecture.
