# Biorn's Person 3 next steps

**Inspection date:** 22 November 2026

**Starting point:** P3 01, draft the model and assistant contracts and create a small, explicitly synthetic fixture package.

Start with **P3 01 contracts and fixtures**, then build **P3 02 approved query tools** and **P3 03 the assistant service**. Complete **P3 04 live data verification** before **P3 05–12 model, report, evaluation and demo work**. Person 1's gold schema is available now. Use it to draft the fixtures offline. The assistant's first tool-backed answer can be built before model training. The forecasting experiment follows verification of live gold, as the work plan specifies. [Three-person work plan](GreenTrack_Three_Person_Work_Plan.md) · [Project acceptance criteria](greentrack-challenges.md)

## Repository evidence

| Local ref | Commit | What it establishes |
| --- | --- | --- |
| `HEAD` on `feat/p3-assistant-foundation`, locally stored `origin/main` and `origin/HEAD` | `64c1ea1` | PR #7 merged the upload-triggered pipeline. The history includes the app infrastructure and workflow merge (PR #3), the data contract, and bronze, silver, quality and gold work. |
| Local `main` | `d568f24` | 19 commits behind this checkout. Use the checked-out files as the basis for the plan. |
| `origin/feature/person2-infrastructure` | `7eef2f8` | Included in HEAD. The application infrastructure, Lambda packaging and AWS workflow definitions are in this checkout. |
| `origin/feature/person1-challenge2-evidence-and-governance` | `43809d7` | One commit ahead of HEAD. Its Lake Formation changes, SageMaker skeleton and additional AWS evidence are available in the local Git ref. They are outside the checked-out code. |

This inspection compared local Git refs, source, contracts, fixtures, workflows and handoffs. Both Person 3 planning documents were already untracked at the start. The three-person plan is a local working copy for this review. GitHub refs, Actions runs and repository variables were not refreshed. No application, Glue, Terraform or browser tests ran, and no deployments, AWS/AI calls, credential reads or state inspection took place. [Working instructions](../AGENTS.md) · [Repository guide](../README.md)

### Application and release code in this checkout

- **App and storage.** FastAPI serves `/consumption`, `/anomalies`, `/forecast` and `/chat`. The default repository generates a synthetic week, fixed anomaly examples and an illustrative previous-day forecast. The opt-in DynamoDB reader and seed tool also use synthetic schema v1. The reader requires demo provenance. The React app sends chat and weekly-summary requests. It displays the disconnected response and has yet to render populated citation links. [API contracts](../api/app/models.py) · [Service](../api/app/service.py) · [Storage selection](../api/app/storage.py) · [DynamoDB item mapping](../api/app/dynamodb_items.py) · [Assistant view](../web/src/components/Assistant.tsx) · [Person 2 handoff](person2-handoff.md)
- **Infrastructure and packaging.** The existing dev Terraform root wires shared infrastructure and Challenges 1 and 2 in `eu-central-1`. Challenge 1 defines the API Lambda, HTTP API Gateway, DynamoDB, private S3 frontend and CloudFront. The configured Gateway `$default` route targets the application Lambda, which serves the chat placeholder. Its integration timeout is 20 seconds and that Lambda's timeout is 15 seconds. The app uses Mangum, and its Linux Python 3.14 ZIP builder collects Python source under `api/app/`. A separate `assistant/` package needs its own artifact or an agreed change to the builder. [Dev root](../infra/environments/dev/main.tf) · [Application module wiring](../infra/environments/dev/application.tf) · [Gateway and Lambda](../infra/challenge1/api.tf) · [Mangum adapter](../api/app/lambda_handler.py) · [ZIP builder](../scripts/build_lambda.py)
- **Release workflows.** `demo-checks.yml` defines credential-free application, ZIP, browser and Terraform configuration checks. `deploy-main.yml` defines a main-push release gated by `DEPLOY_ENABLED=true`, using OIDC and the existing dev root. Its deployed browser smoke checks the **mock application over HTTPS**. `aws-pr-plan.yml` defines an opt-in speculative plan for a labelled same-repository PR with a separate read-only role. Person 2's handoff describes prepared automation and historical test results. Activation, a successful release and live intelligence are separate checks. [Offline checks](../.github/workflows/demo-checks.yml) · [Main deployment](../.github/workflows/deploy-main.yml) · [Optional AWS PR plan](../.github/workflows/aws-pr-plan.yml) · [Deployment guide](deployment-pipeline.md)
- **Historical AWS readiness.** The foundation handoff records Person 1's report that bootstrap was applied from his laptop. The 11 November notes document earlier read-only checks of local SSO, bucket access, state object existence and GitHub role configuration. GitHub OIDC assumption, effective deployment write access and deployed application behavior still need their own evidence. Keep the existing foundation and dev root under the current owners. [Foundation handoff](foundation-handoff.md) · [Application infrastructure handoff](application-infrastructure.md)

