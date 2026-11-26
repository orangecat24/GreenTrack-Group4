GreenTrack Three Person Work Plan

Detailed responsibilities sequence and handoffs for the complete project

Build one working system together: raw electricity readings become clean tables, forecasts, anomaly records, a web dashboard, and answers from a Bedrock assistant. Every member owns a part of the system and helps verify the connections to the other two parts.

Use the labels Person 1, Person 2, and Person 3 until you assign names. This is a recommended division of the work, based on the project brief and the attached Python back-end guide. The original assignment requirements still determine what the group must deliver.

| **Person** | **Primary responsibility**      | **Main outputs**                                                                                                         |
| ---------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Person 1   | Data and cloud foundation       | Bronze to gold pipeline; Terraform foundation; Lake Formation; SageMaker training workflow and endpoint infrastructure.  |
| Person 2   | Application and API integration | React website; Python FastAPI APIs; DynamoDB loaders; model invocation Lambda; GitHub Actions deployment.                |
| Person 3   | Models and AI assistant         | Forecasting and anomaly algorithms; evaluation; Bedrock tools, knowledge base, guardrails, chat API, and weekly reports. |

## How challenge 3 is shared

Person 3 writes and evaluates the model code. Person 1 puts that code into the SageMaker Pipeline and provisions approved models. Person 2 invokes the deployed endpoints and delivers their results to the application. Record each handoff before the next person integrates it.

## How to read this plan

Read pages 1 to 6 together before starting. Person 1 then follows pages 7 to 12, Person 2 pages 13 to 18, and Person 3 pages 19 to 24. Pages 25 and 26 contain the shared acceptance checks, demo order, and cleanup responsibilities.

Each task has an identifier, a start condition, ordered actions, a completion check, and a handoff. Finish tasks in your own list in order, while using mocks to keep working when another person has not yet delivered a dependency.

# Shared technology and working rules

## Use one agreed implementation

Use Python with FastAPI for HTTP APIs, Boto3 for AWS calls, PySpark for Glue, and the SageMaker Python SDK for model development. Use React with TypeScript and Vite for the website. Flask remains an allowed alternative, but this plan uses FastAPI consistently. Mangum adapts FastAPI to Lambda; Uvicorn runs it locally.

Use Lambda plus API Gateway for the back-end, S3 plus CloudFront for the website, and on-demand DynamoDB for application records. This selects one of the brief's allowed architectures. The ECS Fargate and ALB alternative is not part of this work plan. The selected Lambda architecture does not require adding a VPC under the brief.

## Keep file ownership clear

| **Area in the repository**                                                 | **Lead owner**                                                   |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| data/ and infra/challenge2/                                                | Person 1                                                         |
| infra/bootstrap/ infra/shared/ infra/challenge3/ and Terraform root wiring | Person 1                                                         |
| web/ api/ loaders/ inference/ and infra/challenge1/                        | Person 2                                                         |
| .github/workflows/ and application deployment scripts                      | Person 2 with Terraform commands from Person 1                   |
| ml/ assistant/ evaluation/assistant/ and infra/challenge4/                 | Person 3                                                         |
| contracts/ fixtures/ docs/ and acceptance evidence                         | One named editor per change; all three review relevant contracts |

These folder names are suggestions. Keep one group repository. Every merge needs a pull request and at least one teammate review. Suggested rotation: Person 2 reviews Person 1, Person 3 reviews Person 2, and Person 1 reviews Person 3. Ask the receiving teammate to review interface changes.

## Apply the project rules from the first commit

- Use only the DataMax AWS account for this project. Prefix and tag resources with your group name.
- Define every AWS resource through Terraform, including roles, endpoints, triggers, and knowledge-base resources. Use S3 remote state with locking. Do not use console-only changes, CDK, or CloudFormation.
- Use GitHub Actions for checks and deployment. Use OIDC and IAM roles instead of long-lived AWS keys. Store secrets in Secrets Manager or SSM Parameter Store.
- Use small instances, spot training where supported, and remove idle endpoints after demos. Each person tests their own component before asking another person to integrate it.

# Milestones and the order of work

Schedule the work using the phases below. Phase 0 is your first working session. At that session, agree on target dates that fit your deadline and availability. Move to the next milestone when its checks pass. A person can begin an independent later task while another person finishes the current phase.

| **Phase**              | **Person 1** | **Person 2**                        | **Person 3** | **Exit check**                                                                        |
| ---------------------- | ------------ | ----------------------------------- | ------------ | ------------------------------------------------------------------------------------- |
| 0 Agree and prepare    | P1 01 to 02  | P2 01                               | P3 01        | Contracts agreed; repository and AWS foundation usable.                               |
| 1 Build small versions | P1 03 to 04  | P2 02 to 05                         | P3 02 to 03  | HTTPS app and automatic deployment work with mocks; raw and clean sample data exist.  |
| 2 Connect real data    | P1 05 to 08  | P2 06 to 07; start P2 08 with stubs | P3 04 to 05  | Upload produces verified gold tables; real consumption reaches the dashboard.         |
| 3 Connect models       | P1 09 to 10  | P2 08 to 09                         | P3 06 to 08  | Model beats baseline; registered and approved models are callable; app shows outputs. |
| 4 Complete assistant   | P1 11        | P2 10 to 11                         | P3 09 to 10  | Live chat, citations, weekly reports, and assistant evaluation pass.                  |
| 5 Verify and demo      | P1 12        | P2 12                               | P3 11 to 12  | Fresh deployment and full demo succeed; idle resources removed afterward.             |

## Use a short daily coordination check

At the start of each shared work session, each person states the task they are doing, the input they need, and the deliverable they will hand off next. Update the issue board with the task identifier and a link to its pull request. End the session with one reproducible check, not only a verbal status update.

## Keep work moving when a dependency is late

Person 2 builds against saved mock JSON; Person 3 starts the assistant against a hand-built sample of gold tables. Person 1 can create the training workflow structure while model scripts are being completed. Record temporary inputs visibly and replace them before final acceptance. If a task stays blocked for a full shared session, pair on that blocker before starting optional features.

# What all three do in the first session

## First agree on the smallest complete product

