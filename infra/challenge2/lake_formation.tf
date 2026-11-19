data "aws_iam_session_context" "deployer" {
  arn = data.aws_caller_identity.current.arn
}

resource "aws_lakeformation_data_lake_settings" "this" {
  admins = concat(
    [data.aws_iam_session_context.deployer.issuer_arn],
    var.lake_formation_extra_admins,
  )
}

resource "aws_lakeformation_permissions" "pipeline_role_bronze_super" {
  principal   = aws_iam_role.glue_pipeline.arn
  permissions = ["ALL"]

  database {
    name = aws_glue_catalog_database.bronze.name
  }
}

resource "aws_lakeformation_permissions" "pipeline_role_silver_super" {
  principal   = aws_iam_role.glue_pipeline.arn
  permissions = ["ALL"]

  database {
    name = aws_glue_catalog_database.silver.name
  }
}

resource "aws_lakeformation_permissions" "pipeline_role_gold_super" {
  principal   = aws_iam_role.glue_pipeline.arn
  permissions = ["ALL"]

  database {
    name = aws_glue_catalog_database.gold.name
  }
}

resource "aws_lakeformation_permissions" "consumer_gold_database" {
  for_each    = toset(var.consumer_role_arns)
  principal   = each.value
  permissions = ["DESCRIBE"]

  database {
    name = aws_glue_catalog_database.gold.name
  }
}

resource "aws_lakeformation_permissions" "consumer_gold_tables" {
  for_each    = toset(var.consumer_role_arns)
  principal   = each.value
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = aws_glue_catalog_database.gold.name
    wildcard      = true
  }
}
