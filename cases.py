"""Single source of truth for the fixture corpus.

Run `python3 cases.py` to (re)generate fixtures/<case>/main.tf and fixtures/labels.json.
Every value is synthetic: account 111111111111, owner octo-org (id 123456), repo octo-repo (id 456789).
"""
import json
import shutil
from pathlib import Path

SRC = {
    "gh": "https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens/",
    "ms-immutable": "https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-github-immutable-subjects",
    "ms-flexible": "https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-flexible-federated-identity-credentials",
    "aws-operators": "https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition_operators.html",
    "checkov-7627": "https://github.com/bridgecrewio/checkov/pull/7627",
}

LEGACY = "repo:octo-org/octo-repo"
IMMUTABLE = "repo:octo-org@123456/octo-repo@456789"
GH_ISSUER = "https://token.actions.githubusercontent.com"
APP = "/applications/00000000-0000-0000-0000-000000000000"


def aws_doc(sub=None, test="StringEquals", value_expr=None, prelude=""):
    sub_block = ""
    if sub is not None or value_expr is not None:
        values = value_expr or f'["{sub}"]'
        sub_block = f"""
    condition {{
      test     = "{test}"
      variable = "token.actions.githubusercontent.com:sub"
      values   = {values}
    }}"""
    return f"""{prelude}data "aws_iam_policy_document" "trust" {{
  statement {{
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {{
      type        = "Federated"
      identifiers = ["arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com"]
    }}
    condition {{
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }}{sub_block}
  }}
}}
"""


def aws_role(sub=None, test="StringEquals"):
    conds = {"StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"}}
    if sub is not None:
        conds.setdefault(test, {})["token.actions.githubusercontent.com:sub"] = sub
    width = max(map(len, conds))
    cond_hcl = "\n".join(
        f"        {op:<{width}} = {{ "
        + ", ".join(f'"{k}" = "{v}"' for k, v in kv.items())
        + " }"
        for op, kv in conds.items()
    )
    return f"""resource "aws_iam_role" "deploy" {{
  name = "gh-deploy"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = {{ Federated = "arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com" }}
      Condition = {{
{cond_hcl}
      }}
    }}]
  }})
}}
"""


def az_fic(subject, name="gh"):
    return f"""resource "azuread_application_federated_identity_credential" "{name}" {{
  application_id = "{APP}"
  display_name   = "{name}"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "{GH_ISSUER}"
  subject        = "{subject}"
}}
"""


def az_flex(expr, issuer=GH_ISSUER):
    return f"""resource "azuread_application_flexible_federated_identity_credential" "gh" {{
  application_id             = "{APP}"
  display_name               = "gh-flexible"
  audience                   = "api://AzureADTokenExchange"
  issuer                     = "{issuer}"
  claims_matching_expression = "{expr}"
}}
"""


T_DOC = "aws_iam_policy_document.trust"
T_ROLE = "aws_iam_role.deploy"
T_FIC = "azuread_application_federated_identity_credential.gh"
T_FLEX = "azuread_application_flexible_federated_identity_credential.gh"

