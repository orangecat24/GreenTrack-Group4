# Starter guidance corpus

These short documents paraphrase general advice. The source manifest lists
each publisher, title and URL. Challenge 4 uploads the two documents and
matching Bedrock metadata sidecars under `guidance/`. The data source
restricts ingestion to that prefix. [Source manifest](sources.json) ·
[Challenge 4 Knowledge Base](../../infra/challenge4/knowledge_base.tf)

After authorized provisioning, a teammate can start an ingestion job for
the published data source, check its status and record the document set and
job ID. The Knowledge Base uses Titan Text Embeddings V2 with 256 float
dimensions to match the S3 Vectors index. The assistant's later retrieval
role needs `bedrock:Retrieve` on the approved Knowledge Base ARN. P3 03
packages the scripted energy-answer path and prepares the ingestion resources.
[Person 3 handoff](../../docs/person3-handoff.md)
