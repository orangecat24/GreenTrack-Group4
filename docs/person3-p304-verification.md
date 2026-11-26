# P3 04 Athena verification handoff

The offline milestone exercises the configured Athena executor through
`POST /chat` using fabricated wire responses. Person 1 reported **24.054 kWh**
for the complete day of 1 June 2009 in the 19 November workflow run. The
expected hourly coverage derived from that complete day is **1,440 of
1,440 minutes**, 24 complete hours and zero partial, all-null or absent
hours. The reported total is rounded to three decimal places. Live hourly
coverage still needs to be checked independently. [Person 1 gold handoff](gold-handoff.md)
· [Request and expected results](../evaluation/assistant/gold_ground_truth.json)

## Request and comparison

Send this body to the standalone assistant's `POST /chat`.

```json
{
  "household_id": "household-1",
  "start": "2009-06-01T00:00:00Z",
  "end": "2009-06-02T00:00:00Z",
  "request_type": "chat",
  "message": "How much energy did we use on June 1, 2009?"
}
```

The SQL sums the hourly table using the same start-inclusive, end-exclusive
window and checks the published daily row separately. Compare totals at
three decimal places and coverage counts exactly. Check that row count and
distinct hours both equal 24. The selected day is a Monday. A weekday
comparison on that window has no eligible weekend hours. A separate approved
window that includes a weekend is needed for live comparison of both groups.
[Comparison SQL](athena/person3_june_1.sql)

## Console benchmark

On 26 November 2026, the project user supplied Athena console results for
both comparison queries. The hourly query returned 24 distinct hours,
24.054 kWh to three decimal places, 1,440 of 1,440 measured minutes and
24 complete hours. Partial, all-null and absent hour counts were all zero.
The daily table independently returned 24.054 kWh, 1,440 measured minutes
and `is_complete = true` for 1 June 2009 at 00:00 UTC.

These results were supplied by the user from their console session. The
workgroup, query execution IDs and gold snapshot were not supplied. The
assistant Lambda role still needs its own query and chat verification.

## Data mode and offline checks

The standalone app defaults to fixture data and the scripted model. Run its
offline checks from the repo root after installing the assistant's pinned
development dependencies.

```powershell
python -B -m unittest discover -s assistant/tests -v
node fixtures/person3/check.mjs
git diff --check
```

The dev root defaults the standalone Lambda to fixture data and a scripted
model. The `enable_assistant_athena` variable switches data mode independently
of model mode. Terraform sets `GREENTRACK_ASSISTANT_DATA_MODE` and
`GREENTRACK_ASSISTANT_ATHENA_WORKGROUP` for the Lambda. The adapter uses
`eu-central-1`, the fixed `AwsDataCatalog.g4_greentrack_dev_gold.hourly_consumption`
table, and the workgroup's enforced result settings.
[Dev wiring](../infra/environments/dev/assistant.tf)

The fake test checks the configured client, actual parameter binding,
pagination and the resulting HTTP envelope. A completed Athena read uses
`provenance.source: "athena"` and its execution ID, with `is_demo: false`.
That flag identifies the selected data source. `assistant_connected` stays
false pending agreement on live integration semantics. A read failure
returns a safe HTTP 503 with null coverage and no execution ID. The default
synthetic request still returns 9.75 kWh with clearly marked provenance.

Terraform formatting and dev-root validation passed locally with locked AWS
provider `6.73.0` from a local mirror and the backend disabled. All 38
assistant tests and the Node fixture checker passed.

## Workgroup adoption and access

The user reports creating `g4-greentrack-dev-assistant` in `eu-central-1`
with Athena SQL, IAM authentication, customer-managed results, SSE-S3, and
override of client-side settings. The reported results location is
`s3://g4-greentrack-dev-datalake-886565871385/athena-results/assistant/`.
The matching Terraform resource is prepared locally. Before adoption, confirm
these settings in the intended account, plus workgroup state, engine version,
tags, expected bucket owner and ACL, and any limits, metrics, or logging
settings. Review all differences after import, including provider default
tags. [Challenge 4 Athena configuration](../infra/challenge4/athena.tf)

The first P3 04 plan in the shared dev account exposed two differences
from the deployed configuration. Person 2's validation commit `9883c93`
defines the deployed `GET /{proxy+}`, `GET /`, and `POST /chat` routes
and preserves the SageMaker role's `ALL` and `DESCRIBE` gold database
grant. Use those four Terraform file revisions when previewing P3 04
with the current deployed application. The workgroup resource keeps the
observed scan cutoff of 1,099,511,627,776,000 bytes per query.

For the reconciled review, the four files from Person 2's commit are
used in an isolated planning snapshot. The data-quality ruleset copy
uses CRLF line endings, which match both the deployed object's ETag and
Terraform's recorded source checksum. The shared source files in this
checkout remain as they were. Review local source-path differences and
CloudFront origin normalization explicitly whenever regenerating a plan.

## Packaged Lambda smoke test and plan review

On 26 November 2026, the rebuilt `build/greentrack-assistant.zip` passed both
the archive structure check and the scripted Lambda invocation in Ubuntu
under WSL on Linux x86_64 with CPython 3.14. Reproduce it from the repository
root in WSL with `python3.14 -B scripts/check_assistant_zip.py`. The checker
loads the handler and native dependency from the extracted ZIP and asserts
HTTP 200 and 9.75 kWh across 210 of 1,440 minutes using the synthetic fixture.

The saved review plan is `build/p304-assistant-reconciled.tfplan`. It
reported 1 import, 21 additions, 8 changes and 0 destroys. The review
preserved the deployed Gateway routes and SageMaker grant. The remaining
shared differences involved the API ZIP path, CloudFront origin fields
and five data-lake objects with matching checksums. Keep this plan for
review and regenerate it from the intended deployment checkout after
bringing in Person 2's fixes. No apply or separate import has run.

