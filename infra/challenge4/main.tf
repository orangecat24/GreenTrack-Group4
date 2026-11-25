terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.28.0"
    }
  }
}

data "aws_partition" "current" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  name = "${var.name_prefix}-assistant"
}

resource "aws_cloudwatch_log_group" "assistant" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 14
}

resource "aws_iam_role" "assistant" {
  name = local.name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "assistant_logs" {
  name = "assistant-logs"
  role = aws_iam_role.assistant.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.assistant.arn}:*"
    }]
  })
}

resource "aws_iam_role_policy" "assistant_model" {
  count = var.enable_bedrock_model ? 1 : 0
  name  = "assistant-model"
  role  = aws_iam_role.assistant.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = var.model_resource_arns
      },
      {
        Effect   = "Allow"
        Action   = "bedrock:ApplyGuardrail"
        Resource = aws_bedrock_guardrail.assistant.guardrail_arn
      }
    ]
  })
}

resource "aws_bedrock_guardrail" "assistant" {
  name                      = local.name
  blocked_input_messaging   = "I can answer read-only questions about energy use."
  blocked_outputs_messaging = "I can answer read-only questions about energy use."

  content_policy_config {
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }
}

resource "aws_bedrock_guardrail_version" "assistant" {
  guardrail_arn = aws_bedrock_guardrail.assistant.guardrail_arn
  description   = "GreenTrack energy assistant"
  # Publish a new version when the draft guardrail changes.
  lifecycle {
    replace_triggered_by = [aws_bedrock_guardrail.assistant]
  }
}

resource "aws_lambda_function" "assistant" {
  function_name    = local.name
  role             = aws_iam_role.assistant.arn
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  runtime          = "python3.14"
  handler          = "assistant.lambda_handler.handler"
  architectures    = ["x86_64"]
  memory_size      = 256
  timeout          = 12

  environment {
    variables = merge(
      { GREENTRACK_ASSISTANT_MODEL_MODE = var.enable_bedrock_model ? "bedrock" : "scripted" },
      var.enable_bedrock_model ? {
        GREENTRACK_ASSISTANT_MODEL_ID          = var.model_id
        GREENTRACK_ASSISTANT_GUARDRAIL_ID      = aws_bedrock_guardrail.assistant.guardrail_arn
        GREENTRACK_ASSISTANT_GUARDRAIL_VERSION = aws_bedrock_guardrail_version.assistant.version
      } : {}
    )
  }

  lifecycle {
    precondition {
      condition     = !var.enable_bedrock_model || (var.model_id != "" && length(var.model_resource_arns) > 0)
      error_message = "Bedrock mode requires an approved Claude model ID and scoped model resource ARNs."
    }
  }

  depends_on = [aws_iam_role_policy.assistant_logs, aws_iam_role_policy.assistant_model]
}
