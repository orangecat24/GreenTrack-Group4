# GreenTrack Challenges

**Project:** GreenTrack, Energy Consumption Analytics & Forecasting
**Dataset:** UCI Individual Household Electric Power Consumption (about 2M rows at 1-minute resolution, Dec 2006 to Nov 2010, semicolon-separated, missing values encoded as `?`)

GreenTrack analyzes electricity consumption to identify usage patterns, detect unusual spikes, and forecast future energy demand.

Every group builds the complete GreenTrack solution and completes all four challenges. Each group works independently in its own repository and its own set of AWS resources.


## Ground rules

- **AWS account:** DataMax provides the AWS account. Use it only for this project.
- **Infrastructure as code:** all AWS resources are defined in **Terraform**. No console-only changes, and no CDK or CloudFormation. Use remote state (S3 backend with locking) and split the code into modules per challenge.
- **CI/CD:** **GitHub Actions** for everything: `terraform fmt`, `validate`, `plan` on pull requests, `apply` on merge to `main`, plus build and deploy of the application. Authenticate to AWS from GitHub Actions with OIDC and an IAM role, with no long-lived access keys.
- **Repository:** one GitHub repository per group, with pull requests and at least one reviewer from the group on each merge.
- **Naming and cost:** prefix and tag every resource with the group name (for example `g1-greentrack-...`). Use small instance sizes, spot training, and delete SageMaker endpoints and other idle resources after demos.
- **Secrets:** use Secrets Manager or SSM Parameter Store. Never commit credentials.

## Suggested order

Challenge 2 produces the data that Challenges 3 and 4 consume, and Challenge 1 displays all results. Split the work inside your group so you can run in parallel: start Challenge 1 with mock data and Challenge 4 with a hand-built sample of the gold tables while Challenge 2 is in progress.

1. Challenge 2: data pipeline, bronze to gold (foundation for everything else)
2. Challenge 3: SageMaker models
3. Challenge 4: Bedrock assistant
4. Challenge 1: application (starts early with mock data, finishes last by integrating the other three)

---

## Challenge 1: Deploy the application

**Goal:** a working three-tier application in AWS, reachable over HTTPS and fully deployed through Terraform and GitHub Actions.

**What to build**
- **Frontend:** a React or Vue single-page app hosted on S3 + CloudFront (or Amplify Hosting). Pages: consumption dashboard, anomaly list, forecast chart, and a chat panel for the Bedrock assistant.
- **Backend:** a REST API on Lambda + API Gateway, or a container on ECS Fargate behind an ALB. Endpoints: `/consumption`, `/anomalies`, `/forecast`, `/chat`.
- **Database:** DynamoDB (on-demand capacity) for aggregated readings, anomaly records, and forecast results. Design the tables around the API access patterns (for example partition key by meter or household, sort key by timestamp), and load them from the gold tables.
- **Platform:** least-privilege IAM roles for the backend, Secrets Manager or SSM Parameter Store for configuration and secrets, and a VPC only if the backend runs on ECS Fargate.
- **CI/CD:** a GitHub Actions workflow that builds the frontend and backend, runs tests, and deploys on merge to `main`.

**Integration**
Begin with seeded mock data. Once Challenges 2 to 4 produce real outputs, switch the API to read them.

**Done when**
- A fresh `terraform apply` in an empty environment produces a working app.
- A push to `main` deploys a new version without manual steps.
- The dashboard shows real aggregated data, forecasts, and anomalies.

---

## Challenge 2: Data pipeline with Glue and a lakehouse (bronze, silver, gold)

**Goal:** a repeatable, scheduled medallion pipeline that turns the raw CSV into query-ready lakehouse tables.

