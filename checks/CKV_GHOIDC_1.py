"""Checkov custom check: GitHub flexible federated identity credentials must match `sub`
and at least one immutable ID claim (`repository_id` / `repository_owner_id`) using `eq`.

Microsoft Entra enforces this at creation time, so a failing resource also fails `terraform apply`:
https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-flexible-federated-identity-credentials
"""
import re

from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck

GITHUB_ISSUER = "https://token.actions.githubusercontent.com"
# One clause of the expression language: claims['<name>'] <operator> '<comparand>'
CLAUSE = re.compile(r"claims\['([^']+)'\]\s+(eq|matches)\s+'[^']*'")
ID_CLAIMS = ("repository_id", "repository_owner_id")


class GithubFlexibleFICClaims(BaseResourceCheck):
    def __init__(self) -> None:
        super().__init__(
            name="Ensure GitHub flexible federated identity credentials match sub and an immutable ID claim",
            id="CKV_GHOIDC_1",
            categories=(CheckCategories.IAM,),
            supported_resources=("azuread_application_flexible_federated_identity_credential",),
        )

    def scan_resource_conf(self, conf):
        issuer = conf.get("issuer", [""])[0]
        expression = conf.get("claims_matching_expression", [""])[0]
        if not isinstance(issuer, str) or not isinstance(expression, str) or "${" in issuer + expression:
            return CheckResult.UNKNOWN  # unresolved variables: don't guess
        if issuer.rstrip("/") != GITHUB_ISSUER:
            return CheckResult.PASSED

        ops = {}
        for claim, op in CLAUSE.findall(expression):
            ops.setdefault(claim, set()).add(op)
        has_sub = "sub" in ops
        has_id = any("eq" in ops.get(claim, ()) for claim in ID_CLAIMS)
        id_non_eq = any(ops.get(claim, set()) - {"eq"} for claim in ID_CLAIMS)  # only `eq` is supported
        return CheckResult.PASSED if has_sub and has_id and not id_non_eq else CheckResult.FAILED

    def get_evaluated_keys(self):
        return ["issuer", "claims_matching_expression"]


check = GithubFlexibleFICClaims()
