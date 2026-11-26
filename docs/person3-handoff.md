# Person 3 P3 03 assistant handoff

The standalone FastAPI `POST /chat` uses a scripted model and the local gold
fixture by default. The model selects an approved P3 02 tool, the service
checks its arguments against the requested household and normalized window,
and the tool performs the read. The service formats facts from the tool
result and uses the model's final turn to end the conversation. The Bedrock
adapter uses the same loop through Converse and was exercised with a fake
client. [Assistant app](../assistant/main.py) · [Tool contract](../assistant/README.md)

## Run the offline milestone

From the repository root, with the pinned dependencies installed in your
Python 3.14 environment, start the assistant on its own port. The requirements
files reuse the dependency pins already used by the API.

```powershell
python -m pip install -r assistant/requirements-dev.txt
$env:GREENTRACK_ASSISTANT_MODEL_MODE = 'scripted'
python -m uvicorn assistant.main:app --port 8001
```

In another PowerShell terminal, send this request.

```powershell
$body = @{
    household_id = 'household-1'
    start = '2009-06-01T00:00:00Z'
    end = '2009-06-02T00:00:00Z'
    message = 'How much energy did we use on June 1, 2009?'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8001/chat' -ContentType 'application/json' -Body $body
```

Expect **9.75 kWh observed across 210 of 1,440 minutes**, sourced from
`gold_hourly.json`. The response carries synthetic provenance,
`is_demo: true` and `assistant_connected: false`.

```powershell
python -B -m unittest discover -s assistant/tests -v
node fixtures/person3/check.mjs
git diff --check
```

## Build and check the Lambda

```powershell
python -B scripts/build_assistant_zip.py --wheel-dir path/to/linux-wheelhouse
python -B scripts/check_assistant_zip.py --structure-only
```

Provide the pinned Linux CPython 3.14 x86_64 wheels for an offline build.
Omit `--wheel-dir` to fetch the pinned public packages during build setup.
The builder creates `build/greentrack-assistant.zip` with
`assistant.lambda_handler.handler` and the synthetic hourly fixture.
On Linux x86_64 CPython 3.14, run
`python -B scripts/check_assistant_zip.py` to import the extracted ZIP,
send an API Gateway v2 event and check the synthetic result. Windows can
check the archive and run the source handler with Windows dependencies.

## Person 2 integration

Use the request fields and outcomes in the draft contract. `ok`,
`no_data` and `refused` use HTTP 200. Invalid bodies and windows use
HTTP 422 and a `detail` list. Dependency failures and exhausted tool budgets
use HTTP 503 with the chat envelope. A weekly summary requires exactly
seven midnight-to-midnight historical days. Forecast and anomaly sections
are labeled placeholders pending model results. The reserved synthetic
citation demonstrates the shape only. [Draft schema](../contracts/assistant.md)

The loop allows three model turns and two tool calls. It checks an
eight-second service budget between operations. The optional SDK client
uses one-second connect and two-second read timeouts with a single attempt.
The Lambda has a 12-second timeout. Review the end-to-end budget with
Person 2 against the existing 20-second Gateway integration timeout before
connecting the route. The dev root's `assistant` output will provide
`lambda_arn` and `lambda_invoke_arn` after provisioning. The explicit
`POST /chat` route, CORS and Lambda invoke permission belong to Person 2.
[Gateway settings](../infra/challenge1/api.tf)

## Person 1 resource review

The dev root references Challenge 4 behind `enable_assistant`, which
defaults to false. If enabled later, the Lambda defaults to the scripted
model and fixture. For a later authorized model check, review the Claude
model or inference profile supported by Converse and Guardrails in
`eu-central-1`, its exact invocation resource ARNs and quotas. The
`enable_assistant_bedrock_model` option requires explicit model inputs.
The gold executor defaults to synthetic data. The standalone Athena opt-in has
been exercised with a fake client. [Dev root wiring](../infra/environments/dev/assistant.tf) ·
[P3 04 verification handoff](person3-p304-verification.md)

The prospective `runtime_query_role_arn` identifies the separate Lambda
role for P3 04. Coordinate scoped Glue and Lake Formation gold grants,
source reads, the Athena workgroup and the encrypted results prefix with
Person 1. The Knowledge Base has a separate ingestion role, a private
corpus bucket and a matching Titan Text Embeddings V2 and S3 Vectors
configuration. Review embedding and S3 Vectors availability, index and
ingestion quotas, and scope the Knowledge Base role trust to the resulting
Knowledge Base ARN once available. Corpus metadata and the data source are
prepared for a later authorized ingestion job. The resource outputs,
including role ARNs, are pending provisioning.
[P3 02 access review](../assistant/README.md#sql-and-permissions-review-for-person-1) ·
[Corpus manifest](../assistant/corpus/sources.json) ·
[S3 Vectors Knowledge Base configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_knowledge_base)

With the provider already in a local filesystem mirror, run these checks
from the repo root. The init command disables the remote backend.

```powershell
terraform fmt -check -recursive infra/challenge4
terraform fmt -check infra/environments/dev/assistant.tf
terraform -chdir=infra/environments/dev init -backend=false -input=false -lockfile=readonly -plugin-dir=C:/path/to/mirror
terraform -chdir=infra/environments/dev validate
```

## Verification in this checkout

Windows Python 3.14 passed 34 assistant tests, including the HTTP API v2
event against the source handler. The 103 existing API tests and P3 01
fixture checker also passed. A rebuild from the local Linux wheelhouse
passed the ZIP structure check, and the shared API builder produced the
same package files as before. The Linux x86_64 packaged invocation passed
for the rebuilt P3 04 ZIP. [Packaged smoke test](person3-p304-verification.md#packaged-lambda-smoke-test-and-plan-review)

Terraform formatting and backend-disabled dev-root validation passed.
After the fast-forward to `5c024c7`, dev-root validation passed with the
locked AWS provider `6.73.0` installed from a checksum-verified local mirror. The checks
used synthetic rows, fake service responses and local provider schemas.
P3 04 covers live Athena arithmetic, actual runtime access and a real
model answer. [Gold handoff](gold-handoff.md) ·
[Lake Formation handoff](data-lake-lake-formation.md)
