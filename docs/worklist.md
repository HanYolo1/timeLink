# Work list

The prioritized list of open work, scored as [docs/workflow.md](workflow.md) describes: **score = severity weight x
reach x confidence** (S0 8, S1 5, S2 3, S3 1; reach 0-1 from `scripts/hardware_report.py` and the Steam survey;
confidence 1.0 reproduced with a log, 0.7 two or more reporters with logs, 0.4 one report or no log). Work from the
top of **Open**. A GitHub issue stays the full record; this list is the order.

How to use it:

- **Pick:** take the highest-scored row with no owner that you can reproduce on your hardware, claim it on its
  GitHub issue, and put your name in *Owner* in the same PR that starts the work (or a one-line PR).
- **Add:** a new report becomes a row in **Open** with its three parts filled in, so the score can be checked. Link the
  GitHub issue. One row per problem: if a row already covers it, add the link to that row and raise its
  confidence instead of adding a second row.
- **Move:** when a PR merges, move the row to **Fixed, waiting for a release** with the PR; when a release ships it,
  delete the row (the release notes are the record). A row nobody can reproduce for two weeks, with logs asked for,
  goes to **Parked**.
- Keep each table sorted by score, highest first. Re-score when new logs or hardware numbers arrive.

Agents may add and re-score rows; a person reviews the change like any other PR. When **Open** is empty, the next work
is triage: score the open [GitHub issues](https://github.com/HanYolo1/timeLink/issues) into it.

Every row is timeLink's own: a GitHub issue or pull request of this repository, linked as `#N`. (The list this fork
started with was the upstream team's backlog, with their versions, their issue numbers and their chat; it was cleared
rather than carried over. Git history has it.)

## Open

| Score | Problem | S | Reach | Conf. | Owner | Links |
|---:|---|---|---:|---:|---|---|

## Fixed, waiting for a release

| Problem | Fixed by | Notes |
|---|---|---|

## Parked

| Problem | Why parked | Links |
|---|---|---|
