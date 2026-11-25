# Optional wiring for Person 1's review. Keep the same provider and backend
# and leave the existing application route with Person 2.
module "challenge4" {
  count  = var.enable_assistant ? 1 : 0
  source = "../../challenge4"

  name_prefix          = "g4-greentrack-dev"
  lambda_zip_path      = abspath("${path.module}/../../../build/greentrack-assistant.zip")
  enable_bedrock_model = var.enable_assistant_bedrock_model
  model_id             = var.assistant_model_id
  model_resource_arns  = var.assistant_model_resource_arns
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
