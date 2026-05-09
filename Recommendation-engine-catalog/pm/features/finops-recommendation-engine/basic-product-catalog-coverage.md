# Basic Recommendation Engine - Product Catalog Coverage and Browse View

The Basic engine uses Product Catalog pricing to calculate savings, compare source and target SKUs, and defend estimates during approval. Current extracted catalog output lives in `data/csp_catalog/output/`.

## Provider totals

| Provider | Resource types with output | Regions with output | Output files | Catalog entries |
|---|---:|---:|---:|---:|
| AWS | 24 | 32 | 751 | 189,570 |
| AZURE | 25 | 50 | 1250 | 137,901 |
| GCP | 1 | 1 | 1 | 0 |

## Resource-type coverage

| Provider | Resource type | Service family | Service names | Regions | Files | Entries |
|---|---|---|---|---:|---:|---:|
| AWS | `aws_api_gateway` | Integration | Amazon API Gateway | 32 | 32 | 445 |
| AWS | `aws_cloudfront` | Networking | Amazon CloudFront | 15 | 15 | 43 |
| AWS | `aws_cloudwatch` | Monitoring | Amazon CloudWatch | 32 | 32 | 1,638 |
| AWS | `aws_dynamodb` | Databases | Amazon DynamoDB | 32 | 32 | 160 |
| AWS | `aws_ebs` | Storage | Amazon EBS | 32 | 32 | 224 |
| AWS | `aws_ec2` | Compute | Amazon EC2 | 32 | 32 | 64,685 |
| AWS | `aws_efs` | Storage | Amazon EFS | 32 | 32 | 332 |
| AWS | `aws_eks` | Compute | Amazon EKS | 32 | 32 | 224 |
| AWS | `aws_elasticache` | Databases | Amazon ElastiCache | 32 | 32 | 5,270 |
| AWS | `aws_emr` | Analytics | Amazon EMR | 32 | 32 | 14,614 |
| AWS | `aws_fargate` | Compute | AWS Fargate | 32 | 32 | 128 |
| AWS | `aws_kinesis` | Streaming | Amazon Kinesis | 32 | 32 | 512 |
| AWS | `aws_lambda` | Compute | AWS Lambda | 32 | 32 | 64 |
| AWS | `aws_msk` | Streaming | Amazon MSK | 32 | 32 | 1,134 |
| AWS | `aws_nat_gateway` | Networking | NAT Gateway | 32 | 32 | 139 |
| AWS | `aws_opensearch` | Databases | Amazon OpenSearch Service | 32 | 32 | 4,814 |
| AWS | `aws_rds` | Databases | Amazon RDS | 32 | 32 | 59,524 |
| AWS | `aws_redshift` | Data Warehouse | Amazon Redshift | 32 | 32 | 691 |
| AWS | `aws_route53` | Networking | Amazon Route 53 | 32 | 32 | 283 |
| AWS | `aws_s3` | Storage | Amazon S3 | 32 | 32 | 224 |
| AWS | `aws_sagemaker` | Machine Learning | Amazon SageMaker | 32 | 32 | 33,524 |
| AWS | `aws_sns` | Messaging | Amazon SNS | 32 | 32 | 802 |
| AWS | `aws_sqs` | Messaging | Amazon SQS | 32 | 32 | 96 |
| AWS | `aws_vpn` | - | - | 32 | 32 | 0 |
| AZURE | `azure_aks` | Compute | Azure Kubernetes Service | 50 | 50 | 344 |
| AZURE | `azure_api_management` | Developer Tools | API Management | 50 | 50 | 1,044 |
| AZURE | `azure_app_gateway` | Networking | Application Gateway | 50 | 50 | 911 |
| AZURE | `azure_app_service` | Compute | Azure App Service | 50 | 50 | 2,482 |
| AZURE | `azure_blob_storage` | Storage | Storage | 50 | 50 | 3,087 |
| AZURE | `azure_container_instances` | Containers | Container Instances | 50 | 50 | 537 |
| AZURE | `azure_container_registry` | Containers | Container Registry | 50 | 50 | 135 |
| AZURE | `azure_cosmos_db` | Databases | Azure Cosmos DB | 50 | 50 | 2,937 |
| AZURE | `azure_data_factory` | Analytics | Azure Data Factory v2 | 50 | 50 | 1,163 |
| AZURE | `azure_databricks` | Analytics | Azure Databricks | 50 | 50 | 591 |
| AZURE | `azure_event_hubs` | Internet of Things | Event Hubs | 50 | 50 | 373 |
| AZURE | `azure_expressroute` | Networking | ExpressRoute | 50 | 50 | 35 |
| AZURE | `azure_firewall` | Networking | Azure Firewall | 50 | 50 | 96 |
| AZURE | `azure_functions` | Compute | Functions | 50 | 50 | 332 |
| AZURE | `azure_logic_apps` | Integration | Logic Apps | 50 | 50 | 531 |
| AZURE | `azure_managed_disks` | Storage | Storage | 50 | 50 | 3,310 |
| AZURE | `azure_monitor` | Management and Governance | Log Analytics | 50 | 50 | 156 |
| AZURE | `azure_mysql` | Databases | Azure Database for MySQL | 50 | 50 | 1,566 |
| AZURE | `azure_postgresql` | Databases | Azure Database for PostgreSQL | 50 | 50 | 3,787 |
| AZURE | `azure_redis` | Databases | Redis Cache | 50 | 50 | 3,642 |
| AZURE | `azure_service_bus` | Integration | Service Bus | 50 | 50 | 203 |
| AZURE | `azure_sql_db` | Databases | SQL Database | 50 | 50 | 891 |
| AZURE | `azure_synapse` | Analytics | Azure Synapse Analytics | 50 | 50 | 1,625 |
| AZURE | `azure_vm` | Compute | Virtual Machines | 50 | 50 | 108,006 |
| AZURE | `azure_vpn_gateway` | Networking | VPN Gateway | 50 | 50 | 117 |
| GCP | `gcp_compute` | - | - | 1 | 1 | 0 |