- Choose a historical reference period within the dataset, a 24-hour forecast horizon, and a household identifier. The dataset covers one household; do not invent extra real households to fill a chart.
- Choose XGBoost with lag and calendar features for the first forecasting model and the required built-in Random Cut Forest for anomalies. DeepAR and LightGBM are alternatives allowed by the brief if you later change the forecast approach.
- Agree that the first web release has all four views with sample data, followed by real consumption, model outputs, and finally the fully grounded assistant.

Optional extensions remain optional: Bedrock AgentCore, scheduled Batch Transform, and extra charts. Complete the required behavior first. If a framework or algorithm choice changes, update contracts and dependent tasks together.

## Then create the shared contracts

Person 1 proposes gold-table fields and a small data sample. Person 2 proposes the API JSON. Person 3 proposes model payloads and chat answers. Review these together using pages 5 and 6, then commit them before building features. A contract is a written agreement about input and output names, types, units, and meaning.

## Then prepare the repository and access

Person 2 creates folders, the README, and the task board. Person 1 prepares the Terraform bootstrap, group naming, and deployment role. Person 3 checks access to the chosen Claude model, SageMaker algorithms, and Bedrock Knowledge Bases with S3 Vectors in the intended Region. Inspect service availability early; do not replace a required service without agreement with the project supervisor.

Each person installs the tools needed for their role. Everyone needs Git and a supported Python environment. Person 1 needs Terraform and Glue development tools. Person 2 needs Node.js and npm for React. Person 3 needs the model-development dependencies. Record compatible versions in the repository instead of assuming the newest version works with every AWS runtime.

## Finish the session with three concrete artifacts

- A role assignment and issue board listing the task identifiers from this plan.
- Versioned contracts and fixtures that all three can read, with no credentials in them.
- A repository setup guide and the next handoff owner for each person.

For this plan, a fixture means a small saved input or output used during development. Include a normal period, missing values, a duplicate timestamp, and a known spike. Keep source-shaped input fixtures separate from manually calculated expected summaries so tests can catch mistakes.

# Agree on the data contract before coding

## Person 1 leads this agreement with the other two

Write contracts/data.md and include example rows. The following is a suggested contract, not an extra prescribed schema. All three must use the same names or change them together through a reviewed pull request.

| **Record or rule**           | **What to agree and write down**                                                                                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Household and time           | household_id; timestamp meaning; original time zone; explicit offset or UTC conversion policy; start inclusive and end exclusive for requested windows.                         |
| Hourly and daily consumption | Period start, energy_kwh, sample counts or coverage, and the kitchen, laundry, and water-heater/AC breakdown. Define peak statistics separately.                                |
| Quality and missing values   | How ? becomes null; what is removed as a duplicate; acceptable null rate and ranges; when an aggregate is incomplete. Missing observations must not silently become zero usage. |
| Forecast result              | household_id, forecast_origin, predicted_timestamp, predicted_kwh, model_version, and generated_at. An origin is the last time the model may use as known history.              |
| Anomaly result               | household_id, observed_timestamp, observed_kwh, anomaly_score, is_anomaly, model_version, and generated_at.                                                                     |
| Units and features           | Confirm source units from the dataset documentation. Specify the conversion into the forecast target, sub-metering units, feature order, and handling of missing hours.         |

## Resolve the common calculation traps once

Power and energy are different quantities. For example, one minute at a constant 1 kW represents 1/60 kWh. Use the source units and interval length when aggregating; do not simply label a sum of power readings as energy. Independently check a tiny sample by hand before using the whole dataset.

Keep the source timestamps traceable and document any time-zone assumption. Make a clear decision for ambiguous local times. Do not label an unconverted timestamp as UTC. All API filtering, Athena queries, and model splits must follow the same decision.

Use dates from the historical dataset in demonstrations. Show the selected reference period in the UI. A question such as "last Tuesday" must be resolved against that context or clarified. Predictions for the dataset's future are not predictions for the current calendar week.

# Agree on APIs and handoff packages

## Person 2 owns the shared HTTP interface

Use one API Gateway with the required /consumption, /anomalies, /forecast, and /chat paths. Person 2 owns the Gateway, route wiring, CORS settings, and invoke permissions. Person 3 owns the assistant Lambda and gives Person 2 its ARN, which is its AWS resource identifier. This allows /chat to use its own Lambda without creating a second competing public API.

For the three data reads, agree on household, start, end, grain where relevant, page size, and cursor. A cursor lets the browser request the next page. Return records, units, actual covered dates, and an empty list when no matching records exist. Give invalid input a consistent error response; do not invent data.

For POST /chat, agree on question, household_id, reference dates, and bounded conversation context. Return answer text, structured sources when advice is cited, and useful period metadata. Person 3 owns the response schema; Person 2 owns rendering it. Define a weekly-report request through the same API contract so the button and back-end agree.

## Person 3 defines model inputs and outputs

Write contracts/models.md with feature names and order, numeric types, payload format, sample inputs, and sample outputs for both models. Keep the window-based Lambda contract separate from the lower-level endpoint payload. Person 2's Lambda prepares features from approved historical inputs, calls both endpoints, and returns forecast plus anomaly scores.

## Make every handoff reviewable

| **Handoff**     | **Sender and receiver**     | **Required contents**                                                                                                        |
| --------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Gold ready      | Person 1 to Persons 2 and 3 | Catalog names, S3 locations, schema version, sample rows, quality policy, verified SQL totals, and granted role access.      |
| Model package   | Person 3 to Persons 1 and 2 | Runnable scripts, dependencies, feature builder, payload examples, artifacts, metrics, split dates, and model configuration. |
| Serving ready   | Person 1 to Persons 2 and 3 | Approved model version, endpoint names, Region, expected payloads, permissions, and an invocation example.                   |
| Assistant ready | Person 3 to Person 2        | Lambda ARN, request and response schemas, sample answers and citations, report request, and evaluation results.              |

A handoff is accepted only when the receiver can run the provided example and reproduce its result. Send resource names through Terraform outputs and configuration parameters rather than copying credentials or hardcoding account-specific values.

# Person 1 Prepare data and the cloud foundation

You own the data lake and the shared Terraform foundation. Later, you turn Person 3's model scripts into a managed SageMaker training workflow. You do not own the website or the assistant implementation.

## P1 01 Define schemas and a trustworthy sample

