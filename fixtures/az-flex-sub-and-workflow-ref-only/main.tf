resource "azuread_application_flexible_federated_identity_credential" "gh" {
  application_id             = "/applications/00000000-0000-0000-0000-000000000000"
  display_name               = "gh-flexible"
  audience                   = "api://AzureADTokenExchange"
  issuer                     = "https://token.actions.githubusercontent.com"
  claims_matching_expression = "claims['sub'] matches 'repo:octo-org/octo-repo:ref:refs/heads/*' and claims['job_workflow_ref'] matches 'octo-org/octo-repo/.github/workflows/*.yml@refs/heads/main'"
}
