"""Generate the SageMaker Pipeline definition JSON Terraform will manage.

Reads a small YAML-free config (JSON) that Person 3 ships alongside their
scripts, resolves the data lake prefixes from the Terraform outputs, and
writes a pipeline definition JSON file that Person 1 commits so
`aws_sagemaker_pipeline.pipeline` treats Terraform as the single source of
infrastructure truth.

Inputs expected in the config file, defaulting to the values Person 1
already provisions in infra/challenge3:

    {
      "pipeline_name": "g4-greentrack-dev-models",
      "role_arn": "arn:aws:iam::886565871385:role/g4-greentrack-dev-sagemaker-execution",
      "artifacts_prefix": "s3://g4-greentrack-dev-datalake-886565871385/ml/",
      "scripts_prefix":   "s3://g4-greentrack-dev-datalake-886565871385/ml/scripts/",
      "forecast_model_package_group": "g4-greentrack-dev-forecast",
      "anomaly_model_package_group":  "g4-greentrack-dev-anomaly",
      "steps": {
        "processing": {"script": "processing.py",         "instance": "ml.m5.large"},
        "forecast_training":   {"script": "train_forecast.py", "instance": "ml.m5.large"},
        "anomaly_training":    {"script": "train_anomaly.py",  "instance": "ml.m5.large"},
        "evaluation":          {"script": "evaluate.py",       "instance": "ml.m5.large"}
      }
    }

Usage:
    python scripts/build_pipeline_definition.py \
        --config ml/pipeline.json \
        --output infra/challenge3/pipeline_definition.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def step_arguments(prefix: str, name: str) -> list[str]:
    return [
        "--input-gold", f"{prefix}gold/",
        "--output-artifacts", f"{prefix}ml/artifacts/{name}/",
    ]


def processing_step(config: dict) -> dict:
    script = config["steps"]["processing"]["script"]
    return {
        "Name": "ProcessGold",
        "Type": "Processing",
        "Arguments": {
            "RoleArn": config["role_arn"],
            "AppSpecification": {
                "ImageUri": "683313688378.dkr.ecr.eu-central-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
                "ContainerEntrypoint": [
                    "python3", f"/opt/ml/processing/input/code/{script}"
                ],
            },
            "ProcessingInputs": [
                {
                    "InputName": "code",
                    "S3Input": {
                        "S3Uri": config["scripts_prefix"],
                        "LocalPath": "/opt/ml/processing/input/code",
                        "S3DataType": "S3Prefix",
                        "S3InputMode": "File",
                    },
                }
            ],
            "ProcessingOutputConfig": {
                "Outputs": [
                    {
                        "OutputName": "splits",
                        "S3Output": {
                            "S3Uri": f"{config['artifacts_prefix']}processing/",
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob",
                        },
                    }
                ]
            },
            "ProcessingResources": {
                "ClusterConfig": {
                    "InstanceCount": 1,
                    "InstanceType": config["steps"]["processing"]["instance"],
                    "VolumeSizeInGB": 20,
                }
            },
        },
    }


def training_step(config: dict, key: str, step_name: str, hyperparameters: dict) -> dict:
    step = config["steps"][key]
    return {
        "Name": step_name,
        "Type": "Training",
        "DependsOn": ["ProcessGold"],
        "Arguments": {
            "RoleArn": config["role_arn"],
            "AlgorithmSpecification": {
                "TrainingImage": step.get(
                    "image",
                    "492215442770.dkr.ecr.eu-central-1.amazonaws.com/sagemaker-xgboost:1.7-1",
                ),
                "TrainingInputMode": "File",
            },
            "InputDataConfig": [
                {
                    "ChannelName": "train",
                    "DataSource": {
                        "S3DataSource": {
                            "S3Uri": f"{config['artifacts_prefix']}processing/train/",
                            "S3DataType": "S3Prefix",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                }
            ],
            "OutputDataConfig": {
                "S3OutputPath": f"{config['artifacts_prefix']}{key}/",
            },
            "ResourceConfig": {
                "InstanceType": step["instance"],
                "InstanceCount": 1,
                "VolumeSizeInGB": 20,
            },
            "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
            "HyperParameters": hyperparameters,
        },
    }


def register_step(config: dict, source_step: str, package_group: str, name: str) -> dict:
    return {
        "Name": name,
        "Type": "RegisterModel",
        "DependsOn": [source_step],
        "Arguments": {
            "ModelPackageGroupName": package_group,
            "ModelApprovalStatus": "PendingManualApproval",
            "InferenceSpecification": {
                "Containers": [
                    {
                        "Image": "placeholder-inference-image",
                        "ModelDataUrl": {"Get": f"Steps.{source_step}.ModelArtifacts.S3ModelArtifacts"},
                    }
                ],
                "SupportedContentTypes": ["application/json"],
                "SupportedResponseMIMETypes": ["application/json"],
            },
        },
    }


def build(config: dict) -> dict:
    return {
        "Version": "2020-12-01",
        "Metadata": {},
        "Parameters": [
            {"Name": "ApprovalStatus", "Type": "String", "DefaultValue": "PendingManualApproval"}
        ],
        "PipelineExperimentConfig": {
            "ExperimentName": config["pipeline_name"],
            "TrialName": config["pipeline_name"],
        },
        "Steps": [
            processing_step(config),
            training_step(
                config,
                "forecast_training",
                "TrainForecast",
                config["steps"]["forecast_training"].get("hyperparameters", {}),
            ),
            training_step(
                config,
                "anomaly_training",
                "TrainAnomaly",
                config["steps"]["anomaly_training"].get("hyperparameters", {}),
            ),
            register_step(config, "TrainForecast", config["forecast_model_package_group"], "RegisterForecast"),
            register_step(config, "TrainAnomaly", config["anomaly_model_package_group"], "RegisterAnomaly"),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    definition = build(config)
    args.output.write_text(json.dumps(definition, indent=2), encoding="utf-8")
    print(f"Wrote pipeline definition with {len(definition['Steps'])} steps to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
