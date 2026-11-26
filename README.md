# GreenTrack-Group4

GreenTrack student demo: FastAPI, React/TypeScript/Vite and Terraform.

- [Person 2 handoff and local API commands](docs/person2-handoff.md)

- [Frontend startup and tests](web/README.md)
- [Existing AWS foundation and teammate handoff](docs/foundation-handoff.md)
- [Application infrastructure, packaging and later deployment](docs/application-infrastructure.md)
- [Pull-request checks and troubleshooting](docs/pr-checks.md)
- [Deployment pipeline activation, readiness and recovery](docs/deployment-pipeline.md)
- [Data lake and bronze layer (Challenge 2)](docs/data-lake-bronze.md)
- [Silver layer: cleaned Iceberg readings (Challenge 2)](docs/data-lake-silver.md)
- [Data quality checks on silver (Challenge 2)](docs/data-lake-quality.md)
- [Gold layer: business summaries (Challenge 2)](docs/data-lake-gold.md)
- [Pipeline orchestration on upload (Challenge 2)](docs/data-lake-orchestration.md)
- [Lake Formation and Iceberg demos (Challenge 2)](docs/data-lake-lake-formation.md)
- [SageMaker pipeline skeleton (Challenge 3)](docs/sagemaker-skeleton.md)
- [Gold ready handoff package](docs/gold-handoff.md)
- [Fresh-environment deployment runbook](docs/deployment-runbook.md)
- [Person 1 resource inventory and cleanup plan](docs/resource-inventory.md)

The foundation handoff reports that the Terraform state bucket was already
applied by its owner. The user reports successfully deploying and manually
testing the mock website. Local mock mode remains the default and needs no AWS
credentials. Genuine gold consumption is not connected yet; the linked plan
records the current offline baseline and the separately authorized next stages.
Keep automatic deployment disabled during that integration: the GitHub pipeline
still explicitly selects mock and the shared Lake Formation admin configuration
needs review before activation. No new live verification was performed for this
documentation stage.