### Data pipeline, fixtures and reported AWS results

- **Merged code.** The Glue jobs preserve the raw values in bronze, parse minute readings into silver, turn `?` or blank measurements into null, and merge duplicates by household and reading timestamp with newer loads taking precedence. The upload workflow runs bronze → silver → quality → gold on success of each preceding job. A failed quality step prevents that workflow from rebuilding gold. The dev `data_lake` output includes the catalog and table names, bucket, Athena results URI, Glue jobs, workflow and pipeline role. The Glue role is for the pipeline. The assistant needs its own runtime identity and consumer grants. [Bronze](data-lake-bronze.md) · [Silver](data-lake-silver.md) · [Quality](data-lake-quality.md) · [Orchestration](data-lake-orchestration.md) · [Dev data-lake outputs](../infra/environments/dev/datalake.tf)
- **Independently checked offline for this update.** Recalculating the checked-in CSV after deduplicating by timestamp gives 130 unique minutes from 131 rows. On 21 December 2006 the 10:00, 11:00 and 12:00 buckets give 1.767700, 0.516833 and 0.037767 kWh with 60, 58 and 10 measured minutes respectively. The sub-metering sums match the expected CSV. The partial day totals 2.3223 kWh over 128 measured minutes and peaks at 10:00, with a maximum minute power of 3.728 kW. The input is a **dataset-derived sample with an inserted duplicate**. The quality fail/fix CSVs are pipeline test inputs. Keep these separate from Biorn's new synthetic examples and the app's invented June 2009 values. [Raw sample](../fixtures/raw_sample.csv) · [Expected hourly results](../fixtures/expected_hourly.csv) · [Fixture recipe](../data/make_fixture.py)
- **Person 1's merged AWS report, 15 November.** The handoffs record fixture runs through all four jobs, matching Athena hourly, daily and peak results, and a clean re-upload with unchanged totals. This is useful P1 06–07 evidence for a small fixture in AWS. P3 04 still needs a representative historical window and results from the assistant's runtime identity. [Gold handoff](data-lake-gold.md) · [Upload workflow results](data-lake-orchestration.md)
- **Person 1's additional AWS report, 19 November.** The locally available commit `43809d7` reports full UCI ingestion (2,075,259 unique silver timestamps and 34,589 gold hourly rows), all seven demo days complete for `[2009-06-01, 2009-06-08)`, an intentional quality failure and repair, and silver upsert/time-travel examples. It also reports the SageMaker execution role and two Model Package Groups applied. Its Lake Formation handoff still calls for teammate runtime ARNs and consumer-role checks. The SageMaker skeleton still needs a pipeline definition, evaluated packages and endpoints. See `docs/data-lake-gold.md`, `docs/athena/verification_queries.sql`, `docs/data-lake-quality.md`, `docs/data-lake-lake-formation.md` and `docs/sagemaker-skeleton.md` at that commit. Ask Person 1 to confirm which version and results are ready to hand over. The AWS reports from both dates were read from Git and were not reproduced in this inspection.

## What the data contract and gold job provide

The draft data contract (v1) records the single source household (`household-1`), historical clock, source column dictionary and units, bronze/silver/gold fields, duplicate and missing-data rules, quality thresholds and a proposed demo week. The job builds three Iceberg summaries in `g4_greentrack_dev_gold`, partitioned by `year` and `month`. [Data contract](../contracts/data.md) · [Gold job](../data/glue/gold_job.py) · [Gold Terraform](../infra/challenge2/gold.tf)

