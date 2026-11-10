# Reuse this root's backend, guarded provider and shared foundation. The child
# module has no backend or GitHub deployment role of its own.
module "challenge1" {
  source          = "../../challenge1"
  name_prefix     = "g4-greentrack-dev"
  lambda_zip_path = abspath("${path.module}/../../../build/greentrack-api.zip")
  data_mode       = var.app_data_mode
}

variable "app_data_mode" {
  description = "Default offline synthetic demo; opt in to DynamoDB through a reviewed Terraform change."
  type        = string
  default     = "mock"
  validation {
    condition     = contains(["mock", "dynamodb"], var.app_data_mode)
    error_message = "app_data_mode must be mock or dynamodb."
  }
}

output "application" {
  description = "Application URLs, destinations and non-secret configuration for later deployment."
  value = {
    api_base_url               = module.challenge1.api_base_url
    website_url                = module.challenge1.website_url
    frontend_bucket_name       = module.challenge1.frontend_bucket_name
    cloudfront_distribution_id = module.challenge1.cloudfront_distribution_id
    table_names                = module.challenge1.table_names
    configuration_parameters   = module.challenge1.configuration_parameters
    api_lambda_name            = module.challenge1.api_lambda_name
  }
}
