# Stage 5: reviewed bounded gold load

Subsequent stage 6 executed the authorized load after matching rechecks:
175 written, 0 skipped/failed, all verified identical. See
[gold-local-run.md](gold-local-run.md). The original read-only review below is
retained as historical evidence; do not rerun its proposed write unnecessarily.

Reviewed November 26, 2026 on `test/person2-app-validation`, starting clean at
`2dacab7` (`feat: added gold consumption loader and honest UI coverage`).
**Recommendation: proceed to stage 6's bounded load after its explicit write
authorization and rechecks.** No conflicts or missing read capability were found.
This review does not authorize writes by itself or prove PutItem permission.

## Scope and verified destination

- Profile `greentrack`; STS confirmed account **886565871385** and the existing
  SSO DeveloperAdminAccess role/session. Application Region **eu-central-1**.
- Exact table: `g4-greentrack-dev-consumption`.
- ARN: `arn:aws:dynamodb:eu-central-1:886565871385:table/g4-greentrack-dev-consumption`.
- DescribeTable confirmed **ACTIVE**, **PAY_PER_REQUEST**, string **PK HASH** and
  string **SK RANGE**. No schema, capacity or permission changes were requested.
- Household `household-1`; `[2009-06-01T00:00:00Z, 2009-06-08T00:00:00Z)`.
  Source clock remains the project's UTC interchange convention, not a claim
  that the original UCI dataset was recorded in UTC.
- Only two partition/time-window Query reads were needed, with consistent reads
  and the existing pagination logic. No Scan or approximate ItemCount assumption.

| Partition | Candidate rows | New | Identical/skippable | Conflicts |
| --- | --- | --- | --- | --- |
| `HOUSEHOLD#household-1#GRAIN#hourly` | 168 | 168 | 0 | 0 |
| `HOUSEHOLD#household-1#GRAIN#daily` | 7 | 7 | 0 | 0 |
| Total | **175** | **175** | **0** | **0** |

The actual Query results contained no existing records in those two bounded
partitions/windows. This does **not** establish that the entire table is empty
or authorize changes to other households, dates or tables. The daily/hourly PKs
differ; their fixed-width timestamp SKs retain the existing convention.

## Source and validation evidence

The offline loader dry run passed again. Both CSV checksums, the exact source
manifest checksum, normalized snapshot identity, all expected unique bucket starts,
quality and hourly/daily reconciliation were revalidated before the live preview.

- Source manifest: `build/real-data/2026-11-26-gold-week/manifest.json`.
- Source manifest SHA256:
  `2cc84aceabcf19e830028648252cae300ff03eb0cc1f99af311e5e046f91e347`.
- Snapshot:
  `sha256:a59514c69cc1d37884952d82fc19ee5cc15101b2461bb517693f5a8237ea4e93`.
- Hourly CSV SHA256:
  `49b498b56026c246ae2b480231636e9e7f05c1790348f75356d6fb240bf52d7f`.
- Daily CSV SHA256:
  `25084d0c5e543fd9c5771bdf2092a6768e90bc26132e471bb62cfbbec2bd2fc4`.

All **168 hours and 7 days are complete**; null energy/incomplete/missing periods
and duplicate starts are all zero. Hourly and daily rows each describe the same
10,080 observed minutes. Do not add their counts/minutes/energy as separate usage.
Hourly energy sums to `147.32229999999999590` kWh; daily energy sums to
`147.322300000000019` kWh. This is **147.3223 kWh** at useful display precision;
the tiny difference is floating-point accumulation. Daily values reconcile within
0.000001 kWh and match the handoff's rounded figures. Source rows were not
manufactured, repaired or rounded before validation.

## Reviewed local files

Both files below were created locally and confirmed ignored by Git:

| Evidence | SHA256 |
| --- | --- |
| `build/real-data/gold-preview-1.json` | `3131f6d47aac4e29f74f6eb71a2ae712e1fa0aa0a96e2e03c8a59b67568baafc` |
| `build/real-data/reviewed-gold-load-1.json` | `f1fdc1cf3419fc157d2df1accd026b866ba85d1826f38b360689c88386e5e827` |

The preview records each candidate key/outcome and source/destination binding.
The concise reviewed-load manifest adds the exact window, source checksums,
quality, totals, table schema/status and permission-verification limits. Preserve
these files unchanged for stage 6. They contain no credentials or Terraform state.

Verified operations for the local session: STS GetCallerIdentity, DynamoDB
DescribeTable and both Query reads. No missing read grant was observed.
**PutItem was not attempted or simulated**, so effective conditional-write access
remains unverified. Read access does not prove it, and the SSO permission-set
name is not proof. If stage 6 receives AccessDenied, stop and retain its report;
the DataMax account/permission-set owner should review the smallest scoped
PutItem grant on the exact table, including existing Query/DescribeTable access.
Do not broaden IAM or use the application execution role as a loader identity.

## Exact proposed write: stage 6 only, not executed

Continue with the existing [stage 6 prompt](real-data-integration.md#persistent-checklist)
to authorize the reviewed bounded write and recheck identity/source/destination.
Do not run the following command merely because the preview passed.
For later manual execution, use repository-root PowerShell and the verified
greentrack profile in eu-central-1:

```powershell
$env:AWS_PROFILE = 'greentrack'
```

```powershell
$env:AWS_REGION = 'eu-central-1'
```

Verify the reviewed preview before using it:

```powershell
if ((Get-FileHash -LiteralPath 'build/real-data/gold-preview-1.json' -Algorithm SHA256).Hash -ne '3131f6d47aac4e29f74f6eb71a2ae712e1fa0aa0a96e2e03c8a59b67568baafc') { throw 'Preview differs; stop for review.' }
```

Only after stage 6 explicit authorization, the exact proposed command is:

```powershell
.\.venv\Scripts\python.exe api/load_gold.py --manifest 'build/real-data/2026-11-26-gold-week/manifest.json' --region eu-central-1 --consumption-table g4-greentrack-dev-consumption --write --reviewed-preview 'build/real-data/gold-preview-1.json' --approve-preview-sha256 '3131f6d47aac4e29f74f6eb71a2ae712e1fa0aa0a96e2e03c8a59b67568baafc' --report 'build/real-data/gold-write-1.json'
```

The loader revalidates both source inputs, checks the table and queries current
keys before writing. Conditional inserts protect against races after this review.
If another writer has inserted identical rows, they are safe skips. Any different
source/snapshot/content is a conflict: stop for review, never overwrite or delete.
The write report must be new; never discard earlier failure evidence to reuse a
filename. A partial failure is a partial/unconfirmed load, not success; use the
documented reviewed resume behavior after investigating the cause.

## Stage result and limits

No DynamoDB records, policies, resources, IAM/LF settings, Terraform state,
application configuration or deployed assets were changed. No seeding, apply,
commit or push occurred. Read-only queries incur normal DynamoDB read usage.
The existing mock website remains unchanged; keep DEPLOY_ENABLED unset/false.
The actual write and local gold API/browser verification belong to stage 6.
No application code changed, so the earlier 162/26-test baseline was not rerun;
this stage's checks were source validation, live read preview, evidence bindings
and documentation validation. See [gold-loader.md](gold-loader.md) for CLI rules.
