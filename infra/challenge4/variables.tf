variable "name_prefix" {
  description = "Environment naming prefix shared by the GreenTrack dev modules."
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the built Linux x86_64 assistant Lambda ZIP."
  type        = string
}

variable "enable_bedrock_model" {
  description = "Enable Bedrock model calls after review. The default uses the scripted model."
  type        = bool
  default     = false
}

variable "model_id" {
  description = "Approved Claude model or inference profile identifier passed to Converse."
  type        = string
  default     = ""
}

variable "model_resource_arns" {
  description = "Exact authorized model and inference profile ARNs required by the chosen model."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.model_resource_arns :
      can(regex("^arn:[^:]+:bedrock:[^:]+:[^:]*:(foundation-model|inference-profile|application-inference-profile)/[^*?]+$", arn))
    ])
    error_message = "Provide explicit Bedrock model or inference profile ARNs without wildcards."
  }
}