| Gold table | Fields and calculation relevant to Person 3 |
| --- | --- |
| `hourly_consumption` and `daily_consumption` | `household_id` and `period_start` identify the bucket. Sum one-minute active-power readings divided by 60 to get `energy_kwh`. Sum sub-meter readings in Wh divided by 1,000 to get `kitchen_kwh`, `laundry_kwh` and `heater_ac_kwh`. Subtract those three from total energy to get `other_kwh`. `minutes_with_data` counts non-null active-power minutes. `is_complete` is true at 60 or 1,440 minutes respectively. |
| `daily_peak` | `household_id`, `day`, `peak_hour_start`, `peak_hour_kwh` and `max_minute_power_kw`. The hour with the greatest observed kWh wins, with the earlier start breaking ties. Minute power remains in kW. The peak row has no coverage fields of its own. |

### Decisions to confirm at the boundaries

| Topic | What to resolve |
| --- | --- |
| **Clock and windows** | The source clock is kept as written and the draft proposes treating it as UTC without a conversion. Silver parses the source strings and gold truncates to hours and days. The checked-in silver/gold jobs do not explicitly pin the Spark session timezone. Person 1 should confirm Spark and Athena interpretation and boundary behavior, and all three should agree on how the API and model split timestamps are serialized and described to users. Preserve `[start, end)` and select by bucket start. Resolve relative dates against the selected historical period or request clarification. |
| **Units and residuals** | Use the contract conversions and keep peak kW distinct from interval kWh. Confirm that the published catalog agrees, plus the rounding/tolerance and display rules. Gold sums the sub-meters independently of active power. Decide how to handle mismatched nulls or a negative/null residual in corrected data. Sub-meter labels describe circuits or groups, so answers about causes need supporting evidence. |
| **Missing data and coverage** | Gold groups existing silver rows. A bucket with zero non-null power readings can have null energy, and a bucket with no rows can be absent. A measured zero is usable data. The checked-in quality job evaluates silver as a whole, while the draft describes a per-file active-power null threshold. Confirm the quality scope separately from the completeness of each bucket. Choose how to represent absent, null and partial buckets, and specify observed/expected minutes, complete buckets and what totals mean in an incomplete window. The app's `covered_start/end` describe returned bucket boundaries only. Decide weekday/weekend denominators, minimum model/report history, and whether to exclude or impute missing inputs. Gold peaks can select a partial hour or an hour with null energy on an all-null day. Decide how to qualify or suppress those peaks. |
| **Schema and publication** | Confirm deployed Athena types/nullability, names and snapshot/run identifiers. The draft lists `minutes_with_data` as int and Spark's `count` produces a long, so validate the catalog and adapter mapping. Gold publishes tables sequentially with `CREATE OR REPLACE`. Agree which successful run or snapshots may be read together. Confirm the exact demo window and run with Person 1, then compare with independently calculated SQL totals. |
| **API, storage and model compatibility** | Map `period_start` to the API's `timestamp` and derive `interval_end` for the agreed grain. The current API requires numeric nonnegative energy and its reads are demo-only. Agree how nulls, detailed coverage, units, dataset provenance and model version/generation time reach the API, DynamoDB and reports. Preserve synthetic v1 for mock mode. Raw RCF scores need a separately documented threshold/flag. The current `score` is constrained to 0–1 and `expected_kwh` requires a separately defined expectation. Agree version/run keys and forecast selection with Person 2. |
| **Model and chat interfaces** | Keep per-endpoint content types, feature order and response shapes separate from Person 2's combined window Lambda contract. Agree forecast cutoff semantics, first target, 24 hourly targets, seasonal baseline and minimum history. Current chat uses `household_id`, `start`, `end`, `request_type` and a trimmed 1–2,000 character message for ordinary chat. Weekly summary already uses `request_type: "weekly_summary"`. The response currently has requested dates, `answer`, `citations: [{title,url}]` and fixed placeholder/demo/disconnected literals in Python. Agree live success/refusal/no-data/error behavior, provenance, seven-day and incomplete-week rules, forecast association and whether to add bounded context. |

