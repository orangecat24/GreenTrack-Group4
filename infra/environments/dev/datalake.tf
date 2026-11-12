# Challenge 2 data lake (Person 1). Reuses this root's backend and guarded
# provider; the child module has no backend of its own. The Glue job script
# lives in the repository and is uploaded to S3 by Terraform, so a deployment
# never depends on files from someone's laptop.
module "challenge2" {
  source                  = "../../challenge2"
  name_prefix             = "g4-greentrack-dev"
  bronze_job_script_path  = abspath("${path.module}/../../../data/glue/bronze_job.py")
  silver_job_script_path  = abspath("${path.module}/../../../data/glue/silver_job.py")
  quality_job_script_path = abspath("${path.module}/../../../data/glue/quality_job.py")
  quality_ruleset_path    = abspath("${path.module}/../../../data/quality/silver_readings.dqdl")
}

output "data_lake" {
  description = "Data lake locations and names for teammates (upload target, catalog, Athena results)."
  value = {
    bucket_name            = module.challenge2.data_lake_bucket_name
    raw_upload_uri         = module.challenge2.raw_upload_uri
    athena_results_uri     = module.challenge2.athena_results_uri
    bronze_database_name   = module.challenge2.bronze_database_name
    bronze_table_name      = module.challenge2.bronze_table_name
    bronze_job_name        = module.challenge2.bronze_job_name
    silver_database_name   = module.challenge2.silver_database_name
    silver_table_name      = module.challenge2.silver_table_name
    silver_job_name        = module.challenge2.silver_job_name
    quality_job_name       = module.challenge2.quality_job_name
    quality_results_uri    = module.challenge2.quality_results_uri
    glue_pipeline_role_arn = module.challenge2.glue_pipeline_role_arn
  }
}