**When to start:** Phase 0, with P2 01 and P3 01 before feature development.

1\. Inspect the source file layout and its documentation. Record the semicolon separator, date and time fields, missing marker ?, row count scale, and source units.

2\. Propose hourly and daily gold schemas, timestamp rules, coverage fields, and peak and sub-metering outputs. Review them with Persons 2 and 3.

3\. Create a small source-shaped fixture and independently calculated expected hourly and daily results. Include missing and duplicate rows.

4\. Commit contracts/data.md, fixtures, and a data dictionary explaining each field. Agree on how schema changes will be reviewed.

**Done when:** All three can explain one sample row and independently agree on the expected summary values.

**Hand off:** Give Persons 2 and 3 the fixture, gold schema, expected numbers, and historical demo dates.

## P1 02 Create shared AWS infrastructure

**When to start:** Phase 0, once the group name, AWS Region, and repository are agreed.

1\. Write Terraform bootstrap code for the state S3 backend and locking. Bootstrap it through a documented procedure, then use remote state for the main environment.

2\. Create the group naming and tagging convention, GitHub OIDC trust and IAM deployment role, and shared configuration locations. Limit trust to the intended repository and workflow context.

3\. Create challenge-module skeletons and define their inputs and outputs. Own root wiring so teammates do not independently create the same shared resources.

4\. Give Person 2 the Terraform commands and role identifier needed for GitHub Actions. Confirm a minimal plan can run using temporary credentials.

**Done when:** Remote state works with locking, resource ownership is clear, and the workflow can assume the deployment role without static keys.

**Hand off:** Person 2 receives the deployment role, backend settings, module interfaces, and bootstrap instructions.

# Person 1 Build bronze and silver

## P1 03 Preserve and convert the raw data

**When to start:** Phase 1, after P1 02; use the small fixture before the full file.

1\. Define the S3 raw landing and bronze Parquet locations, Glue job role, and bronze catalog database through Terraform. Keep the source file exactly as received.

2\. Write the bronze Glue job to read the semicolon-separated CSV and produce Parquet without cleaning business values. Add source filename and load timestamp metadata.

3\. Register the table in the bronze catalog database. Keep raw inputs, converted outputs, scripts, and query results in separate prefixes so the next trigger can be scoped safely.

4\. Run the fixture, compare input and output counts and values, then try a larger sample. Record how a row can be traced to its source file.

**Done when:** The original file remains available, bronze Parquet is queryable, and conversion does not remove or silently repair source observations.

**Hand off:** Show Persons 2 and 3 the bronze schema and traceability example; Person 3 can inspect representative raw patterns.

## P1 04 Clean the data into Iceberg tables

**When to start:** Phase 1, after bronze conversion succeeds.

1\. Write a PySpark silver job that combines date and time, converts ? to null, casts types, and removes duplicate timestamps using the agreed rule.

2\. Write an Apache Iceberg silver table partitioned by year and month. Register it in the silver catalog database and keep ingestion metadata for traceability.

3\. Use deterministic fixtures to check valid timestamps, null handling, malformed inputs, duplicates, and records crossing hour or month boundaries. Document what happens to invalid rows.

4\. Make reprocessing safe: the same source must not double the logical observations. Choose an overwrite or merge strategy deliberately and keep it reproducible.

**Done when:** Athena reads correct typed silver rows, duplicates follow the agreed policy, and the fixture matches its expected cleaned output.

**Hand off:** Give Person 3 a clean sample for inspecting features, while keeping the gold contract as the final training interface.

# Person 1 Verify quality and create gold

## P1 05 Add visible data quality checks

**When to start:** Phase 2, after P1 04 and before declaring data ready.

1\. Create Glue Data Quality rules for null rates, allowed value ranges, and duplicate timestamps. Record the threshold and purpose of each rule.

2\. Run them at the silver layer and retain their results. Define whether a failure blocks gold publication or marks a run unsuccessful so consumers do not receive unnoticed bad data.

3\. Run one fixture expected to pass and separate fixtures expected to fail. Confirm the failure appears in the job or workflow output.

4\. Record counts before and after cleaning, rejected records where applicable, and the amount of usable data. Make the checks available to the deployment workflow.

**Done when:** A teammate can intentionally trigger a quality failure and locate its reason without asking you to inspect your laptop.

**Hand off:** Give Persons 2 and 3 the quality rules and usable-data policy; flag any feature or UI assumptions affected by missing data.

## P1 06 Produce and verify business summaries

**When to start:** Phase 2, once silver data and its quality policy are stable.

1\. Create gold hourly and daily consumption, peak-hour statistics, and kitchen, laundry, and water-heater/AC sub-metering summaries. Include the agreed coverage and units.

2\. Register gold tables in the gold catalog database. Partition or organize them so the expected Athena time-window queries are practical.

3\. Check the hand-calculated fixture, then compare hourly and daily totals over a real period. Investigate mismatches rather than changing expected values to fit the output.

4\. Publish the gold handoff package from page 6. Freeze a first schema version and announce its availability to Persons 2 and 3.

**Done when:** Athena returns verified hourly and daily values and all required gold outputs exist under a documented schema.

**Hand off:** Person 2 can build the consumption loader and Person 3 can run approved analysis queries and prepare model features.

# Person 1 Automate and govern the data lake

## P1 07 Trigger the complete pipeline on upload

**When to start:** Phase 2, after the bronze, silver, gold, and quality jobs work individually.

1\. Use a Glue Workflow or Step Functions state machine to run bronze, silver, quality checks, and gold in dependency order. Choose one orchestrator for the first version.

2\. Define a new-file trigger for the raw CSV landing prefix through Terraform. Restrict it so Parquet outputs and query-result writes cannot trigger the pipeline again.

3\. Pass the source file or run identifier through the jobs. Test a successful upload, a quality failure, and a retry of the same input.

4\. Publish the latest successful gold run identifier or manifest for downstream consumers. Agree with Person 2 how the gold-to-DynamoDB loader is launched after success.

**Done when:** A new CSV upload automatically reaches gold, failures are visible, and retries do not duplicate published totals.

**Hand off:** Person 2 receives a stable success signal and output manifest; Person 3 receives the available data period and run identifier.

## P1 08 Add permissions and Iceberg demonstrations

