locals {
  results_prefix = "athena-results/assistant/"
  gold_table     = "hourly_consumption"
  lake_bucket    = "arn:${data.aws_partition.current.partition}:s3:::${var.data_lake_bucket_name}"
  glue           = "arn:${data.aws_partition.current.partition}:glue:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}"
}

# The existing IAM-authenticated Athena SQL workgroup will be imported by name.
resource "aws_athena_workgroup" "assistant" {
  name = local.name

  configuration {
    # Preserve the scan cutoff observed on the existing workgroup.
    bytes_scanned_cutoff_per_query  = 1099511627776000
    enforce_workgroup_configuration = true

    result_configuration {
      output_location = "s3://${var.data_lake_bucket_name}/${local.results_prefix}"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy" "assistant_athena" {
  count = var.enable_athena ? 1 : 0
  name  = "assistant-athena"
  role  = aws_iam_role.assistant.id

  # Until Person 1 registers the location with Lake Formation, Athena needs
  # direct IAM reads of the verified Iceberg table's objects and metadata.
  lifecycle {
    precondition {
      condition     = var.hourly_gold_prefix != ""
      error_message = "Athena mode requires the confirmed hourly Iceberg table prefix for source reads."
    }
  }

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AssistantWorkgroupQueries"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution",
        ]
        Resource = aws_athena_workgroup.assistant.arn
      },
      {
        Sid      = "LocateLakeBucket"
        Effect   = "Allow"
        Action   = "s3:GetBucketLocation"
        Resource = local.lake_bucket
      },
      {
        Sid      = "ListApprovedPrefixes"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = local.lake_bucket
        Condition = {
          StringLike = { "s3:prefix" = ["${local.results_prefix}*", "${var.hourly_gold_prefix}*"] }
        }
      },
      {
        Sid    = "AssistantResultObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts",
        ]
        Resource = "${local.lake_bucket}/${local.results_prefix}*"
      },
      {
        Sid      = "ReadHourlyIcebergObjects"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${local.lake_bucket}/${var.hourly_gold_prefix}*"
      },
      {
        Sid      = "DescribeGoldDatabase"
        Effect   = "Allow"
        Action   = "glue:GetDatabase"
        Resource = ["${local.glue}:catalog", "${local.glue}:database/${var.gold_database_name}"]
      },
      {
        Sid    = "ReadHourlyCatalogTable"
        Effect = "Allow"
        Action = "glue:GetTable"
        Resource = [
          "${local.glue}:catalog",
          "${local.glue}:database/${var.gold_database_name}",
          "${local.glue}:table/${var.gold_database_name}/${local.gold_table}",
        ]
      },
      {
        # This Athena integration permission has no resource-level scope.
        # The Lake Formation grants below identify the authorized table.
        Sid      = "RequestLakeFormationDataAccess"
        Effect   = "Allow"
        Action   = "lakeformation:GetDataAccess"
        Resource = "*"
      },
    ]
  })
}

resource "aws_lakeformation_permissions" "assistant_gold_database" {
  count       = var.enable_athena ? 1 : 0
  principal   = aws_iam_role.assistant.arn
  permissions = ["DESCRIBE"]

  database {
    name = var.gold_database_name
  }
}

resource "aws_lakeformation_permissions" "assistant_hourly_gold" {
  count       = var.enable_athena ? 1 : 0
  principal   = aws_iam_role.assistant.arn
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = var.gold_database_name
    name          = local.gold_table
  }
}
