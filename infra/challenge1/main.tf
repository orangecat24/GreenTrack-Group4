# The parent supplies the already-guarded AWS provider and eu-central-1 Region.
# These identity values are resolved by a FUTURE authorized AWS plan, not validate.
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  tags = merge(var.tags, { Challenge = "1" })
  # One source of truth feeds SSM and Lambda environment variables. Publishing
  # config to SSM does NOT require fetching it with boto3 during mock startup.
  api_configuration = {
    APP_DATA_MODE              = var.data_mode
    DYNAMODB_REGION            = data.aws_region.current.region
    DYNAMODB_CONSUMPTION_TABLE = aws_dynamodb_table.demo["consumption"].name
    DYNAMODB_ANOMALIES_TABLE   = aws_dynamodb_table.demo["anomalies"].name
    DYNAMODB_FORECASTS_TABLE   = aws_dynamodb_table.demo["forecasts"].name
    DYNAMODB_FORECAST_ORIGIN   = "2009-06-08T00:00:00Z"
  }
}

# Only PK and SK are key attributes. Grain, origin, energy and provenance remain
# ordinary fields, matching dynamodb_items.py and seed_demo.py exactly.
resource "aws_dynamodb_table" "demo" {
  for_each     = toset(["consumption", "anomalies", "forecasts"])
  name         = "${var.name_prefix}-${each.key}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"
  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  tags = local.tags
}

resource "aws_ssm_parameter" "api_configuration" {
  for_each    = local.api_configuration
  name        = "/${var.name_prefix}/api/${each.key}"
  description = "Non-secret configuration for the GreenTrack synthetic demo. Managed through Terraform."
  type        = "String"
  tier        = "Standard"
  value       = each.value
  tags        = local.tags
}
