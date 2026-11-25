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

variable "silver_job_script_path" {
  description = "Absolute path to data/glue/silver_job.py; the root passes it in, the module uploads it to S3."
  type        = string
}

variable "gold_job_script_path" {
  description = "Absolute path to data/glue/gold_job.py."
  type        = string
}

variable "quality_job_script_path" {
  description = "Absolute path to data/glue/quality_job.py."
  type        = string
}

variable "quality_ruleset_path" {
  description = "Absolute path to data/quality/silver_readings.dqdl."
  type        = string
}

variable "consumer_role_arns" {
  description = "Role ARNs that may read gold tables through Lake Formation (application, SageMaker, assistant tools)."
  type        = list(string)
  default     = []
  validation {
    condition = alltrue([
      for arn in var.consumer_role_arns :
      can(regex("^arn:aws:iam::886565871385:role/g4-[A-Za-z0-9+=,.@_-]+$", arn))
    ])
    error_message = "Only g4- prefixed roles in this account are accepted as gold consumers."
  }
}

variable "consumer_database_permission_overrides" {
  description = "Explicit per-consumer database grants to preserve existing approved access; unlisted consumers get DESCRIBE only."
  type        = map(list(string))
  default     = {}
  validation {
    condition = alltrue([
      for arn, permissions in var.consumer_database_permission_overrides :
      contains(var.consumer_role_arns, arn) && length(permissions) > 0 && alltrue([
        for permission in permissions : contains(["ALL", "ALTER", "CREATE_TABLE", "DESCRIBE", "DROP"], permission)
      ])
    ])
    error_message = "Database permission overrides must name active consumer roles and contain valid, nonempty database permissions."
  }
}

variable "lake_formation_extra_admins" {
  description = "Additional IAM principal ARNs to grant Lake Formation data lake administrator rights."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional data lake tags; the inherited provider also supplies group/project/dev tags."
  type        = map(string)
  default     = {}
}
