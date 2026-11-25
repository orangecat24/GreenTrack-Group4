data "aws_iam_policy_document" "sagemaker_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sagemaker_execution" {
  name               = "${var.name_prefix}-sagemaker-execution"
  assume_role_policy = data.aws_iam_policy_document.sagemaker_trust.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

data "aws_iam_policy_document" "sagemaker_data_lake" {
  statement {
    sid     = "ListDataLake"
    actions = ["s3:ListBucket"]
    resources = [
      "arn:aws:s3:::${var.data_lake_bucket_name}",
    ]
  }

  statement {
    sid     = "ReadGoldAndScripts"
    actions = ["s3:GetObject"]
    resources = [
      "arn:aws:s3:::${var.data_lake_bucket_name}/gold/*",
      "arn:aws:s3:::${var.data_lake_bucket_name}/${local.scripts_key}*",
    ]
  }

  statement {
    sid = "WriteArtifacts"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "arn:aws:s3:::${var.data_lake_bucket_name}/${local.artifacts_key}*",
    ]
  }
}

resource "aws_iam_role_policy" "sagemaker_data_lake" {
  name   = "${var.name_prefix}-sagemaker-data-lake"
  role   = aws_iam_role.sagemaker_execution.id
  policy = data.aws_iam_policy_document.sagemaker_data_lake.json
}
