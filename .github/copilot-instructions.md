# Copilot Instructions

This repository is a composite GitHub Action named `terraform-diff-summary`.

## What Matters Most

- Keep the action dependency-free at runtime.
- Keep core logic in `scripts/terraform_diff_summary.py`.
- Do not inline Python logic in `action.yml`.
- Preserve backward compatibility for existing action inputs where practical.
- Never show Terraform before/after values in summaries; show changed field
  paths only.
- Treat Terraform plan JSON as potentially sensitive.

## Validation

Before proposing or completing code changes, run:

```bash
poetry run test
poetry run ruff check .
```

If either command cannot be run, say so explicitly and explain why.

## Review Focus

For Copilot reviews, pay special attention to:

- Tag-only filtering accidentally hiding material changes.
- Disabled filtering still showing useful changed fields.
- Action inputs in `action.yml` matching environment variables read by the
  script.
- README examples staying aligned with implemented behavior.
- CI smoke tests exercising the real composite action with `uses: ./`.