The existing FastAPI and TypeScript types and the documented DynamoDB keys are the compatibility references. Forecast rows are keyed by origin plus target time, while the current anomaly key allows one record per household/hour. The mock week and illustrative forecast are good API examples and have no role in model-quality evaluation. [Python models](../api/app/models.py) · [TypeScript types](../web/src/api/types.ts) · [Mock data](../api/app/repository.py) · [Storage handoff](person2-handoff.md)

## Ordered work and handoffs

The file paths proposed below identify future deliverables. P3 01–03 can start offline in order, with review of shared interfaces in parallel. Live Athena, provisioning, training, endpoint calls and website verification need coordinated teammate handoffs and separate AWS evidence.

### P3 01 — Draft contracts and synthetic fixtures

**Status and prerequisite.** Partly supported by the gold draft/schema, the pipeline fixture and Person 2's app payloads. Person 3's contracts and synthetic fixtures are still to be written. Start from the checked-out files. Person 1 owns the data schema review, Person 2 owns the API integration review, and both review the examples before treating them as agreed.

**Files and work.** Create `contracts/models.md`, `contracts/assistant.md` and `fixtures/person3/{README.md,gold_hourly.json,gold_daily_expected.json,model_payloads.json,chat_examples.json}`. Draft the 24-hour target, same-hour previous-week baseline, candidate feature order, separate forecasting/RCF endpoint payloads and the combined window response. Record current versus proposed chat fields, including missing-data/refusal and weekly-summary examples. Include a tiny gold-shaped dataset with normal, partial, all-null and absent buckets, a measured zero and a known spike. Describe the duplicate case at the raw/silver boundary. Give citation-shaped examples clearly synthetic provenance.

**Completion and handoff.** Check fixture field names and types against the contract and job. Recalculate expected totals and coverage independently. Person 1 receives schema questions, model target and proposed input fields. Person 2 receives JSON examples and the list of prospective API/storage changes. Record unresolved decisions and service access separately from fixture arithmetic. Both teammates should be able to read and use the sample before accepting the handoff.

### P3 02 — Build approved query tools

**Status and prerequisite.** No tool implementation is present. Start offline once P3 01 supplies a reviewable sample and expected values. Person 1 reviews query arithmetic and grants before the live checks in P3 04.

**Files and work.** Add `assistant/{models.py,tools.py,query_templates.py,athena.py}`, `assistant/tests/{test_tools.py,test_athena.py}` and `assistant/README.md`. Define named read-only tools for totals, hourly patterns, weekday/weekend comparisons and sub-metering. Use fixed SELECT templates with parameterized values and approved configured identifiers. Validate household/window and bound rows, waiting and retries. Return typed values, units and coverage with explicit empty/failed states. Inject an offline fixture executor and stub the Athena boundary for tests.

**Completion and handoff.** Reproduce the fixture arithmetic, test comparison denominators, invalid dates/households, query and result limits, safe failure handling and refusal of arbitrary SQL or writes. Confirm the fixture path creates no AWS clients. Give example tool outputs to Person 2 and a list of approved tables, operations and result-prefix needs to Person 1.

### P3 03 — Build the assistant and resource definitions

**Status and prerequisite.** Person 2's placeholder, UI and Mangum adapter provide integration points. The assistant service and Challenge 4 resources have yet to be implemented. Start after P3 02 and a reviewable chat draft. Model training is a later dependency for reports.

**Files and work.** Add `assistant/{main.py,service.py,bedrock.py,settings.py,lambda_handler.py}`, dependency declarations, `assistant/tests/test_service.py`, `assistant/corpus/{README.md,sources.json}`, `infra/challenge4/` and `docs/person3-handoff.md`. Use FastAPI/Mangum and a bounded Claude tool loop with a scripted offline model adapter. Plan an assistant ZIP for the chosen Lambda runtime and test the packaged handler. Define the Lambda, scoped roles, Guardrails, guidance corpus in S3 and Bedrock Knowledge Base backed by S3 Vectors, including ingestion configuration. Record real source titles and URLs for the corpus. Person 1 coordinates dev-root wiring and checks model access, quotas, Region and resource compatibility before provisioning. Person 2 owns the explicit `POST /chat` route, CORS and invoke permission in the existing Gateway and agrees the timing budget with Biorn.

