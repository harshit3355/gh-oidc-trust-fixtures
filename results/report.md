# Results

Run 2026-10-03T19:40:51+00:00 · fixtures `30ce2f5` · 30 cases · checkov 3.3.21 · Keeping Infrastructure as Code Secure v2.2.0

## Summary

| Tool | TP | FN | FP | TN |
|---|---|---|---|---|
| kics v2.2.0 | 0 | 15 | 0 | 15 |
| checkov 3.3.21 (built-in) | 8 | 7 | 8 | 7 |
| checkov 3.3.21 + PR #7610 | 6 | 9 | 0 | 15 |
| proposed: checkov 3.3.21 + PR #7610 + CKV_GHOIDC_1 | 10 | 5 | 0 | 15 |

TP/FN count cases labelled FAIL; FP/TN count cases labelled PASS. `NONE` = the tool did not evaluate the resource.

## Per case

| Case | Kind | Expect | kics v2.2.0 | checkov 3.3.21 (built-in) | checkov 3.3.21 + PR #7610 | proposed: checkov 3.3.21 + PR #7610 + CKV_GHOIDC_1 |
|---|---|---|---|---|---|---|
| `aws-doc-legacy-branch` | guard | PASS | NONE ✅ | PASS ✅ | PASS ✅ | PASS ✅ |
| `aws-doc-immutable-branch` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `aws-doc-immutable-environment` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `aws-doc-immutable-any-ref` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `aws-doc-immutable-via-variable` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `aws-doc-legacy-org-wildcard` | policy | FAIL | NONE ❌ FN | PASS ❌ FN | PASS ❌ FN | PASS ❌ FN |
| `aws-doc-immutable-org-wildcard` | policy | FAIL | NONE ❌ FN | FAIL ✅ | PASS ❌ FN | PASS ❌ FN |
| `aws-doc-owner-prefix-wildcard` | security | FAIL | NONE ❌ FN | FAIL ✅ | FAIL ✅ | FAIL ✅ |
| `aws-doc-repo-wildcard` | security | FAIL | NONE ❌ FN | FAIL ✅ | FAIL ✅ | FAIL ✅ |
| `aws-doc-bare-wildcard` | security | FAIL | NONE ❌ FN | FAIL ✅ | FAIL ✅ | FAIL ✅ |
| `aws-doc-no-sub` | security | FAIL | NONE ❌ FN | FAIL ✅ | FAIL ✅ | FAIL ✅ |
| `aws-doc-workflow-first-claim` | security | FAIL | NONE ❌ FN | FAIL ✅ | FAIL ✅ | FAIL ✅ |
| `aws-role-legacy-branch` | guard | PASS | NONE ✅ | PASS ✅ | PASS ✅ | PASS ✅ |
| `aws-role-immutable-branch` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `aws-role-immutable-environment` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `aws-role-legacy-org-wildcard` | policy | FAIL | NONE ❌ FN | PASS ❌ FN | PASS ❌ FN | PASS ❌ FN |
| `aws-role-no-sub` | security | FAIL | NONE ❌ FN | FAIL ✅ | FAIL ✅ | FAIL ✅ |
| `az-fic-legacy-branch` | guard | PASS | NONE ✅ | PASS ✅ | PASS ✅ | PASS ✅ |
| `az-fic-immutable-branch` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `az-fic-immutable-environment` | guard | PASS | NONE ✅ | FAIL ❌ FP | PASS ✅ | PASS ✅ |
| `az-fic-immutable-pull-request` | policy | FAIL | NONE ❌ FN | FAIL ✅ | PASS ❌ FN | PASS ❌ FN |
| `az-fic-dangling-legacy` | cross-resource | FAIL | NONE ❌ FN | PASS ❌ FN | PASS ❌ FN | PASS ❌ FN |
| `az-flex-sub-and-repo-id` | guard | PASS | NONE ✅ | NONE ✅ | NONE ✅ | PASS ✅ |
| `az-flex-immutable-repo-and-owner-id` | guard | PASS | NONE ✅ | NONE ✅ | NONE ✅ | PASS ✅ |
| `az-flex-org-sub-and-owner-id` | guard | PASS | NONE ✅ | NONE ✅ | NONE ✅ | PASS ✅ |
| `az-flex-sub-and-workflow-ref-only` | apply-failure | FAIL | NONE ❌ FN | NONE ❌ FN | NONE ❌ FN | FAIL ✅ |
| `az-flex-sub-only` | apply-failure | FAIL | NONE ❌ FN | NONE ❌ FN | NONE ❌ FN | FAIL ✅ |
| `az-flex-repo-id-only` | apply-failure | FAIL | NONE ❌ FN | NONE ❌ FN | NONE ❌ FN | FAIL ✅ |
| `az-flex-repo-id-matches-operator` | apply-failure | FAIL | NONE ❌ FN | NONE ❌ FN | NONE ❌ FN | FAIL ✅ |
| `az-flex-terraform-cloud-issuer` | control | PASS | NONE ✅ | NONE ✅ | NONE ✅ | PASS ✅ |

## Commands

- **kics v2.2.0**: `scan -p fixtures -q $KICS/assets/queries -o /tmp/tmp2d0grt8_ --report-formats json --output-name kics --type Terraform --disable-secrets --no-progress --silent`
- **checkov 3.3.21 (built-in)**: `-d fixtures --framework terraform -o json --compact --check CKV_AWS_358,CKV_AWS_393,CKV_AZURE_249`
- **checkov 3.3.21 + PR #7610**: `-d fixtures --framework terraform -o json --compact --check CKV_AWS_358,CKV_AWS_393,CKV_AZURE_249`
- **proposed: checkov 3.3.21 + PR #7610 + CKV_GHOIDC_1**: `-d fixtures --framework terraform -o json --compact --check CKV_AWS_358,CKV_AWS_393,CKV_AZURE_249,CKV_GHOIDC_1 --external-checks-dir checks`

## What this result does not establish

- Prevalence: the cases are synthetic; nothing here measures how often these patterns occur in real repositories.
- Runtime behaviour: no tokens were minted and no cloud API was called; Entra/AWS acceptance is taken from official docs.
- Coverage beyond the listed resources: GCP, GitLab, Terraform plan JSON and modules with unresolved variables are not tested.
- `policy` cases (org-wide wildcards) encode this corpus's stance; some tools allow them by design.