The user verified that the `greentrack` CLI profile selects account
`886565871385`. If the SSO session expires, sign in again before planning.

Challenge 4 grants the assistant role query actions on its workgroup,
S3 results access under its prefix, and Glue and Lake Formation access
for the gold database and named hourly table. The repository records
that source location registration with Lake Formation was deferred.
For the documented unregistered setup, confirm the hourly table's actual
S3 root and where its Iceberg metadata and data objects reside. The user
provided the console location for the table root. Set
`assistant_hourly_gold_prefix` to
`gold/g4_greentrack_dev_gold.db/hourly_consumption/`.
If registration is already active or the objects have a different layout,
agree the source access policy with Person 1 before applying. Verify that
the deploying identity can grant the two Lake Formation permissions.
[Lake Formation access model](https://docs.aws.amazon.com/lake-formation/latest/dg/access-control-underlying-data.html)

## Later authorized deployment

1. From the repo root, build `build/greentrack-assistant.zip` using
   `python -B scripts/build_assistant_zip.py --wheel-dir path/to/linux-wheelhouse`.
   Run `python -B scripts/check_assistant_zip.py` on Linux x86_64 CPython 3.14
   with the exact ZIP intended for deployment.
2. Coordinate use of the shared dev state with Person 1. Confirm the workgroup
   is outside Terraform state, and preserve the environment's existing
   variable settings, including any existing gold consumer overrides. In an
   approved shell for the correct account, run from the repository root:

   ```powershell
   terraform -chdir=infra/environments/dev init -input=false -lockfile=readonly
   ```

   Pass the usual shared dev variable file if the environment requires one.
   The dev root's gated import block previews adoption when the assistant
   module is enabled. The plan should show the existing workgroup at
   `module.challenge4[0].aws_athena_workgroup.assistant` with ID
   `g4-greentrack-dev-assistant`.
3. Plan with Athena enabled and Bedrock disabled. Set the verified hourly
   source prefix in the following command and include the usual shared
   environment variables or variable file.

   ```powershell
   $hourlyPrefix = 'gold/g4_greentrack_dev_gold.db/hourly_consumption/'
   terraform -chdir=infra/environments/dev plan -input=false '-var=enable_assistant=true' '-var=enable_assistant_athena=true' '-var=enable_assistant_bedrock_model=false' "-var=assistant_hourly_gold_prefix=$hourlyPrefix" -out=p304-assistant.tfplan
   ```

   Check that the workgroup is adopted without creation, deletion, or
   replacement and that any in-place differences are intentional. Check
   that existing Lake Formation grants, the shared API, and Gateway stay
   intact. Review all planned Challenge 4 resources, including the Lambda,
   IAM policies and the two new grants. Apply only the approved saved plan
   with `terraform -chdir=infra/environments/dev apply p304-assistant.tfplan`.
   Carry the approved module enablement into future shared dev runs once
   the module has resources in state.
4. Invoke the standalone Lambda directly after approval. From PowerShell at
   the repo root, create an HTTP API v2 event using the request above:

   ```powershell
   $request = (Get-Content -Raw evaluation/assistant/gold_ground_truth.json | ConvertFrom-Json).request
   $event = @{
       version = '2.0'
       routeKey = 'POST /chat'
       rawPath = '/chat'
       rawQueryString = ''
       headers = @{ 'content-type' = 'application/json' }
       requestContext = @{
           stage = '$default'
           http = @{ method = 'POST'; path = '/chat'; sourceIp = '127.0.0.1' }
       }
       body = ($request | ConvertTo-Json -Compress)
       isBase64Encoded = $false
   }
   New-Item -ItemType Directory -Force build | Out-Null
   $event | ConvertTo-Json -Depth 8 | Set-Content -Encoding ascii build/p304-event.json
   aws lambda invoke --region eu-central-1 --function-name g4-greentrack-dev-assistant --payload fileb://build/p304-event.json build/p304-response.json
   $response = Get-Content -Raw build/p304-response.json | ConvertFrom-Json
   $response.statusCode
   $response.body | ConvertFrom-Json
   ```

   Check the invocation metadata for a function error, then check the
   inner HTTP 200 and `status: "ok"`. Require Athena provenance with an
   execution ID, 24.054 kWh at three decimal places, and the exact coverage
   above. Record the Lambda role from the deployed configuration or
   Terraform output and tie the execution ID to the approved workgroup
   and publication. The caller's permission to invoke Lambda is separate
   from the assistant role used to query gold.

## Evidence pending for live verification

1. Person 1 confirms the historical clock, catalog types, gold run or
   Iceberg snapshot, and the reported daily baseline. Capture the approved
   publication identity separately from query execution IDs.
2. Confirm the actual assistant runtime role ARN, its scoped Glue and Lake
   Formation permissions, access to source objects, and the Athena workgroup
   with enforced result prefix and encryption. Use that identity for the
   actual read. [Lake Formation handoff](data-lake-lake-formation.md)
3. Save the app version, normalized request window, comparison SQL execution
   IDs and numeric results. Save the assistant's Athena execution ID,
   response, coverage, elapsed time, and any mismatch. Confirm the response
   fits the service timing budget and both reads used the approved publication.
4. Extend later live checks to the hourly pattern, sub-metering, and
   weekday/weekend tools. Keep peak hour energy in kWh distinct from peak
   single-minute power in kW. Record the model and Guardrail configuration
   and answer separately if Claude is included in live acceptance.

The historical benchmark comes from Person 1's handoff. The newer console
results were supplied by the project user. Live Lambda verification and
shared app integration are still pending.