## Coverage notes

- Azure is broadly populated across 50 regions and many compute, storage, database, networking, analytics, integration, monitoring, and container services.
- AWS is broadly populated across 32 regions, including EC2, RDS, EBS, S3, EFS, Lambda, EKS, Fargate, NAT, CloudFront, Route 53, Redshift, EMR, Kinesis, MSK, SageMaker, CloudWatch, SQS, SNS, and API Gateway. `aws_vpn` currently has zero entries and needs builder validation.
- GCP config/builders exist for 17 resource types across 43 regions, but current output is not populated beyond a zero-entry `gcp_compute` file; the GCP pricing build requires API key setup and validation.
- AI/ML catalog expansion must add Bedrock, Azure OpenAI, Vertex/Gemini, vector DB, and LLM gateway pricing where available.

## Required Product Catalog review view

Filters: provider, category, sub-category, region, SKU/meter search, pricing model, OS/license, technical specs, recommendation eligibility, and freshness.

Required actions: compare source/target SKU, show effective rate snapshot, export pricing evidence, show stale-rate warnings, and show which recommendation definitions are blocked by missing pricing data.

## Compatibility groups

Every Product Catalog product type and every movement-capable recommendation must carry a compatibility group. The Basic engine can recommend movement only when the source and target share the same group. Cross-group movement is treated as migration work and is not auto-configured in Basic.

The group definitions are maintained in `basic-product-compatibility-groups.md`. Examples:

- VM movement: `compute.vm.same-architecture-family`.
- GPU movement: `compute.gpu.same-accelerator-architecture`.
- Block volume movement: `storage.block.same-volume-performance-family`.
- Object tier movement: `storage.object.same-bucket-storage-class-policy`.
- Managed database movement: `data.managed-service.same-engine-edition-and-ha-model`.
- AI model routing: `ai.model.same-modality-context-window-and-slo-tier`.

## Acceptance criteria

- Product Catalog view supports provider/category/subcategory/region/search filters.
- Product Catalog view supports product type and compatibility group filters.
- Step 5/6 of authoring can open the same compare drawer.
- Every savings estimate references an immutable pricing snapshot ID.
- Rates older than seven days show stale warnings.
- Coverage page lists recommendation definitions blocked by missing Product Catalog data.
- Source-to-target candidates outside the same compatibility group are blocked or labelled as migration work.
