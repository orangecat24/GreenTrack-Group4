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

The foundation handoff reports that the Terraform state bucket was already
applied by its owner. Person 2's application is prepared for deployment; local
mock mode remains the default and does not require AWS credentials.
The GitHub deployment pipeline is prepared but requires explicit repository
activation; no deployment was run from the implementation session.
