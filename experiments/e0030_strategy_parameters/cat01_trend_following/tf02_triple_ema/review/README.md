# Review Workflow

This folder stores the review/correction dialogue between two roles:
- Reviewer model (audits and raises findings)
- Programmer model (implements fixes and responds)

## Naming convention

Files are sequential and zero-padded:
- `r01_REVIEW.md`
- `r02_RESPONSE.md`
- `r03_REVIEW.md`
- `r04_RESPONSE.md`
- ...

Odd numbers are `REVIEW`, even numbers are `RESPONSE`.

## Role responsibilities

### Reviewer (`rNN_REVIEW.md`)
- Analyze conceptual and implementation quality.
- Report findings ordered by severity (`Critical`, `High`, `Medium`, `Low`).
- For each finding include:
  - what is wrong,
  - where it is,
  - why it matters,
  - expected correction criteria.
- Avoid vague recommendations; make them testable.

### Programmer (`rNN_RESPONSE.md`)
- Answer point-by-point to the latest review.
- For each finding, mark status:
  - `Fixed`
  - `Partially fixed`
  - `Not fixed` (with reason)
- Include:
  - files changed,
  - behavioral impact,
  - validation executed (`uv run pytest`, `uv run python main.py`, scripts, etc.),
  - remaining risks/open questions.

## Iteration protocol

1. Reviewer writes next `REVIEW` file.
2. Programmer implements and writes next `RESPONSE` file.
3. Repeat until no blocking findings remain.

Recommended stop condition:
- No `Critical`/`High` findings open.
- Acceptance checks from the latest review are passing.

## Scope and traceability

- Keep each file self-contained and dated.
- Reference concrete paths and symbols using backticks.
- Do not rewrite previous review/response files; append progress with a new numbered file.
- Keep generated artifacts out of git unless explicitly required.
