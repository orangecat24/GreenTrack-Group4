# This is a child module, not a separately initialized deployment/state root.
# It is called from infra/environments/dev, which supplies the guarded provider.
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
