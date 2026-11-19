variable "name_prefix" {
  description = "Short group/project/environment prefix used on SageMaker resources."
  type        = string
  validation {
    condition     = can(regex("^g4-[a-z0-9-]{3,34}[a-z0-9]$", var.name_prefix))
    error_message = "Use a lowercase g4- prefix, 7-38 characters, ending in a letter or digit."
  }
}

variable "data_lake_bucket_name" {
  description = "Data lake bucket; SageMaker reads gold under gold/ and writes artifacts under ml/."
  type        = string
}

variable "tags" {
  description = "Additional SageMaker tags; the inherited provider also supplies group/project/dev tags."
  type        = map(string)
  default     = {}
}
