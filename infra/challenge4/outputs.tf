output "handoff" {
  description = "Resource references for Person 2's future route and Person 1's access and ingestion review."
  value = {
    lambda_arn              = aws_lambda_function.assistant.arn
    lambda_invoke_arn       = aws_lambda_function.assistant.invoke_arn
    runtime_query_role_arn  = aws_iam_role.assistant.arn
    knowledge_base_id       = aws_bedrockagent_knowledge_base.guidance.id
    knowledge_base_arn      = aws_bedrockagent_knowledge_base.guidance.arn
    knowledge_base_role_arn = aws_iam_role.knowledge_base.arn
    data_source_id          = aws_bedrockagent_data_source.guidance.data_source_id
    corpus_bucket           = aws_s3_bucket.corpus.id
    guardrail_arn           = aws_bedrock_guardrail.assistant.guardrail_arn
    guardrail_version       = aws_bedrock_guardrail_version.assistant.version
    vector_index_arn        = aws_s3vectors_index.guidance.index_arn
  }
}
