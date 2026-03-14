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
