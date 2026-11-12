# One pipeline role shared by the Glue jobs (bronze now; silver and gold reuse
# it later). The g4- name prefix is required: the GitHub deploy role may only
# manage IAM roles that start with g4-.

data "aws_iam_policy_document" "glue_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue_pipeline" {
  name               = "${var.name_prefix}-glue-pipeline"
  assume_role_policy = data.aws_iam_policy_document.glue_trust.json
  tags               = local.tags
}

# AWS-managed baseline for Glue jobs: CloudWatch logs, Glue catalog access,
# and S3 access limited to aws-glue-* buckets (not ours, hence the inline
# policy below).
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_pipeline.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# What the pipeline may do in OUR bucket, by layer:
#   raw/ and scripts/  read only  (the pipeline never changes the source)
#   bronze/, silver/, gold/, glue-temp/  read and write (its own outputs)
data "aws_iam_policy_document" "glue_data_lake" {
  statement {
    sid       = "ListDataLake"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data_lake.arn]
  }

  statement {
    sid     = "ReadRawAndScripts"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.data_lake.arn}/${local.raw_prefix}*",
      "${aws_s3_bucket.data_lake.arn}/${local.scripts_prefix}*",
    ]
  }

  statement {
    sid = "WriteDerivedLayers"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.data_lake.arn}/${local.bronze_prefix}*",
      "${aws_s3_bucket.data_lake.arn}/silver/*",
      "${aws_s3_bucket.data_lake.arn}/gold/*",
      "${aws_s3_bucket.data_lake.arn}/${local.glue_temp_prefix}*",
    ]
  }
}

resource "aws_iam_role_policy" "glue_data_lake" {
  name   = "${var.name_prefix}-glue-data-lake"
  role   = aws_iam_role.glue_pipeline.id
  policy = data.aws_iam_policy_document.glue_data_lake.json
}