**When to start:** Phase 2, before the gold-data milestone is accepted.

1\. Configure Lake Formation access by layer. Restrict bronze and silver writes to the pipeline role and give the intended application, SageMaker, and assistant tool roles gold read access.

2\. Coordinate role identifiers with Persons 2 and 3. Keep catalog creation and grants separate where needed so Terraform modules do not depend on each other in a cycle.

3\. Demonstrate one incremental upsert on a silver table, then query an earlier snapshot using Iceberg time travel. Save both queries and their observed results.

4\. Test the real consumer roles, including the assistant query role. Remember that Athena needs permission to write query-result files even when source tables are read-only.

**Done when:** Required roles can read gold, unauthorized layer writes are blocked, and the upsert and time-travel examples are reproducible.

**Hand off:** Give both teammates catalog names, result-bucket configuration, role access confirmation, and a verified SQL example.

# Person 1 Build the managed model workflow

## P1 09 Prepare SageMaker pipeline infrastructure

**When to start:** Phase 3 after gold is usable; begin the skeleton while Person 3 completes model scripts.

1\. Ask Person 3 for the model package specification: processing, training and evaluation entry points, dependencies, artifacts, input channels, and feature contract.

2\. Create Terraform definitions for the SageMaker Pipeline, relevant roles, model package groups, and artifact locations. Person 3 owns ml/ scripts; put workflow generation and infrastructure wiring in your area.

3\. Generate a JSON pipeline definition with the SageMaker Python SDK. Let Terraform create or update the pipeline resource from that definition; do not use an SDK deployment as a second source of infrastructure truth.

4\. Represent processing, forecast training, anomaly training, evaluation, and registration with explicit dependencies. Coordinate the GitHub Actions pipeline-run command with Person 2.

**Done when:** The workflow structure is reviewable, points to versioned scripts, and can be created through Terraform.

**Hand off:** Give Person 3 the pipeline interface and ask them to verify script arguments, outputs, metrics, and dependency order.

## P1 10 Register approve and deploy model versions

**When to start:** Phase 3 after P3 07 supplies evaluated model code and artifacts.

1\. Run the pipeline through GitHub Actions and inspect each step. Persist evaluation reports and register versioned forecast and anomaly model artifacts.

2\. Keep a Model Registry approval step. Have Person 2 review Person 3's metrics before an authorized approval; record which version was approved.

3\. Provision real-time or supported serverless endpoints through Terraform for the approved versions. Confirm algorithm and Region compatibility before choosing the mode; use small instances and spot training where supported.

4\. Publish endpoint names, Region, model version, payload examples, and runtime permissions. Invoke the examples before asking Person 2 to connect the app.

**Done when:** An approved version is traceable to its training inputs and evaluation, and both deployed models return expected response shapes.

**Hand off:** Person 2 receives the serving-ready package; Person 3 verifies prediction and score semantics against their evaluation.

# Person 1 Support integration and final verification

## P1 11 Make data and infrastructure repeatable

**When to start:** Phase 4 while Persons 2 and 3 complete the application and assistant.

1\. Run the complete data path with a new historical input file. Check workflow status, counts, gold values, loader notifications, and downstream read permissions.

2\. Review all challenge modules for group tags, least-privilege roles, configuration parameters, and accidental console-only dependencies. Person 2 owns application code; Person 3 owns assistant code.

3\. Prepare a deployment runbook listing bootstrap, build artifacts, pipeline execution, model approval, endpoint provisioning, and data loading in the actual order required.

4\. Help Person 2 verify the fresh-environment procedure. Preserve training scripts, manifests, model configuration, and source data locations so the system can be reconstructed.

**Done when:** A teammate can follow the documented process and identify the input and output of each deployment stage.

**Hand off:** Give Person 2 the infrastructure runbook and Person 3 the stable demo tables and configuration outputs.

## P1 12 Demonstrate the pipeline and clean up resources

**When to start:** Phase 5 after the page 25 acceptance checks, then again immediately after the demo.

1\. Create a fresh isolated group environment or equivalent clean deployment test through Terraform with Person 2. Verify the application, data path, and approved model deployment prerequisites.

2\. Own the demo segment showing CSV arrival, automatic bronze-to-gold processing, quality checks, Athena aggregates, and the Iceberg upsert and time-travel evidence.

3\. Keep a short resource inventory and coordinate endpoint lifetime with the other two. Remove SageMaker endpoints and idle resources through the maintained Terraform process after demonstrations.

4\. Retain code, reports, necessary source data, and reconstruction instructions. Make deletion of retained data or state deliberate rather than part of routine endpoint cleanup.

**Done when:** The pipeline demo can be repeated and the inventory shows which resources were removed or intentionally retained.

**Hand off:** All three receive the final infrastructure status and the instructions needed to rebuild the environment later.

# Person 2 Prepare the application and API

You own the user-facing application, its API Gateway, application records, model invocation, and deployment workflows. Person 3 supplies the assistant service and model behavior; Person 1 supplies trustworthy tables and the AWS foundation.

## P2 01 Create the shared repository and API contract

**When to start:** Phase 0 with P1 01 and P3 01.

1\. Create the agreed repository folders, README, task board, and pull-request process. Add all three members and require at least one teammate review for merges.

2\. Create reproducible Python environments and front-end dependency files. Exclude local credentials, generated large datasets, and local environment files from commits.

3\. Propose typed JSON examples for /consumption, /anomalies, /forecast, and /chat. Agree on periods, units, missing-data behavior, pagination, and consistent error responses.

4\. Commit contracts/api.md, sample responses, and local setup commands. Name the owner of each shared file before teammates edit it.

**Done when:** All three can clone the repository and use the same API examples without depending on unpublished local files.

**Hand off:** Give Person 1 the DynamoDB access patterns and Person 3 the expected chat, report, and model-window response shapes.

## P2 02 Build a local FastAPI service with mocks

**When to start:** Phase 1, after the first contracts are agreed.

1\. Create FastAPI routes for consumption, anomalies, and forecast reads. Use the agreed request and response models and return seeded fixtures initially.

2\. Add input checks for date order, supported grain, household, and page size. Test a normal request, invalid dates, empty results, and pagination behavior.

3\. Run the API locally with Uvicorn and inspect its generated documentation. Package FastAPI and Mangum for Lambda through a reproducible dependency installation step.