**What to build**
- **Bronze (raw):** the CSV exactly as received, stored in S3 and converted to Parquet with no business transformations. Add ingestion metadata (source file name, load timestamp) so every row is traceable.
- **Silver (cleaned):** a Glue ETL job (PySpark) that combines date and time into one timestamp, converts `?` to nulls, casts types, removes duplicate timestamps, and writes Apache Iceberg tables partitioned by year and month. Glue Data Quality rules run at this layer (null rate, value ranges, duplicate timestamps).
- **Gold (business-ready):** hourly and daily consumption, peak-hour statistics, and a sub-metering breakdown (kitchen, laundry, water heater and AC). Gold tables are the input for the models, the Bedrock assistant, and the application.
- **Catalog and querying:** all three layers registered in the Glue Data Catalog as separate databases (`bronze`, `silver`, `gold`) and queried with Athena. Demonstrate one time-travel query and one incremental upsert on a silver table.
- **Governance:** Lake Formation permissions per layer, for example write access to bronze and silver only for the pipeline role, and read access to gold for the application, SageMaker, and Bedrock roles.
- **Orchestration:** a Glue Workflow or Step Functions state machine (bronze to silver to gold), triggered by EventBridge Scheduler or by a new file landing in bronze.

**Done when**
- Dropping a new CSV into the bronze bucket triggers the pipeline end to end.
- Athena returns correct hourly and daily aggregates from the gold tables.
- Data quality rules run on silver and report failures.

---

## Challenge 3: Train and deploy models with SageMaker

**Goal:** one forecasting model and one anomaly detection model, both deployed and callable.

**What to build**
- **Forecasting model:** predict demand for the next 24 hours or next 7 days. Candidates are DeepAR, or XGBoost/LightGBM on lag and calendar features. Compare against a naive seasonal baseline using MAPE and RMSE.
- **Anomaly detection model:** Random Cut Forest (built-in algorithm) on hourly consumption to flag spikes.
- **MLOps:** a SageMaker Pipeline covering processing, training, evaluation, and registration, with a Model Registry approval step. Training data comes from the gold tables of Challenge 2.
- **Deployment:** a real-time or serverless inference endpoint, invoked from a Lambda function. Optional: a scheduled Batch Transform job (EventBridge) that writes forecasts back to S3.
- **Automation:** the endpoint, pipeline definition, and IAM roles are created with Terraform. A GitHub Actions workflow triggers the pipeline run.
- **Cost control:** spot training, small instance types, and endpoint teardown after demos.

**Done when**
- The forecasting model beats the baseline on a held-out period.
- A Lambda call returns both a forecast and anomaly scores for a given time window.

---

## Challenge 4: GenAI feature with Amazon Bedrock

**Goal:** a natural-language assistant on top of the consumption data.

**What to build**
- **Text-to-insight:** users ask questions such as "Why was usage high last Tuesday evening?" or "Compare my weekday and weekend consumption." A Bedrock model (Claude) uses tool calling to run parameterized Athena queries through a Lambda function and answers from the results.
- **Narrative reports:** a generated weekly summary of consumption, detected anomalies, and the forecast.
- **Energy-saving advice:** a Bedrock Knowledge Base using Amazon S3 Vectors as the vector store, holding a small corpus of energy efficiency guidance, so recommendations cite their sources.
- **Safety and quality:** Bedrock Guardrails, a SQL tool limited to read-only allowlisted queries, and an evaluation set of 15 to 20 questions with expected answers.
- **Packaging:** an API endpoint (Lambda + API Gateway) that the frontend from Challenge 1 uses as its chat panel. Bedrock AgentCore is an optional stretch for the agent runtime.

**Done when**
- The assistant answers the evaluation questions correctly from live Athena data.
- It refuses out-of-scope and write-style requests.
- It is callable from the GreenTrack frontend.

---

## Final demo

Each group presents the full flow: raw CSV lands in bronze, the pipeline produces silver and gold, models produce forecasts and anomaly scores, the app displays them, and the Bedrock assistant answers questions about the data. Each group also shows its GitHub Actions pipeline deploying a change to the running system.
