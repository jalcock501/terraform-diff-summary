# Terraform Diff Summary

A small GitHub Action that writes a compact Terraform plan summary to the
GitHub Step Summary.

It is useful when release/version tags make Terraform plans noisy. By default,
it filters out resource updates where the only effective change is
`tags.Version` or `tags_all.Version`.

The summary deliberately shows changed field paths rather than before/after
values, so it gives reviewers useful context without dumping potentially
sensitive Terraform values into the Step Summary.

## Usage

```yaml
- name: Terraform Plan
  run: terraform plan -out=tfplan

- name: Terraform Plan JSON
  run: terraform show -json tfplan > tfplan.json

- name: Terraform Diff Summary
  uses: your-org/terraform-diff-summary@v1
  with:
    plan-json-path: tfplan.json
```

## Inputs

| Name | Required | Default | Description |
|---|---:|---|---|
| `plan-json-path` | yes | n/a | JSON from `terraform show -json tfplan`. |
| `version-tag-name` | no | `Version` | Tag key to ignore for tag-only changes. |
| `max-changed-fields` | no | `8` | Field path cap per resource before `...`. |

## Output

The action appends Markdown to `$GITHUB_STEP_SUMMARY`.

Example:

```md
### Terraform plan summary

| Field | Count |
|---|---:|
| Resource changes | 12 |
| Filtered Version tag-only changes | 9 |
| Changes shown below | 3 |

| Address | Action | Type | Changed fields |
|---|---|---|---|
| `aws_ecs_service.api` | `update` | `aws_ecs_service` | `desired_count` |
```

## Local Development

Install dependencies:

```bash
poetry install
```

Run the script directly:

```bash
PLAN_JSON_PATH=tfplan.json \
VERSION_TAG_NAME=Version \
MAX_CHANGED_FIELDS=8 \
GITHUB_STEP_SUMMARY=/tmp/summary.md \
python scripts/terraform_diff_summary.py
```

Run tests:

```bash
poetry run test
```

Run lint checks:

```bash
poetry run ruff check .
```

## Notes

This action does not run `terraform plan` for you. It only summarises an
existing JSON plan generated with:

```bash
terraform show -json tfplan > tfplan.json
```