4\. Keep service logic separate from fixture or DynamoDB readers so real storage can replace the mock implementation. Reserve /chat for Person 3's integration.

**Done when:** A teammate can call the local endpoints, receive documented JSON, and see predictable validation errors.

**Hand off:** Give Person 3 a working API example and Person 1 the Lambda package requirements for infrastructure integration.

# Person 2 Build the interface and application storage

## P2 03 Build all four browser views

**When to start:** Phase 1, using P2 02 and fixture responses while real data is being prepared.

1\. Create the React TypeScript application with Vite. Add the consumption dashboard, anomaly list, forecast chart, and chat panel to one coherent navigation flow.

2\. Add household and date selection where needed. Use one API client module and show units, selected dates, loading states, empty states, and readable error messages.

3\. Build charts from the fixture JSON rather than hardcoded values inside components. Use distinct series or labels for observations and predictions.

4\. Agree with Person 3 on displaying source citations and a weekly-report button. Implement their visual placeholders now so the chat service can be connected later.

**Done when:** All four views work locally with mocks and the dates and units are visible.

**Hand off:** Give Person 3 a screenshot or runnable page and the exact answer and citation fields the interface expects.

## P2 04 Create the application AWS resources

**When to start:** Phase 1 after P1 02 provides the remote state, roles, and module inputs.

1\. Write infra/challenge1/ for the API Lambda, API Gateway, S3 front-end hosting, CloudFront, and on-demand DynamoDB tables. Use Terraform outputs for URLs and names.

2\. Design DynamoDB keys for household and time-range queries. Define separate keys or tables for readings, anomalies, and forecasts, including multiple forecast origins when needed.

3\. Create least-privilege application and inference roles and configuration parameters. Ask Person 1 to grant the loader any required gold data access.

4\. Own Gateway routes, browser CORS configuration, and invocation permissions. Later wire /chat to Person 3's Lambda ARN rather than creating the assistant resources twice.

**Done when:** Terraform plans cleanly and the storage design supports the agreed reads without full-table scans for normal time windows.

**Hand off:** Give Person 1 runtime role ARNs for permissions and Person 3 the Gateway integration contract.

# Person 2 Automate deployment and load gold data

## P2 05 Create GitHub Actions checks and releases

**When to start:** Phase 1 after P1 02 and P2 04; extend as later components arrive.

1\. Create workflows that run Terraform formatting, validation, and plan on pull requests, together with the relevant Python and front-end checks.

2\. On merge to main, build the front-end, package Python services and Glue or model scripts as needed, then apply infrastructure and publish application artifacts in a documented order.

3\. Use the GitHub OIDC role from Person 1. Serialize applies and releases for the same environment. Consume artifact names and outputs rather than creating cloud resources outside Terraform.

4\. Include smoke checks after release and expose useful logs. Add model-pipeline execution commands from Person 1 and evaluation commands from Person 3. Keep model approval separate from routine application deployment.

**Done when:** A reviewed merge automatically updates the HTTPS app and its Python API; a failed check prevents a bad release.

**Hand off:** All three receive workflow instructions, required inputs, logs, and the current deployed URLs.

## P2 06 Load real consumption into DynamoDB

**When to start:** Phase 2 after P1 06 and P1 07 provide a verified gold output and completion signal.

1\. Implement a Python loader using Boto3. Read the agreed gold export or query result, map it into application items, and write hourly and daily summaries.

2\. Make the load repeatable using stable item keys and the gold run identifier. Retrying the same run should update the same items rather than create duplicates.

3\. Connect the loader to the successful pipeline signal agreed with Person 1. Handle failed or partially completed loads visibly; publish only verified successful data to normal API readers.

4\. Compare item counts and totals against Person 1's expected Athena results for a selected period. Test a retry and confirm that the result is unchanged.

**Done when:** New successful gold data reaches DynamoDB through a repeatable process and matches the published analytical totals.

**Hand off:** Tell Persons 1 and 3 which run and periods are available through the application and how to find load failures.

# Person 2 Connect real reads and prepare inference

## P2 07 Switch the dashboard to real consumption

**When to start:** Phase 2 after P2 06; keep model panels on clearly marked fixtures until their outputs exist.

1\. Replace fixture reads for /consumption with DynamoDB queries using the agreed partition and time keys. Preserve the response schema already used by React.

2\. Implement bounded time windows and pagination. Check inclusive start and exclusive end behavior against the same Athena query and timestamp policy.

3\. Display real totals, hourly or daily series, peak information, and sub-metering breakdowns. Show missing or incomplete data honestly using the coverage fields.

4\. Run a browser check comparing one selected period across gold SQL, DynamoDB, API JSON, and the chart. Save the matching values as integration evidence.

**Done when:** The real consumption view agrees with the verified gold data and handles empty or invalid periods predictably.

**Hand off:** Give Person 3 an example of the live consumption API and its period and unit metadata.

## P2 08 Implement the window-based model Lambda

**When to start:** Start in Phase 2 with P3 01 payload fixtures; connect live endpoints in Phase 3 after P1 10.

1\. Write a Python Lambda handler accepting a household, reference window, forecast origin, and agreed horizon. Return both forecasts and anomaly scores in one documented response.

2\. Use Person 3's feature builder and exact feature order. Prepare only data allowed at the forecast origin; never include later observed readings while constructing a forecast.

3\. Call both SageMaker endpoints with Boto3 using configuration from Person 1. Test normal responses, invalid windows, missing history, and a failed endpoint.

4\. First verify the logic with saved model responses. After the serving-ready handoff, invoke real endpoints and compare shapes and values with Person 3.

**Done when:** A direct Lambda invocation for a given time window returns both required model outputs from deployed models.

**Hand off:** Give Person 3 live invocation results and Person 1 any concrete permission or endpoint configuration failures.

# Person 2 Publish models and connect chat

## P2 09 Load model outputs and complete model views

**When to start:** Phase 3 after P2 08 returns real results and Person 3 approves their interpretation.

1\. Persist forecast and anomaly outputs in the agreed application shape. Keep timestamp, forecast origin where relevant, score or prediction, generation time, and model version.

2\. Extend the loader or inference completion path so results reach DynamoDB reliably. If you publish an S3 result export, document its path and run identifier for Person 3's weekly reports.

