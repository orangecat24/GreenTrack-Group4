variable "name_prefix" {
  description = "Short group/project/environment prefix used on data lake resources."
  type        = string
  validation {
    condition     = can(regex("^g4-[a-z0-9-]{3,34}[a-z0-9]$", var.name_prefix))
    error_message = "Use a lowercase g4- prefix, 7-38 characters, ending in a letter or digit."
  }
}

variable "bronze_job_script_path" {
  description = "Absolute path to data/glue/bronze_job.py; the root passes it in, the module uploads it to S3."
  type        = string
}

variable "tags" {
  description = "Additional data lake tags; the inherited provider also supplies group/project/dev tags."
  type        = map(string)
  default     = {}
}
