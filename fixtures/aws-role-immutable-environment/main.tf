resource "aws_iam_role" "deploy" {
  name = "gh-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = "arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com" }
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com", "token.actions.githubusercontent.com:sub" = "repo:octo-org@123456/octo-repo@456789:environment:production" }
      }
    }]
  })
}
