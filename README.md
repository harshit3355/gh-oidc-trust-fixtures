# gh-oidc-trust-fixtures

Labelled Terraform test cases for **GitHub Actions OIDC trust policies** on AWS and Microsoft Entra ID, a harness that scores IaC scanners against them, and a checkov custom check for Entra **flexible federated identity credentials**.

## Problem

Since 2026-07-15 GitHub issues an **immutable `sub` claim** by default for repositories that are created, renamed or transferred ([changelog](https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens/)):

```
repo:octo-org/octo-repo:ref:refs/heads/main                 # name-based (legacy)
repo:octo-org@123456/octo-repo@456789:ref:refs/heads/main   # immutable
```

Static scanners were written for the old format. With checkov 3.3.21:

- every correctly pinned immutable subject **fails** CKV_AWS_358, CKV_AWS_393 and CKV_AZURE_249 (false positive);
- Entra **flexible** federated identity credentials are not checked at all. Microsoft requires GitHub flexible credentials to match `sub` **and** `repository_id` or `repository_owner_id` ([docs](https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-flexible-federated-identity-credentials)). Entra rejects anything else, so the mistake only appears at `terraform apply`.

KICS v2.2.0 has no GitHub OIDC trust checks.

**Who this is for:** platform teams that keep GitHub → AWS IAM or GitHub → Entra ID trust in Terraform and run checkov or KICS in CI.

## What's here

| Path | What it is |
|---|---|
| `cases.py` | Single source for the 30 cases: Terraform, expected verdict, kind, rationale, source link |
| `fixtures/` | Generated `main.tf` per case + `labels.json` |
| `checks/CKV_GHOIDC_1.py` | checkov custom check for `azuread_application_flexible_federated_identity_credential` |
| `eval/run.py` | Runs each scanner, scores verdicts against the labels, writes `results/` |
| `scripts/setup.sh` | Installs the pinned scanners (checkov 3.3.21, KICS v2.2.0 built from source) |

Case kinds: `guard` (correctly pinned, must pass), `security` (over-broad trust), `apply-failure` (Entra rejects it), `policy` (org-wide or `pull_request` trust; some tools allow it by design), `cross-resource`, `control` (non-GitHub issuer).

## Worked example

```hcl
resource "azuread_application_flexible_federated_identity_credential" "gh" {
  application_id             = "/applications/00000000-0000-0000-0000-000000000000"
  display_name               = "gh-flexible"
  audience                   = "api://AzureADTokenExchange"
  issuer                     = "https://token.actions.githubusercontent.com"
  claims_matching_expression = "claims['sub'] matches 'repo:octo-org/octo-repo:*'"
}
```

checkov 3.3.21 and KICS v2.2.0 say nothing. `CKV_GHOIDC_1` fails it, because no `repository_id`/`repository_owner_id` clause is present. Adding `and claims['repository_id'] eq '456789'` makes it pass.

## Measured results

From [`results/report.md`](results/report.md) (30 cases; per-case table, commands and environment are in that file and in `results/results.json`):

| Tool | TP | FN | FP | TN |
|---|---|---|---|---|
| KICS v2.2.0 | 0 | 15 | 0 | 15 |
| checkov 3.3.21 (built-in) | 8 | 7 | 8 | 7 |
| checkov 3.3.21 + [PR #7610](https://github.com/bridgecrewio/checkov/pull/7610) | 6 | 9 | 0 | 15 |
| checkov 3.3.21 + PR #7610 + `CKV_GHOIDC_1` | 10 | 5 | 0 | 15 |

Notes:
- All 8 built-in checkov false positives are immutable subjects. The PR #7610 regex change removes all of them.
- Two built-in checkov "true positives" (`aws-doc-immutable-org-wildcard`, `az-fic-immutable-pull-request`) only fail because of the same regex bug. With the fix applied, checkov passes them.
- The 5 remaining misses of the proposed setup are 4 `policy` cases (checkov allows org-wide wildcards and `pull_request` subjects) and 1 `cross-resource` case (a leftover name-based credential next to its immutable replacement). No tool tested covers that last one.

## Quick start

Linux or WSL with `python3`, `git` and `go`:

```bash
bash scripts/setup.sh   # pinned tools into ~/.cache/gh-oidc-trust-fixtures (override with TOOLS_DIR)
python3 eval/run.py     # writes results/results.json and results/report.md
```

The first `setup.sh` run takes about 35 minutes, mostly building KICS from source. Later runs reuse the tools, and the evaluation itself takes a few minutes. A fresh clone with an empty `TOOLS_DIR` reproduced the scores above exactly; only run metadata changed.

`eval/run.py` exits non-zero if the proposed configuration produces any false positive, or misses a `security` or `apply-failure` case.

Use the check in your own pipeline:

```bash
checkov -d . --external-checks-dir path/to/gh-oidc-trust-fixtures/checks
```

To add a case, edit `CASES` in `cases.py`, run `python3 cases.py`, then re-run the evaluation.

## Failure and security model

- Everything is static. No tokens are minted and no cloud API is called. Whether AWS or Entra accept a configuration is taken from their official documentation, cited per case in `labels.json`.
- `CKV_GHOIDC_1` returns UNKNOWN (not PASSED) when the issuer or expression contains unresolved Terraform interpolation.
- All identifiers in the fixtures are synthetic (account `111111111111`, owner id `123456`, repo id `456789`).

## Limitations

- The cases are synthetic. This measures detection on known patterns, not how often they occur in real repositories.
- Out of scope: GCP, GitLab, Terraform plan JSON, `azurerm` user-assigned identity credentials, and module-heavy code.
- `policy` labels reflect this corpus's stance; checkov allows those patterns on purpose.
- The PR #7610 configuration is a local one-line patch of checkov 3.3.21 (see `scripts/setup.sh`), not a released version.

## Lineage and maintenance

- GitHub: [immutable subject claims](https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens/).
- Microsoft: [migrating federated credentials](https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-github-immutable-subjects) and [flexible credential rules](https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-flexible-federated-identity-credentials).
- Related reports: checkov [#7610](https://github.com/bridgecrewio/checkov/pull/7610) and [#7627](https://github.com/bridgecrewio/checkov/pull/7627); terraform-provider-azuread [#1901](https://github.com/hashicorp/terraform-provider-azuread/issues/1901).

The goal is to move the flexible-credential check and these cases upstream into checkov: proposed as CKV_AZURE_252 in [bridgecrewio/checkov#7715](https://github.com/bridgecrewio/checkov/pull/7715) (issue [#7714](https://github.com/bridgecrewio/checkov/issues/7714)). Scanner versions are pinned, so results only change when a version is deliberately bumped.

## License

Apache-2.0.