# kind: guard = correctly pinned, must PASS (catches false positives)
#       security = over-broad trust, must FAIL
#       policy = org-wide trust; FAIL here, but some tools allow it by design
#       apply-failure = Entra rejects this at apply time, must FAIL
#       cross-resource = needs reasoning across resources
#       control = out of scope for GitHub checks, must PASS
CASES = [
    # --- AWS: data "aws_iam_policy_document" (checkov CKV_AWS_358) ---
    ("aws-doc-legacy-branch", "PASS", "guard", T_DOC, ["gh"], "Name-based subject pinned to one branch.",
     aws_doc(f"{LEGACY}:ref:refs/heads/main")),
    ("aws-doc-immutable-branch", "PASS", "guard", T_DOC, ["gh", "ms-immutable"], "Immutable subject pinned to one branch.",
     aws_doc(f"{IMMUTABLE}:ref:refs/heads/main")),
    ("aws-doc-immutable-environment", "PASS", "guard", T_DOC, ["gh"], "Immutable subject pinned to one environment.",
     aws_doc(f"{IMMUTABLE}:environment:production")),
    ("aws-doc-immutable-any-ref", "PASS", "guard", T_DOC, ["gh", "aws-operators"], "Repo-bound by immutable IDs; any ref of that one repo.",
     aws_doc(f"{IMMUTABLE}:*", test="StringLike")),
    ("aws-doc-immutable-via-variable", "PASS", "guard", T_DOC, ["gh"], "Immutable subject supplied through a variable default.",
     aws_doc(value_expr="[var.github_sub]",
             prelude=f'variable "github_sub" {{\n  default = "{IMMUTABLE}:ref:refs/heads/main"\n}}\n\n')),
    ("aws-doc-legacy-org-wildcard", "FAIL", "policy", T_DOC, ["ms-immutable", "aws-operators"], "Trusts every current and future repo under a recyclable owner name.",
     aws_doc("repo:octo-org/*", test="StringLike")),
    ("aws-doc-immutable-org-wildcard", "FAIL", "policy", T_DOC, ["gh", "aws-operators"], "Owner-bound by ID but trusts every repo of the owner.",
     aws_doc("repo:octo-org@123456/*", test="StringLike")),
    ("aws-doc-owner-prefix-wildcard", "FAIL", "security", T_DOC, ["aws-operators"], "repo:octo-org* also matches other owners such as octo-org-evil.",
     aws_doc("repo:octo-org*", test="StringLike")),
    ("aws-doc-repo-wildcard", "FAIL", "security", T_DOC, ["aws-operators"], "repo:* trusts any repository on GitHub.",
     aws_doc("repo:*", test="StringLike")),
    ("aws-doc-bare-wildcard", "FAIL", "security", T_DOC, ["aws-operators"], "sub * trusts any GitHub Actions token.",
     aws_doc("*", test="StringLike")),
    ("aws-doc-no-sub", "FAIL", "security", T_DOC, [], "Only aud is checked; any GitHub Actions token can assume the role.",
     aws_doc()),
    ("aws-doc-workflow-first-claim", "FAIL", "security", T_DOC, [], "Custom subject without a repo claim matches same-named workflows in other repos.",
     aws_doc("workflow:deploy")),
    # --- AWS: resource "aws_iam_role" inline trust (checkov CKV_AWS_393) ---
    ("aws-role-legacy-branch", "PASS", "guard", T_ROLE, ["gh"], "Name-based subject pinned to one branch.",
     aws_role(f"{LEGACY}:ref:refs/heads/main")),
    ("aws-role-immutable-branch", "PASS", "guard", T_ROLE, ["gh", "ms-immutable"], "Immutable subject pinned to one branch.",
     aws_role(f"{IMMUTABLE}:ref:refs/heads/main")),
    ("aws-role-immutable-environment", "PASS", "guard", T_ROLE, ["gh"], "Immutable subject pinned to one environment.",
     aws_role(f"{IMMUTABLE}:environment:production")),
    ("aws-role-legacy-org-wildcard", "FAIL", "policy", T_ROLE, ["ms-immutable", "aws-operators"], "Trusts every current and future repo under a recyclable owner name.",
     aws_role("repo:octo-org/*", test="StringLike")),
    ("aws-role-no-sub", "FAIL", "security", T_ROLE, [], "Only aud is checked; any GitHub Actions token can assume the role.",
     aws_role()),
    # --- Entra: classic federated identity credential (checkov CKV_AZURE_249) ---
    ("az-fic-legacy-branch", "PASS", "guard", T_FIC, ["ms-immutable"], "Name-based subject pinned to one branch.",
     az_fic(f"{LEGACY}:ref:refs/heads/main")),
    ("az-fic-immutable-branch", "PASS", "guard", T_FIC, ["ms-immutable"], "Immutable subject exactly as in the Microsoft migration guide.",
     az_fic(f"{IMMUTABLE}:ref:refs/heads/main")),
    ("az-fic-immutable-environment", "PASS", "guard", T_FIC, ["ms-immutable"], "Immutable subject pinned to one environment.",
     az_fic(f"{IMMUTABLE}:environment:production")),
    ("az-fic-immutable-pull-request", "FAIL", "policy", T_FIC, ["checkov-7627"],
     "Repo-bound, but trusts every pull_request run, i.e. unreviewed code; debated upstream.",
     az_fic(f"{IMMUTABLE}:pull_request")),
    ("az-fic-dangling-legacy", "FAIL", "cross-resource", "azuread_application_federated_identity_credential.legacy", ["ms-immutable"],
     "Old name-based credential left beside its immutable replacement; Microsoft says to remove it.",
     az_fic(f"{LEGACY}:ref:refs/heads/main", name="legacy") + "\n" + az_fic(f"{IMMUTABLE}:ref:refs/heads/main", name="immutable")),
    # --- Entra: flexible federated identity credential (no checkov/KICS check exists) ---
    ("az-flex-sub-and-repo-id", "PASS", "guard", T_FLEX, ["ms-flexible"], "sub plus repository_id, as in the Microsoft example.",
     az_flex(f"claims['sub'] matches '{LEGACY}:ref:refs/heads/*' and claims['repository_id'] eq '456789'")),
    ("az-flex-immutable-repo-and-owner-id", "PASS", "guard", T_FLEX, ["ms-immutable"], "Immutable sub plus both ID claims.",
     az_flex(f"claims['sub'] matches '{IMMUTABLE}:*' and claims['repository_id'] eq '456789' and claims['repository_owner_id'] eq '123456'")),
    ("az-flex-org-sub-and-owner-id", "PASS", "guard", T_FLEX, ["ms-flexible"], "Owner-level trust bound by repository_owner_id; allowed by Microsoft.",
     az_flex("claims['sub'] matches 'repo:octo-org/*' and claims['repository_owner_id'] eq '123456'")),
    ("az-flex-sub-and-workflow-ref-only", "FAIL", "apply-failure", T_FLEX, ["ms-flexible"],
     "No repository_id/repository_owner_id: Entra rejects it (same shape as the azuread provider's docs example).",
     az_flex(f"claims['sub'] matches '{LEGACY}:ref:refs/heads/*' and claims['job_workflow_ref'] matches 'octo-org/octo-repo/.github/workflows/*.yml@refs/heads/main'")),
    ("az-flex-sub-only", "FAIL", "apply-failure", T_FLEX, ["ms-flexible"], "GitHub expressions must also match an immutable claim.",
     az_flex(f"claims['sub'] matches '{LEGACY}:*'")),
    ("az-flex-repo-id-only", "FAIL", "apply-failure", T_FLEX, ["ms-flexible"], "GitHub expressions must match sub.",
     az_flex("claims['repository_id'] eq '456789'")),
    ("az-flex-repo-id-matches-operator", "FAIL", "apply-failure", T_FLEX, ["ms-flexible"], "repository_id supports only eq.",
     az_flex(f"claims['sub'] matches '{LEGACY}:*' and claims['repository_id'] matches '4567*'")),
    ("az-flex-terraform-cloud-issuer", "PASS", "control", T_FLEX, ["ms-flexible"], "Not a GitHub issuer; GitHub rules must not fire.",
     az_flex("claims['sub'] matches 'organization:octo-org:project:*:workspace:*:run_phase:*'", issuer="https://app.terraform.io")),
]


def main():
    root = Path(__file__).parent / "fixtures"
    shutil.rmtree(root, ignore_errors=True)
    labels = {}
    for case_id, expect, kind, target, sources, why, tf in CASES:
        (root / case_id).mkdir(parents=True)
        (root / case_id / "main.tf").write_text(tf, encoding="utf-8", newline="\n")
        labels[case_id] = {"expect": expect, "kind": kind, "target": target, "why": why,
                           "sources": [SRC[s] for s in sources]}
    (root / "labels.json").write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(labels)} cases to {root}")


if __name__ == "__main__":
    main()
