---
name: Parser failure
about: Report Terraform plan JSON that the action cannot parse or summarize correctly
title: "Parser failure: "
labels: parser, bug
assignees: ""
---

## Summary

<!-- What happened? What did you expect the summary to show? -->

## Terraform Details

- Terraform version:
- Provider(s) involved:
- Command used to generate JSON:

```bash
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
```

## Action Configuration

```yaml
- uses: jalcock501/terraform-diff-summary@v1
  with:
    plan-json-path: tfplan.json
```

## Sanitized JSON Shape

<!--
Paste the smallest sanitized Terraform plan JSON shape that reproduces the issue.
Do not paste secrets, tokens, account IDs, production ARNs, customer names, or
real infrastructure values.
-->

```json
{
  "resource_changes": []
}
```

## Expected Behavior

<!-- What should the action have rendered or filtered? -->

## Actual Behavior

<!-- Include error messages or relevant summary output if safe. -->

## Safety Checklist

- [ ] I removed secrets, tokens, credentials, and certificates.
- [ ] I removed or anonymized account IDs and production ARNs.
- [ ] I removed customer names, hostnames, and real infrastructure values.
- [ ] The JSON example is the smallest shape that reproduces the issue.
