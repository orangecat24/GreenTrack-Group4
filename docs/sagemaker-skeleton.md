# SageMaker pipeline skeleton (Person 1, task P1 09)

This is the infrastructure skeleton that receives Person 3's model package.
Nothing here is an active training job: it provisions the identity and
registries so an `aws sagemaker start-pipeline-execution` from Person 3's
code can run without further permission work.

## What this module adds

| Resource | Name | Purpose |
| --- | --- | --- |
| IAM role | `g4-greentrack-dev-sagemaker-execution` | Role every SageMaker processing, training and inference job runs as |
| IAM policy | inline `sagemaker-data-lake` | Read gold + `ml/scripts/`; write only `ml/` |
| Managed policy | `AmazonSageMakerFullAccess` | Lets the role create jobs, read logs, use built-in images |
| Model Package Group | `g4-greentrack-dev-forecast` | Registry for XGBoost 24-hour forecasting versions |
| Model Package Group | `g4-greentrack-dev-anomaly` | Registry for Random Cut Forest versions |

S3 layout the role is allowed to use, under the existing data lake bucket:

```
gold/                     read
ml/scripts/<file>.py      read   (Person 3 publishes processing/training scripts here)
ml/artifacts/             write  (outputs of each pipeline run)
ml/reports/               write  (evaluation reports surfaced to the approval step)
```

## Handoff to Person 3

Give Person 3 the Terraform outputs:

```
module.challenge3.sagemaker_execution_role_arn
module.challenge3.forecast_model_package_group
module.challenge3.anomaly_model_package_group
module.challenge3.scripts_prefix
module.challenge3.artifacts_prefix
```

Person 3's P3 07 model package should include processing, training,
evaluation and inference entry points plus payload fixtures. When that lands,
P1 10 proceeds as follows:

1. Copy [ml/pipeline.json.example](../ml/pipeline.json.example) to
   `ml/pipeline.json` and set Person 3's script filenames, hyperparameters
   and their chosen training/inference images.
2. Upload Person 3's entry points under
   `s3://g4-greentrack-dev-datalake-886565871385/ml/scripts/`.
3. Generate the pipeline JSON Terraform will manage:
   `python scripts/build_pipeline_definition.py --config ml/pipeline.json --output infra/challenge3/pipeline_definition.json`.
4. Add `aws_sagemaker_pipeline` to [infra/challenge3](../infra/challenge3),
   sourcing the JSON above. Terraform remains the single source of
   infrastructure truth.
5. After the pipeline runs and a registered model version is approved in
   the Model Registry, add `aws_sagemaker_model`,
   `aws_sagemaker_endpoint_configuration` and `aws_sagemaker_endpoint` for
   each approved package, and publish the serving-ready handoff.

The helper script and example config are committed now so the model-package
arrival is a straight drop-in. The actual pipeline and endpoint resources
are intentionally deferred: their values depend on Person 3's chosen images,
container entry points and payload shapes, which would be guesses today.

## Status (2026-11-19)

Applied in `886565871385/eu-central-1`:

- `arn:aws:iam::886565871385:role/g4-greentrack-dev-sagemaker-execution`
- Model Package Groups `g4-greentrack-dev-forecast`, `g4-greentrack-dev-anomaly`

No training job, model package or endpoint exists yet; those arrive with
P1 10 once Person 3 delivers the model package.
