# Creates the S3 bucket that stores Terraform state for group 4.
# Run this ONCE from a laptop. Its own small state file stays local in this folder.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"

  # Safety check: Terraform refuses to run in any other AWS account.
  allowed_account_ids = ["886565871385"]

  # These tags are added automatically to every resource in this file.
  default_tags {
    tags = {
      Group     = "g4"
      Project   = "greentrack"
      ManagedBy = "terraform"
    }
  }
}

# The bucket itself. The account ID at the end makes the name unique in all of AWS.
resource "aws_s3_bucket" "terraform_state" {
  bucket = "g4-greentrack-tfstate-886565871385"

  # Stops "terraform destroy" from deleting the bucket by mistake.
  lifecycle {
    prevent_destroy = true
  }
}

# Keep old versions of the state file, so a broken state can be restored.
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypt the state file while it is stored.
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# State files can contain secrets, so block all public access.
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Prints the bucket name after apply.
output "state_bucket_name" {
  value = aws_s3_bucket.terraform_state.bucket
}