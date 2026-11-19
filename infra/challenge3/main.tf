data "aws_caller_identity" "current" {}

locals {
  tags          = merge(var.tags, { Challenge = "3" })
  artifacts_key = "ml/"
  scripts_key   = "ml/scripts/"
}
