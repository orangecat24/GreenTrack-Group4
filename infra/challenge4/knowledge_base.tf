locals {
  guidance_prefix = "guidance/"
  corpus_dir      = "${path.module}/../../assistant/corpus"
  corpus = {
    for item in jsondecode(file("${local.corpus_dir}/sources.json")) : item.file => item
  }
  embedding_model_arn = "arn:${data.aws_partition.current.partition}:bedrock:${data.aws_region.current.region}::foundation-model/amazon.titan-embed-text-v2:0"
  embedding_dimension = 256
}

resource "aws_s3_bucket" "corpus" {
  bucket_prefix = "${local.name}-corpus-"
}

resource "aws_s3_bucket_public_access_block" "corpus" {
  bucket                  = aws_s3_bucket.corpus.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "guidance" {
  for_each     = local.corpus
  bucket       = aws_s3_bucket.corpus.id
  key          = "${local.guidance_prefix}${each.key}"
  content      = file("${local.corpus_dir}/${each.key}")
  content_type = "text/plain; charset=utf-8"
}

resource "aws_s3_object" "guidance_metadata" {
  for_each = local.corpus
  bucket   = aws_s3_bucket.corpus.id
  key      = "${aws_s3_object.guidance[each.key].key}.metadata.json"
  content = jsonencode({
    metadataAttributes = {
      title     = each.value.title
      sourceUrl = each.value.url
      publisher = each.value.publisher
    }
  })
  content_type = "application/json"
}

resource "aws_s3vectors_vector_bucket" "guidance" {
  vector_bucket_name = "gt-vectors-${substr(sha256(aws_s3_bucket.corpus.id), 0, 32)}"
}

resource "aws_s3vectors_index" "guidance" {
  vector_bucket_name = aws_s3vectors_vector_bucket.guidance.vector_bucket_name
  index_name         = "guidance"
  data_type          = "float32"
  dimension          = local.embedding_dimension
  distance_metric    = "cosine"

  metadata_configuration {
    non_filterable_metadata_keys = ["AMAZON_BEDROCK_TEXT_CHUNK", "AMAZON_BEDROCK_METADATA"]
  }
}

resource "aws_iam_role" "knowledge_base" {
  name = "${local.name}-kb"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "bedrock.amazonaws.com" }
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        # The KB ID is assigned after creation. The trust initially limits the
        # service to Knowledge Bases in this account and Region.
        ArnLike = {
          "aws:SourceArn" = "arn:${data.aws_partition.current.partition}:bedrock:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "knowledge_base" {
  name = "guidance-ingestion"
  role = aws_iam_role.knowledge_base.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = local.embedding_model_arn
      },
      {
        Effect    = "Allow"
        Action    = "s3:ListBucket"
        Resource  = aws_s3_bucket.corpus.arn
        Condition = { StringLike = { "s3:prefix" = "${local.guidance_prefix}*" } }
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.corpus.arn}/${local.guidance_prefix}*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3vectors:GetIndex", "s3vectors:GetVectors", "s3vectors:PutVectors",
          "s3vectors:QueryVectors", "s3vectors:DeleteVectors"
        ]
        Resource = aws_s3vectors_index.guidance.index_arn
      }
    ]
  })
}

resource "aws_bedrockagent_knowledge_base" "guidance" {
  name     = local.name
  role_arn = aws_iam_role.knowledge_base.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_model_arn
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = local.embedding_dimension
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.guidance.index_arn
    }
  }

  depends_on = [aws_iam_role_policy.knowledge_base]
}

resource "aws_bedrockagent_data_source" "guidance" {
  knowledge_base_id    = aws_bedrockagent_knowledge_base.guidance.id
  name                 = "assistant-guidance"
  data_deletion_policy = "DELETE"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = aws_s3_bucket.corpus.arn
      inclusion_prefixes = [local.guidance_prefix]
    }
  }

  depends_on = [aws_s3_object.guidance_metadata, aws_s3_bucket_public_access_block.corpus]
}