**Completion and handoff.** Offline, demonstrate a tool-backed answer with scripted model responses and exercise invalid tools, bounded rounds, missing data and errors. Review the artifact and Terraform via the existing dev root. Record later authorized deployment and resource checks separately. Give Person 2 the schema, timing plan and assistant Lambda ARN/invoke ARN when provisioned. Give Person 1 the runtime/query role ARN for grants and the corpus/model configuration for review.

### P3 04 — Verify live Athena data and a real answer

**Status and prerequisite.** Person 1's AWS reports supply a fixture comparison and a full-data candidate window. Live consumer access, the approved gold run and the assistant's actual result comparison remain open. Requires P3 03, P1 06's confirmed handoff and P1 08 access for the assistant role.

**Files and work.** Configure `assistant/settings.py` and `assistant/athena.py` with the agreed catalog, tables, workgroup, result prefix/encryption and permissions. Use `assistant/tests/integration/test_live_tools.py` and `evaluation/assistant/gold_ground_truth.json` to record expectations and checks. Person 1 supplies run/snapshot identifiers and independently reviewed SQL for the chosen window. Check the half-open filter explicitly when adapting the side-branch verification SQL. The role needs scoped catalog/Lake Formation and source reads plus the necessary Athena query and result-output operations.

**Completion and handoff.** Record the actual runtime role, Athena execution IDs, window and totals/coverage per tool. Check time boundaries, peak interpretation, sub-metering and normalized weekday/weekend comparisons. Verify one live assistant answer against those facts, with restrained explanations and visible dates. Hand Person 2 a reproducible request and expected facts, and give Person 1 any discrepancies or access failures. Keep weekly model inputs visibly stubbed until real publication.

### P3 05 — Establish a fair baseline and feature builder

**Status and prerequisite.** No experiment is present. Draft interfaces offline as needed. Fix live gold and complete P3 04 before accepting the experiment.

**Files and work.** Add `ml/{prepare.py,features.py,baseline.py,metrics.py}`, `ml/config/experiment.json`, `ml/tests/` and `ml/README.md`. Predeclare chronological train, validation and held-out boundaries, forecast origins, masking and a common 24-hour target. Compare against the same hour in the previous week. Propose lag/calendar features using information available at each origin. Document eligible history, training-only fitting of any imputation/scaling, MAPE near-zero rules and counts, and RMSE in kWh.

**Completion and handoff.** Reproduce splits, masks, baseline and metrics from the same gold snapshot, using equal eligible targets for the forecast and its baseline. Check leakage and missing hours with small examples. Give Person 1 processing inputs/outputs and Person 2 the reusable builder, order and missing-history rules.

### P3 06 — Train the forecast and anomaly models

**Status and prerequisite.** No training code or trained model is present in HEAD. Fixed app anomalies and illustrative forecasts are synthetic. Requires verified P3 05, an agreed SageMaker runtime with Person 1 and authorized training.

**Files and work.** Add `ml/{train_forecast.py,train_anomaly.py,evaluate.py}`, model configs and pinned ML dependencies. Train XGBoost, using a documented direct or recursive 24-hour strategy consistently in evaluation and serving. Train SageMaker's built-in Random Cut Forest on hourly inputs. Tune and select the anomaly threshold using training/validation data. Retain raw scores and threshold flags.

**Completion and handoff.** Reproduce the training invocations and held-out MAPE/RMSE comparison, with an improvement criterion agreed before tuning. Record an underperforming result as such and keep approval pending. Give Person 1 early metrics, script arguments, runtime and artifact shapes for P1 09.

### P3 07 — Publish the evaluated model package

**Status and prerequisite.** Model package and evaluation evidence are pending P3 06. The side-branch role and package-group report can inform the handoff after confirmation with Person 1.