3\. Connect /forecast and /anomalies reads to these real items. Keep cached display reads distinct from the Lambda demonstration that invokes both models.

4\. Complete the forecast chart and anomaly list. Check model version, time axis, target units, threshold flags, and repeated generation of the same result window.

**Done when:** The app displays real forecasts and anomalies, and a teammate can trace a chart point to a model version and result record.

**Hand off:** Person 3 receives accessible result data and a documented Python reader or internal service function for report generation.

## P2 10 Connect the real assistant and reports

**When to start:** Phase 4 after P3 04 provides live chat and P3 09 provides cited advice and reports.

1\. Wire API Gateway /chat and its invocation permission to Person 3's assistant Lambda. Provide required configuration through Terraform outputs or parameters.

2\. Replace the chat fixture client with the real request. Render answer text, dates, and source titles or URLs according to the contract. Support bounded conversation history as agreed.

3\. Wire the weekly-report button to the agreed request. Show consumption, anomaly, and forecast explanations without relabeling predictions as historical observations.

4\. Test a real data question, cited advice, a weekly report, a refused write request, invalid input, and a service error through the browser.

**Done when:** The full assistant experience works from the deployed website, including citations, report generation, and understandable refusals.

**Hand off:** Give Person 3 browser observations and example failing requests; give Person 1 any specific routing or permission issues.

# Person 2 Verify delivery and present the application

## P2 11 Run the complete integration and release checks

**When to start:** Phase 4 once live consumption, model outputs, and the assistant are available.

1\. Write a short integration check that uploads or selects the agreed demo input, waits for successful processing, and checks known numbers through the API.

2\. Use a predictable model window and assistant question. Confirm that the UI, SQL results, forecast records, and cited answer refer to the same household and dates.

3\. Verify a clean deployment with Person 1 using the documented bootstrap and artifact prerequisites. Confirm static asset deployment, API configuration, CORS, and all required routes.

4\. Merge a harmless reviewed change and observe build, tests, Terraform apply, deployment, and smoke checks. Capture the commit and release evidence.

**Done when:** A fresh deployment and a later main-branch update both work using the documented automation.

**Hand off:** All three receive the release evidence, outstanding defects, and one shared final-demo environment.

## P2 12 Own the application demo and release record

**When to start:** Phase 5 after all acceptance checks pass.

1\. Prepare browser bookmarks or a short script showing consumption, anomalies, forecast, chat citations, and the weekly report for the chosen historical period.

2\. Coordinate timing with Person 1's pipeline and Person 3's model and assistant segments. Demonstrate a GitHub Actions deployment changing the running application.

3\. Write final setup and operating instructions, with exact configuration names and links to each person's component runbook. Include how to find the latest successful release.

4\. After the demo, confirm which website and API resources should remain available and coordinate idle-resource removal with Person 1. Keep deployment code and evidence.

**Done when:** A teammate can open the deployed app, explain each screen, and identify the release that produced it.

**Hand off:** Give the group the final URLs, commit, release log, screenshots if useful, and any retained-resource notes.

# Person 3 Prepare the models and assistant

You own model behavior and assistant behavior. You provide model code to Person 1 for SageMaker orchestration and payloads to Person 2 for inference. You also deliver the Python FastAPI assistant Lambda and its Bedrock resources.

## P3 01 Define intelligence inputs and starter fixtures

**When to start:** Phase 0 with P1 01 and P2 01.

1\. Review the data dictionary, gold schema, and historical dates. Choose the 24-hour forecast target, seasonal baseline, and hourly anomaly input with the team.

2\. Write initial contracts/models.md examples for feature inputs, forecast outputs, and anomaly scores. Define the high-level Lambda window response with Person 2.

3\. Agree on chat request and response fields, cited-source format, and how the weekly-report action is requested. Save representative answers as fixtures for the UI.

4\. Check the intended Region, model access, and required service combinations with Person 1. Create a small hand-built sample of the intended gold tables to support early assistant development.

**Done when:** Persons 1 and 2 can use your model and assistant fixtures before trained models or live gold tables exist.

**Hand off:** Send the contracts and fixtures to both teammates, with any service access blocker stated precisely.

## P3 02 Create the approved Athena query tools

**When to start:** Phase 1 using sample gold tables and P1 01; repeat checks on live gold after P1 08.

1\. Define a small tool list, such as consumption totals, hourly patterns, weekday-versus-weekend comparison, and sub-metering breakdown for a requested period.

2\. Implement Python functions backed by fixed, read-only, parameterized Athena query templates. Validate household, dates, allowed tables, and maximum result size.

3\. Handle Athena execution, bounded waiting or status checking, result parsing, and failed queries. Return structured values and units rather than asking Claude to interpret raw log text.

4\. Ask Person 1 to review SQL arithmetic and grants. Keep source-data writes impossible through these tools while permitting the required query-result output operations.

**Done when:** Each tool returns a known correct answer on the sample, rejects invalid arguments, and exposes no arbitrary SQL execution interface.

**Hand off:** Give Person 2 example tool-supported answers and Person 1 the assistant query role and required catalog access.

# Person 3 Establish the assistant and live data path

## P3 03 Build the assistant service and Bedrock resources

**When to start:** Phase 1 after P3 02; do not wait for model training.

1\. Create a Python FastAPI /chat implementation and Lambda package using Mangum. Use Boto3 to call Claude through Bedrock and declare the approved tool schemas.

2\. Implement the loop: send question, inspect requested tool, validate arguments, run the tool, return its result to Claude, and produce the final response. Bound repeated tool calls.

3\. Define infra/challenge4/ for the assistant Lambda, roles, configuration, Bedrock Guardrails, knowledge base, and S3 Vectors resources. Keep the public Gateway in Person 2's module.

4\. Collect a small credible guidance corpus in S3 with source titles and URLs. Configure ingestion, and document the embedding model and permissions needed for retrieval.

**Done when:** The service answers one sample data question through a tool and its Terraform resources can be reviewed and deployed.

**Hand off:** Give Person 2 the assistant Lambda ARN and schema; give Person 1 the role identifiers needed for gold grants.

## P3 04 Switch assistant tools to live Athena data

**When to start:** Phase 2 after P1 06 and P1 08 provide verified gold tables and access.

