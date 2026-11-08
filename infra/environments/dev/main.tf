# Main Terraform project for group 4 (the "dev" environment).
# Everything the team builds in AWS is added from here.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Store the state in our group's S3 bucket instead of on this laptop,
  # so the whole team and GitHub Actions share the same state.
  backend "s3" {
    bucket       = "g4-greentrack-tfstate-886565871385"
    key          = "environments/dev/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true # stops two people running "apply" at the same time
  }
}

provider "aws" {
  region = "eu-central-1"

  # Safety check: Terraform refuses to run in any other AWS account.
  allowed_account_ids = ["886565871385"]

  # These tags are added automatically to every resource in this project.
  default_tags {
    tags = {
      Group       = "g4"
      Project     = "greentrack"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

# Use the "shared" module: creates the GitHub deploy role for group 4.
module "shared" {
  source = "../../modules/shared"
}

# Show the role's ARN after apply, so we can give it to Person 2.
output "github_deploy_role_arn" {
  value = module.shared.github_deploy_role_arn
}