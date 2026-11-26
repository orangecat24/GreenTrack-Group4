# Preview adoption of the manually created workgroup in the shared dev plan.
import {
  for_each = var.enable_assistant ? toset(["g4-greentrack-dev-assistant"]) : toset([])
  to       = module.challenge4[0].aws_athena_workgroup.assistant
  id       = each.value
}