1\. Replace hand-built table locations with real catalog names and configuration. Run each tool against Person 1's published example period and expected numbers.

2\. Check that timestamp interpretation, coverage, units, and weekday versus weekend calculations match the data contract.

3\. Make Claude explain only what the results support. For a high-usage question, compare the period and available sub-metering; avoid claiming an appliance or behavior without evidence.

4\. Return answer text, selected period, and useful source metadata in the agreed JSON. Keep report inputs stubbed only until live model outputs exist.

**Done when:** A live data question produces correct numerical facts without relying on sample tables.

**Hand off:** Tell Person 2 the live service is ready for integration and provide a reproducible request and expected answer facts.

# Person 3 Build baseline features and both models

## P3 05 Prepare a fair forecasting experiment

**When to start:** Phase 2 after live gold is available and P3 04 works.

1\. Create chronological training, validation, and final held-out periods. Write their boundaries down before comparing models. Keep the held-out period for final evaluation.

2\. Implement a seasonal baseline, for example the same hour in the previous week. Use the same forecast origins, horizon, missing-data mask, and target units for model and baseline.

3\. Build lag and calendar features with one reusable Python feature builder. Document feature order and scaling or imputation; use only information available at the forecast origin.

4\. Implement MAPE and RMSE calculation and specify how near-zero actual values are handled. Inspect missing hours rather than filling all missing values with zero.

**Done when:** The baseline, splits, feature definitions, and evaluation inputs can be reproduced from the same gold snapshot or run.

**Hand off:** Give Person 1 the processing inputs and outputs and Person 2 the feature-builder interface and minimum-history rule.

## P3 06 Train forecasting and anomaly models

**When to start:** Phase 3 after the baseline and features are verified.

1\. Train the first XGBoost forecasting model. For the 24-hour horizon, choose a documented direct or recursive prediction strategy and reproduce it during evaluation and serving.

2\. Tune using the validation period, then compare against the baseline on the held-out period. Improve data treatment or features if it does not beat the baseline.

3\. Train SageMaker's built-in Random Cut Forest on hourly consumption. Record the feature inputs and define an anomaly threshold using training or validation data.

4\. Keep training, evaluation, and inference entry points as scripts, not only notebook cells. Record dependencies, parameters, input locations, and output artifacts.

**Done when:** The forecasting comparison is credible, and both models have reproducible training code and documented output meaning.

**Hand off:** Send early metrics and script interfaces to Person 1 so the SageMaker Pipeline can be completed without guessing arguments.

# Person 3 Deliver and verify production model behavior

## P3 07 Publish the evaluated model package

**When to start:** Phase 3 after P3 06, before Person 1 finishes P1 10.

1\. Create a compact evaluation report containing split dates, forecast horizon, baseline and model MAPE and RMSE, missing-value policy, and interpretation.

2\. Export the model package with processing, training, evaluation, and inference scripts plus payload fixtures. State exactly which artifact each SageMaker step reads and writes.

3\. Give Person 1 model settings, runtime dependencies, registration metadata, and evaluation output fields. Give Person 2 feature order, request types, expected outputs, and failure conditions.

4\. Request review of the evidence before model approval. A successful training job alone does not demonstrate improvement or correct serving behavior.

**Done when:** Person 1 can build the pipeline from the package and Person 2 can reproduce sample inference preparation.

**Hand off:** The handoff includes model code, artifact references, metrics, schemas, and one runnable example for each model.

## P3 08 Validate the pipeline and live serving results

**When to start:** Phase 3 with P1 09 to 10 and P2 08 to 09.

1\. Review the SageMaker Pipeline steps with Person 1. Confirm the evaluation and registration steps consume the right artifacts and preserve model versions.

2\. Check prediction and anomaly responses from the deployed endpoints against the expected input shapes. Distinguish a numeric anomaly score from the chosen flag threshold.

3\. Test Person 2's window-based Lambda over a known historical period. Ensure the feature builder, forecast origin, missing-history behavior, and multi-step strategy match evaluation.

4\. Check that published DynamoDB or S3 result records contain sufficient time and version metadata for the dashboard and weekly reports.

**Done when:** The model used by the application behaves consistently with the evaluated model, and the Lambda returns both outputs.

**Hand off:** Confirm serving acceptance to both teammates and provide a stable demo window with example forecast and anomaly results.

# Person 3 Complete advice reports and evaluation

## P3 09 Ground advice and weekly reports in evidence

**When to start:** Phase 4 after knowledge-base ingestion and live model outputs are available.

1\. Retrieve relevant guidance from the Bedrock Knowledge Base backed by S3 Vectors. Include source titles and links in the structured response and use them in the answer.

2\. Separate consumption facts from general guidance. Use Athena tools for measurements and the guidance corpus for recommendations; do not substitute retrieved advice for numeric data.

3\. Read weekly consumption, anomalies, and forecasts through the agreed Python readers or result store. Generate a narrative with totals, notable periods, and clearly identified predictions.

4\. Apply the configured Guardrails to the relevant model interactions. Check unsupported topics, missing measurements, ambiguous dates, and requests to change data.

**Done when:** Advice has valid source citations and a weekly report correctly combines all three live result types.

**Hand off:** Give Person 2 real cited responses, the weekly-report request, and examples of expected refusal and missing-data behavior.

## P3 10 Run the required assistant evaluation

**When to start:** Phase 4 after P3 09 and once Person 2 can call the real service.

1\. Create 20 evaluation questions within the brief's allowed 15 to 20 range. Include comparisons, high-usage analysis, summaries, cited advice, out-of-scope topics, and write-style requests.

2\. Define expected numbers or behaviors for every question. Ask Person 1 to verify SQL ground truth and Person 2 to verify the UI can express each request.

3\. Run against live Athena data and current model outputs. Check numerical facts with tolerances, time context, citation validity, refusal behavior, and unsupported claims.

4\. Record observed results, failures, fixes, and a rerun. Save the evaluation data and runner so the final results are reviewable rather than a collection of selected successful screenshots.

**Done when:** Every evaluation question meets its expected facts or behavior and failures have been resolved with evidence.

**Hand off:** Send Persons 1 and 2 the final evaluation report, reproducible runner, and recommended demo questions.