**Files and work.** Add `ml/inference.py`, `ml/tests/test_inference_contract.py` and `evaluation/models/` with reproducible metrics and artifact references. Update `contracts/models.md`, payload fixtures and `ml/README.md`. Record processing/training/evaluation/inference entry points, dependencies, input/output channels, feature order, split dates, gold version, artifact IDs and failure cases.

**Completion and handoff.** Person 1 can invoke the scripts and map artifacts into P1 09–10. Person 2 can reproduce feature preparation and sample payloads for P2 08. Both review metrics and failure behavior before the authorized approval step.

### P3 08 — Validate pipeline, endpoints and publication

**Status and prerequisite.** HEAD has synthetic app reads. The SageMaker skeleton described on the other ref does not establish a pipeline run, approved model or serving endpoint. Requires P3 07, P1 09–10 and P2 08–09.

**Files and work.** Use `ml/tests/integration/test_serving.py` and `evaluation/models/serving_acceptance.md` with Person 1's future `infra/challenge3/` and Person 2's future `inference/` and result publication code. Trace processing through registration and approval, then call Person 2's window Lambda against a known period. Compare origin, feature order, multi-step strategy, threshold and both outputs to evaluation. Verify storage provenance and versions all the way to the app.

**Completion and handoff.** Record pipeline, registry, endpoint and output record versions and a Lambda request returning both real outputs. Give both teammates an accepted demo window. Person 2 supplies the Python result reader or agreed S3/DynamoDB read interface and permissions for reports.

### P3 09 — Ground advice and weekly reports

**Status and prerequisite.** The UI sends the weekly-summary action. Retrieval, citations, report assembly and Guardrails behavior are pending. Requires P3 04, proven KB ingestion from P3 03 and versioned model results from P3 08.

**Files and work.** Add `assistant/{retrieval.py,reports.py}` and focused tests. Update the assistant service, corpus manifest and handoff. Use Athena for measured facts, the agreed reader for anomalies and predictions, and the KB for attributable guidance. Include origin, dates, provenance and incomplete coverage in the report. Apply Guardrails and retain independent tool validation and refusal behavior.

**Completion and handoff.** Reconcile one real report against all three result types. Check that guidance citations resolve to retrieved sources and test missing data, ambiguity, out-of-scope and write requests. Give Person 2 the cited responses, summary and refusal examples for UI rendering and Gateway integration.

### P3 10 — Evaluate the assistant on 20 questions

**Status and prerequisite.** No evaluation suite is present. Draft cases offline now as supporting material, and run live acceptance after P3 09 and once Person 2 can call the service.

**Files and work.** Add `evaluation/assistant/{questions.json,run.py,README.md,results.json,report.md}`. Include known totals, comparisons, high usage, weekly reports, cited advice, historical date ambiguity, missing readings and refusal cases. Define expected facts, tolerances and behavior. Person 1 reviews SQL ground truth and Person 2 reviews UI request coverage.

**Completion and handoff.** Run all 20 against the live data path, retain failures and reruns, and show that each case meets its expectation. Give both teammates the runner, results and demo question set.

### P3 11 — Verify the deployed website

**Status and prerequisite.** The checked-in deployment smoke targets mock behavior. Live website acceptance needs P3 10 and Person 2's P2 10–11 route, UI and release verification.

**Files and work.** Coordinate live checks with Person 2 in `web/deployed/` and record them in `docs/person3-handoff.md`. Reproduce the evaluated requests through the public website and Gateway. Check facts, timestamps, citation links, summary, missing data and refusals, and tie the results to the deployed versions.

**Completion and handoff.** Match browser results to direct-service evidence and repeat affected checks after fixes. Share the release commit, exact requests and observed results with both teammates.

### P3 12 — Prepare demo and cleanup evidence

**Status and prerequisite.** Demo evidence depends on accepted model and assistant behavior through P3 11. An evidence outline may be drafted offline.

**Files and work.** Create `docs/person3-demo.md` linked to evaluation reports and handoffs. Show held-out baseline comparison, Registry approval, model versions, score interpretation, live questions, weekly narrative, citations and a refusal. Record gold run, release commit, model, assistant, KB/corpus, Guardrail and evaluation versions.

