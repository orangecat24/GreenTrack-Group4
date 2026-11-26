# Optional wiring for Person 1's review. Keep the same provider and backend
# and leave the existing application route with Person 2.
module "challenge4" {
  count  = var.enable_assistant ? 1 : 0
  source = "../../challenge4"

  name_prefix           = "g4-greentrack-dev"
  lambda_zip_path       = abspath("${path.module}/../../../build/greentrack-assistant.zip")
  data_lake_bucket_name = module.challenge2.data_lake_bucket_name
  gold_database_name    = module.challenge2.gold_database_name
  enable_athena         = var.enable_assistant_athena
  hourly_gold_prefix    = var.assistant_hourly_gold_prefix
  enable_bedrock_model  = var.enable_assistant_bedrock_model
  model_id              = var.assistant_model_id
  model_resource_arns   = var.assistant_model_resource_arns
}

variable "enable_assistant_athena" {
  description = "Opt the standalone assistant into live Athena data while keeping model mode independent."
  type        = bool
  default     = false
}

variable "assistant_hourly_gold_prefix" {
  description = "Approved hourly Iceberg table root under gold/ for Athena source reads."
  type        = string
  default     = ""
}

variable "enable_assistant" {
  description = "Create standalone Challenge 4 resources after teammate review."
  type        = bool
  default     = false
}

variable "enable_assistant_bedrock_model" {
  description = "Switch the standalone assistant from the scripted model to approved Bedrock inference."
  type        = bool
  default     = false
}

variable "assistant_model_id" {
  description = "Approved Claude model or inference profile identifier for future inference."
  type        = string
  default     = ""
}

variable "assistant_model_resource_arns" {
  description = "Approved model and inference profile resources for future inference permissions."
  type        = set(string)
  default     = []
}

output "assistant" {
  description = "Challenge 4 resource references when the standalone assistant is enabled."
  value       = one(module.challenge4[*].handoff)
}