# Person 3 Finish verification and demonstrate intelligence

## P3 11 Validate answers through the deployed website

**When to start:** Phase 5 after P2 10 to 11 and P3 10.

1\. Run the evaluation questions through the public application path, not only direct local calls. Compare browser answers and citations with the service-level evaluation.

2\. Check a high-usage question, weekday/weekend comparison, cited saving recommendation, weekly summary, missing-data question, and refused write request.

3\. Inspect failures with the responsible owner: query numbers with Person 1, route or display issues with Person 2, and model or prompt behavior in your own code.

4\. Rerun affected cases after fixes and review required service configuration in the fresh deployment. Confirm no sample tables or mocked model outputs remain in the acceptance path.

**Done when:** The deployed user flow is supported by the same live data and evaluation evidence as the direct API tests.

**Hand off:** Give the group the final intelligence acceptance result and exact requests used in the rehearsal.

## P3 12 Own model and assistant demo evidence

**When to start:** Phase 5, then support cleanup after the demonstration.

1\. Prepare a concise explanation of baseline comparison, held-out evaluation, model versions, anomaly scores, and the Model Registry approval evidence.

2\. Demonstrate selected live questions, weekly narrative, and advice citations. Include one appropriate refusal to show that the approved tool boundary is enforced.

3\. Record the gold run, model versions, assistant configuration, and evaluation version used in the demo. Store scripts and reports in the repository.

4\. Tell Person 1 which model endpoints and assistant resources are idle after the demo. Confirm the code and required documents remain available for reconstruction.

**Done when:** You can explain where every displayed fact came from, and the group retains the model and assistant evidence after resources are removed.

**Hand off:** Give the team final evaluation files, approved artifact references, demo requests, and cleanup inputs.

# Shared acceptance checklist before the demonstration

Use this checklist together. The owner prepares the evidence; another member reproduces the check. A completed task in the issue board does not replace demonstrating the required behavior.

| **Required outcome**          | **Lead and support**                        | **Evidence to keep**                                                                                                                                     |
| ----------------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Terraform and GitHub Actions  | Person 1 infrastructure; Person 2 workflows | Remote S3 state with locking; module plans; PR fmt, validate and plan; main apply and automatic app release; OIDC without long-lived keys.               |
| Reproducible application      | Person 2 with Person 1                      | Clean-environment deployment; HTTPS URL; all four API paths; dashboard, anomaly list, forecast chart, and chat panel with real data.                     |
| Application storage and roles | Person 2 with Person 1                      | On-demand DynamoDB items and time-range reads; successful repeatable loads; least-privilege roles and managed configuration.                             |
| Bronze silver and gold        | Person 1                                    | Original CSV; bronze Parquet and metadata; cleaned typed silver Iceberg partitioned by year/month; required gold summaries; all three catalog databases. |
| Data quality and governance   | Person 1 with Person 3                      | Null/range/duplicate checks and a failure case; Lake Formation layer permissions; validated Athena totals; silver upsert and time travel.                |
| Automatic data processing     | Person 1 with Person 2                      | New CSV triggers bronze-to-gold; workflow status; successful publication and application data update; safe retry evidence.                               |
| Forecast and anomaly models   | Person 3 with Person 1                      | Forecast beats seasonal baseline on held-out dates using MAPE and RMSE; required built-in Random Cut Forest on hourly data.                              |
| SageMaker operations          | Person 1 with Person 3                      | Processing, training, evaluation, registration, and Model Registry approval; Terraform resources; Actions-triggered pipeline run.                        |
| Live model integration        | Person 2 with Persons 1 and 3               | Lambda invocation returns forecast and anomaly scores for a time window; real results visible in the app.                                                |
| Bedrock functionality         | Person 3 with Person 2                      | Claude tools run approved parameterized Athena reads; weekly narrative; Bedrock Knowledge Base uses S3 Vectors; advice cites sources.                    |
| Assistant safety and quality  | Person 3 with Person 1                      | Guardrails configured; 20 expected-answer tests against live data; out-of-scope and write requests refused; browser integration works.                   |
| Naming secrets and cost       | Each person; Person 1 coordinates           | Group prefixes and tags; Secrets Manager or SSM; small resources and spot training; endpoint and idle-resource teardown plan.                            |

# Final deployment demo and cleanup order

## Rebuild the actual system in a controlled order

Person 1 owns bootstrap and shared resources. Person 2 builds application artifacts and publishes the website and API through GitHub Actions. Load data after tables and roles exist. Person 3 supplies model scripts; Person 1 runs training, records model approval, and provisions approved endpoints; Person 2 publishes usable results. Person 3 ingests guidance and runs the assistant evaluation. Then all three verify the website.

A new model version requires the approval step specified by the brief. Routine application merges should still deploy automatically without requiring a new training run and model approval every time. Keep these two flows distinct in the workflow design.

## Run the final demonstration as one story

- Person 1 uploads the agreed raw CSV and shows the automatic pipeline, quality results, and correct gold queries. Keep the required Iceberg upsert and time-travel examples ready.
- Person 3 explains the forecasting baseline comparison, the anomaly model, and the approved model version. Person 2 invokes the Lambda and shows both returned model outputs.
- Person 2 opens the website and shows real consumption, anomalies, and forecasts for the agreed historical period.
- Person 3 asks live data questions, generates the weekly report, shows energy-saving sources, and demonstrates an appropriate refusal through the chat panel.
- Person 2 merges a small reviewed application change and shows GitHub Actions deploying the new version to the running system.

Training and full-data processing may take longer than a presentation slot. Rehearse the order and prepare logs from the same reproducible run, while still demonstrating the live behaviors required by the brief. Do not present saved screenshots as a replacement for a callable model or assistant.

## Close the work together

Person 1 removes idle infrastructure and endpoints through Terraform. Person 2 records the final release and operating instructions. Person 3 preserves model artifacts, evaluation results, and assistant test cases. All three confirm what remains running and why, and keep the repository sufficient to reconstruct the project.

## Source documents

Required scope and completion conditions: greentrack-challenges.md from the project sources. Implementation context: GreenTrack_Project_Guide_and_Plan_Python_Backend(1).docx attached to this conversation. The role split, folder names, 24-hour starting horizon, 20-question evaluation, and phase sequence are recommendations within that required scope.