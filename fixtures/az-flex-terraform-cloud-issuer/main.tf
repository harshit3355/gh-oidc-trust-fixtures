resource "azuread_application_flexible_federated_identity_credential" "gh" {
  application_id             = "/applications/00000000-0000-0000-0000-000000000000"
  display_name               = "gh-flexible"
  audience                   = "api://AzureADTokenExchange"
  issuer                     = "https://app.terraform.io"
  claims_matching_expression = "claims['sub'] matches 'organization:octo-org:project:*:workspace:*:run_phase:*'"
}
