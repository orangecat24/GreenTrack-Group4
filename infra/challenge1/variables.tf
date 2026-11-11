variable "name_prefix" {
  description = "Short group/project/environment prefix used on application resources."
  type        = string
  validation {
    condition     = can(regex("^g4-[a-z0-9-]{3,34}[a-z0-9]$", var.name_prefix))
    error_message = "Use a lowercase g4- prefix, 7-38 characters, ending in a letter or digit."
  }
}

variable "lambda_zip_path" {
  description = "Path to scripts/build_lambda.py output; build it before a plan or apply."
  type        = string
}

variable "data_mode" {
  description = "Mock makes no application AWS calls; dynamodb explicitly enables synthetic table reads."
  type        = string
  default     = "mock"
  validation {
    condition     = contains(["mock", "dynamodb"], var.data_mode)
    error_message = "data_mode must be mock or dynamodb."
  }
}

variable "local_cors_origins" {
  description = "Exact local Vite origins; CloudFront's HTTPS origin is added automatically."
  type        = set(string)
  default     = ["http://localhost:5173", "http://127.0.0.1:5173"]
  validation {
    condition = alltrue([
      for origin in var.local_cors_origins :
      can(regex("^http://(localhost|127\\.0\\.0\\.1):[0-9]{1,5}$", origin))
    ])
    error_message = "Use explicit local HTTP origins with a port and no trailing slash."
  }
}

variable "tags" {
  description = "Additional application tags; the inherited provider also supplies group/project/dev tags."
  type        = map(string)
  default     = {}
}
