# Chat preflight correction: saved-plan review

Reviewed November 25, 2026, after the user generated the plan in PowerShell.
**Recommendation: proceeding with this exact saved plan is reasonable.** The
review does not guarantee that AWS operations or the deployed browser test will
succeed. No apply, new plan, upload, invalidation or AWS mutation was run by the
review session.

## Exact artifact reviewed

- File: `build/chat-cors.tfplan` (ignored; do not commit or share the binary).
- Terraform: 1.17.0; plan timestamp: `2026-11-25T21:54:59Z`.
- SHA256: `54762c568da9c3b87a7d3b2762fc6343eaf55d09cef0c62d668ab8f9a7677e17`.
- Account: 886565871385; application Region: eu-central-1.
- Summary: **2 additions, 2 in-place updates, 0 destructions/replacements**.

The pasted terminal output and a local, captured `terraform show -json` of the
saved plan were reviewed. Raw state/plan JSON and credentials were not printed.
All resource mutations are in `module.challenge1`; the extra update below was
investigated rather than assuming the original route-only estimate was exact.

## Changes and preservation checks

| Resource | Planned action |
| --- | --- |
| `aws_apigatewayv2_route.api` | Change `$default` to `GET /{proxy+}` in place; preserve its Lambda integration. |
| `aws_apigatewayv2_route.api_root` | Add `GET /` using the same integration, preserving the documentation redirect. |
| `aws_apigatewayv2_route.api_chat` | Add `POST /chat` using the same integration for chat and weekly summary. |
| `aws_cloudfront_distribution.frontend` | Update its origin configuration in place as explained below. |

CloudFront is not being deleted or replaced. The nested `- origin` / `+ origin`
display represents a change to its origin block. Before and after retain the
same regional frontend S3 endpoint, origin ID `frontend-s3`, OAC ID
`E14I2RDB1QI53W`, three connection attempts and ten-second connection timeout.
The only top-level distribution field with a planned difference is `origin`:

- An `s3_origin_config` block with `origin_access_identity=""` is added.
  This is compatible with the retained OAC: [AWS documents an empty legacy
  identity when using OAC](https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_S3OriginConfig.html).
  It does not create an OAI or change the bucket policy/public-access blocks.
- `response_completion_timeout` changes from the refreshed value 0 to a
  provider-computed value, known after apply. No explicit new timeout value is
  requested in the Terraform source.

This is acceptable configuration reconciliation alongside the route fix; it
does not redirect the origin to a different bucket or weaken OAC. The plan
cannot establish whether a later refresh will show this block again. If a future
plan repeats the difference, investigate provider normalization separately
instead of repeatedly applying it or hiding all origin changes with ignore rules.

All six Lake Formation resources are no-op. Existing IAM, data-lake resources,
Glue jobs/scripts, DynamoDB tables and Lambda have no planned mutations. Lambda
still has `APP_DATA_MODE=mock`. The CloudFront domain/API URL, website assets,
cache behavior and API/UI response contract do not change.

## Apply and test manually

From the repository root in the existing greentrack/eu-central-1 PowerShell
terminal, first verify that the binary has the reviewed hash:

```powershell
if ((Get-FileHash -LiteralPath 'build/chat-cors.tfplan' -Algorithm SHA256).Hash -ne '54762c568da9c3b87a7d3b2762fc6343eaf55d09cef0c62d668ab8f9a7677e17') { throw 'Plan differs from the reviewed file; stop.' }
```

Then apply that exact file. A saved-plan apply starts immediately without a
second yes/no prompt:

```powershell
& '.\.qa\terraform-1.17.0\terraform.exe' '-chdir=infra/environments/dev' apply '../../../build/chat-cors.tfplan'
```

Wait for `Apply complete!`; CloudFront can take several minutes. Do not close
the terminal or start another apply while it is running. If it fails, inspect
the error before proceeding; some operations may already have completed.
After success, with the deployed-test URL variables still set from the run guide:

```powershell
npm.cmd --prefix web run test:deployed
```

Expected result: `1 passed`. The test verifies successful preflight, exact CORS,
the public API origin and all four tabs including mock chat/weekly summary.
No Lambda rebuild, frontend upload/invalidation, seeding or Glue job rerun is
needed for this configuration correction. API Gateway request/Lambda invocation
and any applicable CloudFront charges still follow normal usage billing.

The browser pass is **pending**, not inferred from this plan. If the plan becomes
stale or code/artifacts/state change, generate and review a new plan rather than
using `-target`, overwriting state or destroying resources to force it through.
See [run-the-demo.md section 8.6](run-the-demo.md#86-recover-from-chat-preflight-http-405).
