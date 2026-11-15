resource "aws_s3_bucket_notification" "data_lake" {
  bucket      = aws_s3_bucket.data_lake.id
  eventbridge = true
}

resource "aws_glue_workflow" "pipeline" {
  name = "${var.name_prefix}-pipeline"
  tags = local.tags
}

resource "aws_glue_trigger" "start_on_upload" {
  name          = "${var.name_prefix}-start-on-upload"
  workflow_name = aws_glue_workflow.pipeline.name
  type          = "EVENT"
  tags          = local.tags

  event_batching_condition {
    batch_size   = 1
    batch_window = 60
  }

  actions {
    job_name = aws_glue_job.bronze.name
  }
}

resource "aws_glue_trigger" "silver_after_bronze" {
  name              = "${var.name_prefix}-silver-after-bronze"
  workflow_name     = aws_glue_workflow.pipeline.name
  type              = "CONDITIONAL"
  start_on_creation = true
  tags              = local.tags

  predicate {
    conditions {
      job_name = aws_glue_job.bronze.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    job_name = aws_glue_job.silver.name
  }
}

resource "aws_glue_trigger" "quality_after_silver" {
  name              = "${var.name_prefix}-quality-after-silver"
  workflow_name     = aws_glue_workflow.pipeline.name
  type              = "CONDITIONAL"
  start_on_creation = true
  tags              = local.tags

  predicate {
    conditions {
      job_name = aws_glue_job.silver.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    job_name = aws_glue_job.quality.name
  }
}

resource "aws_glue_trigger" "gold_after_quality" {
  name              = "${var.name_prefix}-gold-after-quality"
  workflow_name     = aws_glue_workflow.pipeline.name
  type              = "CONDITIONAL"
  start_on_creation = true
  tags              = local.tags

  predicate {
    conditions {
      job_name = aws_glue_job.quality.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    job_name = aws_glue_job.gold.name
  }
}

data "aws_iam_policy_document" "eventbridge_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "start_workflow" {
  statement {
    actions   = ["glue:NotifyEvent"]
    resources = [aws_glue_workflow.pipeline.arn]
  }
}

resource "aws_iam_role" "eventbridge_pipeline" {
  name               = "${var.name_prefix}-eventbridge-pipeline"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_trust.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "eventbridge_pipeline" {
  name   = "${var.name_prefix}-eventbridge-pipeline"
  role   = aws_iam_role.eventbridge_pipeline.id
  policy = data.aws_iam_policy_document.start_workflow.json
}

resource "aws_cloudwatch_event_rule" "raw_upload" {
  name = "${var.name_prefix}-raw-upload"
  tags = local.tags

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [aws_s3_bucket.data_lake.bucket] }
      object = { key = [{ prefix = local.raw_prefix }] }
    }
  })
}

resource "aws_cloudwatch_event_target" "start_pipeline" {
  rule     = aws_cloudwatch_event_rule.raw_upload.name
  arn      = aws_glue_workflow.pipeline.arn
  role_arn = aws_iam_role.eventbridge_pipeline.arn
}
