# GreenTrack-Group4

GreenTrack student demo: FastAPI, React/TypeScript/Vite and Terraform.

- [Person 2 handoff and local API commands](docs/person2-handoff.md)
- Person 3 P3 01 drafts and review handoff
  - [Model and inference contracts](contracts/models.md)
  - [Assistant and weekly-summary contract](contracts/assistant.md)
  - [Synthetic fixtures, offline checks, and teammate review](fixtures/person3/README.md)
- [Person 3 P3 02 query tools and teammate handoff](assistant/README.md)
- [Person 3 P3 03 standalone assistant, Lambda, and teammate handoff](docs/person3-handoff.md)
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
applied by its owner. Person 2's application is prepared for deployment; local
mock mode remains the default and does not require AWS credentials.
The GitHub deployment pipeline is prepared but requires explicit repository
activation; no deployment was run from the implementation session.
