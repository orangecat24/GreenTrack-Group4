# Shared resources for group 4: the role that GitHub Actions uses to deploy.

# 1) READ the GitHub login provider that already exists in this AWS account.
#    It is shared by all groups, so we never create, change or delete it.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# 2) WHO may use the role: only GitHub Actions running in OUR repository,
#    either on the main branch or in a pull request.
data "aws_iam_policy_document" "github_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    # The login token must be meant for AWS.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # The login token must come from our repository (main branch or a pull request).
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:orangecat24/GreenTrack-Group4:ref:refs/heads/main",
        "repo:orangecat24/GreenTrack-Group4:pull_request",
      ]
    }
  }
}

# 3) The role itself.
resource "aws_iam_role" "github_deploy" {
  name               = "g4-greentrack-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_trust.json
}

# 4) WHAT the role may do, part A: work with most AWS services
#    (S3, Glue, Lambda, DynamoDB, SageMaker, ...). This AWS policy excludes IAM.
resource "aws_iam_role_policy_attachment" "power_user" {
  role       = aws_iam_role.github_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

# 5) WHAT the role may do, part B: manage IAM roles and policies,
#    but ONLY ones whose names start with "g4-". Other groups' roles are off limits.
data "aws_iam_policy_document" "g4_iam_only" {
  statement {
    actions = ["iam:*"]
    resources = [
      "arn:aws:iam::886565871385:role/g4-*",
      "arn:aws:iam::886565871385:policy/g4-*",
    ]
  }

  # Needed to read the shared GitHub provider (read only).
  statement {
    actions = [
      "iam:GetOpenIDConnectProvider",
      "iam:ListOpenIDConnectProviders",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "g4_iam_only" {
  name   = "g4-greentrack-github-deploy-iam"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.g4_iam_only.json
}

# The role's address (ARN). Person 2 needs this for GitHub Actions.
output "github_deploy_role_arn" {
  value = aws_iam_role.github_deploy.arn
}