**Completion and handoff.** Rehearse the public demo and preserve the reproducible scripts, reports and artifact references. Give Person 1 the idle resource list for coordinated Terraform cleanup and give Person 2 the demo requests and version manifest for the release record.

## Coordination and checks

| Who | Confirm next |
| --- | --- |
| **Person 1** | Approve timestamp conventions, source units, coverage/null policies, catalog types and the selected gold run. Confirm the status of `43809d7`, publish accepted gold and SQL ground truth, and coordinate P1 08 consumer access, workgroup and result prefix. Check Claude and embedding model access, KB/S3 Vectors, Guardrails and SageMaker runtime/quotas in `eu-central-1`. For the model package, agree script arguments, artifact channels, approval evidence and endpoint mode. |
| **Person 2** | Review the provisional chat statuses, citations, weekly window/forecast behavior and endpoint/window payloads. Agree live DynamoDB/API mapping and publication, the report reader, assistant artifact and route timing. Confirm release activation and evidence when ready. Own shared Gateway, API and UI integration. |
| **All three** | Choose one editor per shared contract and review the fixtures together. Agree the forecast cutoff, splits, feature and missing-history policy, metrics, improvement criterion and acceptance reviewers. Record signed-off interfaces and reproducible checks in the relevant Markdown handoffs. |

This document needs only a Markdown viewer. For a later local app check with the dependencies already present, serve the FastAPI app in mock mode and start Vite in a second PowerShell terminal. [API startup](person2-handoff.md) · [Frontend startup](../web/README.md)

```powershell
# Terminal 1, repository root
$env:APP_DATA_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload

# Terminal 2, repository root
Set-Location web
npm.cmd run dev
```

Open `http://127.0.0.1:5173` for the app or `http://127.0.0.1:8000/docs` for the API. These commands were reviewed for the plan and not run. Later changes can reuse `.\.venv\Scripts\python.exe -m pytest -c api\pytest.ini api\tests -q`, the frontend's `test:run`, `lint`, `build` and `test:e2e` scripts, and the registered-root Terraform helper as relevant. Report future offline checks and live results with their own evidence. [PR checks](pr-checks.md)

## Immediate next task

**Do P3 01 now.** Create the draft model and assistant contracts with a small synthetic fixture package that Person 1 and Person 2 can review. Use the merged gold job as the schema reference and record open decisions in the drafts so the review can proceed offline.

```text
Implement only P3 01 in the current GreenTrack checkout. Read AGENTS.md,
docs/Biorn_Person3_Next_Steps.md, docs/GreenTrack_Three_Person_Work_Plan.md,
contracts/data.md, data/glue/gold_job.py, fixtures/expected_hourly.csv,
api/app/models.py and web/src/api/types.ts.

Create draft contracts/models.md and contracts/assistant.md plus
fixtures/person3/README.md, gold_hourly.json, gold_daily_expected.json,
model_payloads.json and chat_examples.json. Base the gold field names and
units on the current job and document unresolved catalog types, timestamp
convention, null versus absent buckets, coverage and API/storage mapping.
Use household-1 and visibly label every new fixture as synthetic in its
documentation and payload or fixture metadata. Keep table rows gold-shaped.

Include a complete bucket, partial bucket, all-null bucket, absent hour,
measured zero and a known spike. Describe duplicates at the raw/silver
boundary. Independently recalculate the expected energy and coverage.
Propose a 24-hour target and same-hour previous-week baseline. Keep the
forecast and RCF endpoint payloads separate from the combined window
Lambda payload. Include chat, weekly summary, no-data, refusal and
citation-shaped examples. Label illustrative scores and citations so they
cannot be mistaken for model output or retrieved evidence.

Check the JSON and arithmetic with tools already available offline.
Record decisions that need Person 1 or Person 2 review, how to reproduce
the fixture checks and what each teammate receives. Link the new package
from the relevant handoff. Preserve existing work and shared runtime
contracts. Stay within contracts, fixtures and their handoff links.
Leave query tools, app code, infrastructure and models for later tasks.
Use no AWS or AI service, credentials or Terraform state. Do not install
dependencies, train, deploy, commit or push.
```
