resource "azuread_application_federated_identity_credential" "gh" {
  application_id = "/applications/00000000-0000-0000-0000-000000000000"
  display_name   = "gh"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:octo-org@123456/octo-repo@456789:pull_request"
}
