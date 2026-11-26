variable "name_prefix" {
  description = "Environment naming prefix shared by the GreenTrack dev modules."
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the built Linux x86_64 assistant Lambda ZIP."
  type        = string
}

variable "data_lake_bucket_name" {
  description = "Existing dev data lake bucket containing gold objects and Athena results."
  type        = string
}

variable "gold_database_name" {
  description = "Gold Glue database containing the assistant's hourly table."
  type        = string
}

variable "enable_athena" {
  description = "Read hourly gold through Athena. Fixture mode is the default."
  type        = bool
  default     = false
}

variable "hourly_gold_prefix" {
  description = "Confirmed hourly_consumption Iceberg table root in the lake bucket, including a trailing slash."
  type        = string
  default     = ""

  validation {
    condition = var.hourly_gold_prefix == "" || can(regex(
      "^gold/([A-Za-z0-9_][A-Za-z0-9_.-]*/)*hourly_consumption/$", var.hourly_gold_prefix
    ))
    error_message = "Use the approved hourly_consumption table prefix under gold/ with a trailing slash."
  }
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
