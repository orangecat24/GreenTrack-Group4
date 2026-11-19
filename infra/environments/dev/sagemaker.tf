module "challenge3" {
  source                = "../../challenge3"
  name_prefix           = "g4-greentrack-dev"
  data_lake_bucket_name = module.challenge2.data_lake_bucket_name
}

output "sagemaker" {
  description = "SageMaker roles, registries and artifact prefixes for Person 3."
  value = {
    execution_role_arn           = module.challenge3.sagemaker_execution_role_arn
    forecast_model_package_group = module.challenge3.forecast_model_package_group
    anomaly_model_package_group  = module.challenge3.anomaly_model_package_group
    artifacts_prefix             = module.challenge3.artifacts_prefix
    scripts_prefix               = module.challenge3.scripts_prefix
  }
}
