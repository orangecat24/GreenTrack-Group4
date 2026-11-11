resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name_prefix}-api"
  retention_in_days = 7
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/aws/apigateway/${var.name_prefix}-api"
  retention_in_days = 7
  tags              = local.tags
}

resource "aws_iam_role" "api" {
  name = "${var.name_prefix}-api-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "logs" {
  name = "${var.name_prefix}-api-logs"
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
    }]
  })
}

# In mock mode there is NO DynamoDB permission attached to the execution role.
# Changing data_mode in Terraform adds just Query on these three tables. The
# loader's BatchWriteItem permission belongs to a different, future identity.
resource "aws_iam_role_policy" "read_demo" {
  count = var.data_mode == "dynamodb" ? 1 : 0
  name  = "${var.name_prefix}-api-query"
  role  = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:Query"]
      Resource = [for table in aws_dynamodb_table.demo : table.arn]
    }]
  })
}

resource "aws_lambda_function" "api" {
  function_name = "${var.name_prefix}-api"
  role          = aws_iam_role.api.arn
  runtime       = "python3.14"
  architectures = ["x86_64"]
  handler       = "app.lambda_handler.handler"
  filename      = var.lambda_zip_path
  # fileexists lets fmt/init/validate run before the artifact is built. The
  # precondition still prevents an actual plan from accepting a missing ZIP.
  source_code_hash               = fileexists(var.lambda_zip_path) ? filebase64sha256(var.lambda_zip_path) : null
  memory_size                    = 512
  timeout                        = 15
  reserved_concurrent_executions = 2
  environment {
    variables = local.api_configuration
  }
  lifecycle {
    precondition {
      condition     = fileexists(var.lambda_zip_path)
      error_message = "Build the Linux Lambda ZIP with scripts/build_lambda.py before planning deployment."
    }
  }
  depends_on = [aws_iam_role_policy.logs, aws_iam_role_policy.read_demo]
  tags       = local.tags
}

resource "aws_apigatewayv2_api" "api" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"
  # CORS belongs ONLY to the gateway. FastAPI/local Vite behavior is unchanged.
  cors_configuration {
    allow_origins = sort(concat(["https://${aws_cloudfront_distribution.frontend.domain_name}"], tolist(var.local_cors_origins)))
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["accept", "content-type"]
    max_age       = 300
  }
  tags = local.tags
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 20000
}

resource "aws_apigatewayv2_route" "api" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_stage" "api" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit  = 2
  }
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.gateway.arn
    # No request bodies, chat text, query strings or authorization headers.
    format = jsonencode({
      requestId = "$context.requestId", status = "$context.status",
      routeKey  = "$context.routeKey", responseLength = "$context.responseLength"
    })
  }
  tags = local.tags
}

resource "aws_lambda_permission" "gateway" {
  statement_id   = "AllowThisHttpApi"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.api.function_name
  principal      = "apigateway.amazonaws.com"
  source_arn     = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
  source_account = data.aws_caller_identity.current.account_id
}
