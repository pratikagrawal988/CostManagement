"""
Seed ProductCategory and AIServiceClassification tables with AWS mappings.

Run once on startup to populate reference data for FOCUS transformation.
"""

from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import ProductCategory, AIServiceClassification, new_id, utcnow


def seed_aws_product_categories(db: Session, tenant_id: str = "tenant-demo") -> int:
    """Seed AWS service-to-category mappings."""

    categories = [
        # Compute
        ("AWS", "EC2", "^(BoxUsage|DataTransfer|ElasticIP|NAT)", "Compute", "EC2", "hour"),
        ("AWS", "Lambda", ".*Lambda.*", "Compute", "Lambda", "calls"),
        ("AWS", "ECS", ".*ECS.*", "Compute", "ECS", "hour"),
        ("AWS", "EKS", ".*EKS.*", "Compute", "EKS", "hour"),

        # Storage
        ("AWS", "S3", "^(TimedStorage|DataTransfer|Requests-S3)", "Storage", "S3", "gb_month"),
        ("AWS", "EBS", ".*EBS.*", "Storage", "EBS", "gb_month"),
        ("AWS", "Glacier", ".*Glacier.*", "Storage", "Glacier", "gb_month"),

        # Database
        ("AWS", "RDS", "^(APN1|Aurora)", "Database", "RDS", "hour"),
        ("AWS", "DynamoDB", ".*DynamoDB.*", "Database", "DynamoDB", "requests"),
        ("AWS", "Redshift", ".*Redshift.*", "Database", "Redshift", "hour"),

        # Networking
        ("AWS", "CloudFront", ".*CloudFront.*", "Networking", "CloudFront", "gb_transfer"),
        ("AWS", "VPC", ".*NatGateway.*", "Networking", "NAT", "gb_transfer"),
        ("AWS", "Route53", ".*Route53.*", "Networking", "Route53", "requests"),

        # AI/ML
        ("AWS", "Bedrock", ".*Bedrock.*", "AI/ML", "Bedrock", "tokens"),
        ("AWS", "SageMaker", ".*SageMaker.*", "AI/ML", "SageMaker", "hour"),
        ("AWS", "Rekognition", ".*Rekognition.*", "AI/ML", "Rekognition", "requests"),
    ]

    count = 0
    for provider, service, sku_pattern, category, subcategory, unit_type in categories:
        existing = db.query(ProductCategory).filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.provider == provider,
            ProductCategory.service_name == service,
            ProductCategory.sku_pattern == sku_pattern,
        ).one_or_none()

        if not existing:
            mapping = ProductCategory(
                id=new_id(),
                tenant_id=tenant_id,
                provider=provider,
                service_name=service,
                sku_pattern=sku_pattern,
                category=category,
                subcategory=subcategory,
                unit_type=unit_type,
                created_at=utcnow(),
            )
            db.add(mapping)
            count += 1

    db.commit()
    return count


def seed_ai_service_classifications(db: Session, tenant_id: str = "tenant-demo") -> int:
    """Seed AI service SKU-to-model mappings for cost allocation."""

    classifications = [
        # Bedrock - Claude
        ("AWS", "Bedrock", "claude-3.*input.*", "LLM", "Claude", "3-Sonnet", "tokens", "input_tokens"),
        ("AWS", "Bedrock", "claude-3.*output.*", "LLM", "Claude", "3-Sonnet", "tokens", "output_tokens"),
        ("AWS", "Bedrock", "claude-3-opus.*input.*", "LLM", "Claude", "3-Opus", "tokens", "input_tokens"),
        ("AWS", "Bedrock", "claude-3-opus.*output.*", "LLM", "Claude", "3-Opus", "tokens", "output_tokens"),

        # Bedrock - Llama
        ("AWS", "Bedrock", "llama2.*input.*", "LLM", "Llama", "2", "tokens", "input_tokens"),
        ("AWS", "Bedrock", "llama2.*output.*", "LLM", "Llama", "2", "tokens", "output_tokens"),

        # Bedrock - Mistral
        ("AWS", "Bedrock", "mistral.*input.*", "LLM", "Mistral", "7B", "tokens", "input_tokens"),
        ("AWS", "Bedrock", "mistral.*output.*", "LLM", "Mistral", "7B", "tokens", "output_tokens"),

        # Bedrock - Vision
        ("AWS", "Bedrock", ".*vision.*input.*", "Vision", "Claude", "3-Sonnet", "tokens", "input_tokens"),
        ("AWS", "Bedrock", ".*vision.*output.*", "Vision", "Claude", "3-Sonnet", "tokens", "output_tokens"),

        # Bedrock - Embeddings
        ("AWS", "Bedrock", ".*embedding.*", "Embeddings", "Titan", "Text", "tokens", "per_request"),

        # SageMaker
        ("AWS", "SageMaker", ".*ml\\..*instance.*", "Compute", "SageMaker", "Instance", "hour", "per_instance"),

        # Rekognition
        ("AWS", "Rekognition", ".*DetectLabels.*", "Vision", "Rekognition", "DetectLabels", "requests", "per_request"),
        ("AWS", "Rekognition", ".*DetectFaces.*", "Vision", "Rekognition", "DetectFaces", "requests", "per_request"),
    ]

    count = 0
    # NOTE: AIServiceClassification's real unique constraint is
    # (tenant_id, provider, service, sku_pattern) — it has no ai_subtype/
    # model_variant/usage_unit/tier/cost_allocation_group columns. Map the
    # tuple's positions onto the columns that do exist: ai_subtype -> ai_vendor,
    # variant -> ai_model, usage_unit -> cost_unit, tier -> token_type.
    for provider, service, sku_pattern, ai_type, ai_subtype, variant, usage_unit, tier in classifications:
        existing = db.query(AIServiceClassification).filter(
            AIServiceClassification.tenant_id == tenant_id,
            AIServiceClassification.provider == provider,
            AIServiceClassification.service == service,
            AIServiceClassification.sku_pattern == sku_pattern,
        ).one_or_none()

        if not existing:
            classification = AIServiceClassification(
                id=new_id(),
                tenant_id=tenant_id,
                provider=provider,
                service=service,
                sku_pattern=sku_pattern,
                ai_type=ai_type,
                ai_vendor=ai_subtype,
                ai_model=variant,
                cost_unit=usage_unit,
                token_type=tier,
                created_at=utcnow(),
            )
            db.add(classification)
            count += 1

    db.commit()
    return count


def seed_azure_product_categories(db: Session, tenant_id: str = "tenant-demo") -> int:
    """Seed Azure service-to-category mappings."""

    categories = [
        # Compute
        ("AZURE", "Virtual Machines", "^(Virtual Machines|VM)", "Compute", "VM", "hour"),
        ("AZURE", "App Service", ".*App Service.*", "Compute", "App Service", "hour"),
        ("AZURE", "Container Instances", ".*Container Instances.*", "Compute", "ACI", "second"),
        ("AZURE", "Azure Kubernetes Service", ".*AKS.*", "Compute", "AKS", "hour"),
        ("AZURE", "Azure Functions", ".*Functions.*", "Compute", "Functions", "calls"),
        ("AZURE", "Batch", ".*Batch.*", "Compute", "Batch", "core_hour"),

        # Storage
        ("AZURE", "Storage", "^(Storage|Blob|File Share|Queue|Table)", "Storage", "Storage", "gb_month"),
        ("AZURE", "Managed Disks", ".*Managed Disks.*", "Storage", "Managed Disks", "gb_month"),
        ("AZURE", "Archive Storage", ".*Archive.*", "Storage", "Archive", "gb_month"),

        # Database
        ("AZURE", "SQL Database", ".*SQL Database.*", "Database", "SQL", "hour"),
        ("AZURE", "Cosmos DB", ".*Cosmos DB.*", "Database", "Cosmos DB", "requests"),
        ("AZURE", "Database for MySQL", ".*MySQL.*", "Database", "MySQL", "hour"),
        ("AZURE", "Database for PostgreSQL", ".*PostgreSQL.*", "Database", "PostgreSQL", "hour"),
        ("AZURE", "Redis Cache", ".*Redis.*", "Database", "Redis", "hour"),

        # Networking
        ("AZURE", "VPN Gateway", ".*VPN Gateway.*", "Networking", "VPN", "hour"),
        ("AZURE", "Application Gateway", ".*Application Gateway.*", "Networking", "App GW", "hour"),
        ("AZURE", "Load Balancer", ".*Load Balancer.*", "Networking", "LB", "hour"),
        ("AZURE", "Bandwidth", ".*Bandwidth.*", "Networking", "Bandwidth", "gb_transfer"),
        ("AZURE", "ExpressRoute", ".*ExpressRoute.*", "Networking", "ExpressRoute", "hour"),

        # AI/ML
        ("AZURE", "Cognitive Services", ".*Cognitive Services.*", "AI/ML", "Cognitive", "requests"),
        ("AZURE", "Machine Learning", ".*Machine Learning.*", "AI/ML", "ML", "hour"),
        ("AZURE", "Text Analytics", ".*Text Analytics.*", "AI/ML", "Text Analytics", "requests"),
        ("AZURE", "Language", ".*Language.*", "AI/ML", "Language", "requests"),
        ("AZURE", "Vision", ".*Vision.*", "AI/ML", "Vision", "requests"),
    ]

    count = 0
    for provider, service, sku_pattern, category, subcategory, unit_type in categories:
        existing = db.query(ProductCategory).filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.provider == provider,
            ProductCategory.service_name == service,
            ProductCategory.sku_pattern == sku_pattern,
        ).one_or_none()

        if not existing:
            mapping = ProductCategory(
                id=new_id(),
                tenant_id=tenant_id,
                provider=provider,
                service_name=service,
                sku_pattern=sku_pattern,
                category=category,
                subcategory=subcategory,
                unit_type=unit_type,
                created_at=utcnow(),
            )
            db.add(mapping)
            count += 1

    db.commit()
    return count


def seed_azure_ai_classifications(db: Session, tenant_id: str = "tenant-demo") -> int:
    """Seed Azure AI service mappings."""

    classifications = [
        # Cognitive Services - Language
        ("AZURE", "Language", "language.*input.*", "LLM", "Azure OpenAI", "GPT-4", "tokens", "input_tokens"),
        ("AZURE", "Language", "language.*output.*", "LLM", "Azure OpenAI", "GPT-4", "tokens", "output_tokens"),

        # Cognitive Services - Vision
        ("AZURE", "Vision", "vision.*analyze.*", "Vision", "Computer Vision", "Standard", "requests", "per_request"),
        ("AZURE", "Vision", "vision.*ocr.*", "Vision", "OCR", "Standard", "requests", "per_request"),

        # Cognitive Services - Speech
        ("AZURE", "Speech", "speech.*recognition.*", "Speech", "Speech to Text", "Standard", "hours", "per_hour"),
        ("AZURE", "Speech", "speech.*synthesis.*", "Speech", "Text to Speech", "Standard", "hours", "per_hour"),

        # Machine Learning
        ("AZURE", "Machine Learning", ".*ml.*instance.*", "Compute", "ML Instance", "Standard", "hour", "per_instance"),
    ]

    count = 0
    # See note in seed_ai_service_classifications() re: column mapping.
    for provider, service, sku_pattern, ai_type, ai_subtype, variant, usage_unit, tier in classifications:
        existing = db.query(AIServiceClassification).filter(
            AIServiceClassification.tenant_id == tenant_id,
            AIServiceClassification.provider == provider,
            AIServiceClassification.service == service,
            AIServiceClassification.sku_pattern == sku_pattern,
        ).one_or_none()

        if not existing:
            classification = AIServiceClassification(
                id=new_id(),
                tenant_id=tenant_id,
                provider=provider,
                service=service,
                sku_pattern=sku_pattern,
                ai_type=ai_type,
                ai_vendor=ai_subtype,
                ai_model=variant,
                cost_unit=usage_unit,
                token_type=tier,
                created_at=utcnow(),
            )
            db.add(classification)
            count += 1

    db.commit()
    return count


def seed_gcp_product_categories(db: Session, tenant_id: str = "tenant-demo") -> int:
    """Seed GCP service-to-category mappings."""

    categories = [
        # Compute
        ("GCP", "Compute Engine", "^(compute|n1|e2|c2|m1|m2|a2|n2|n2d)", "Compute", "VM", "hour"),
        ("GCP", "App Engine", ".*App Engine.*", "Compute", "App Engine", "hour"),
        ("GCP", "Cloud Functions", ".*Cloud Functions.*", "Compute", "Functions", "calls"),
        ("GCP", "Cloud Run", ".*Cloud Run.*", "Compute", "Cloud Run", "second"),
        ("GCP", "GKE", ".*Kubernetes.*", "Compute", "GKE", "hour"),

        # Storage
        ("GCP", "Cloud Storage", "^(Storage|Standard|Nearline|Coldline|Archive)", "Storage", "Storage", "gb_month"),
        ("GCP", "Cloud Datastore", ".*Datastore.*", "Storage", "Datastore", "operations"),

        # Database
        # Note: Cloud SQL and Firestore are categorized as Database only (not
        # also Storage) — ProductCategory uniqueness is keyed on
        # (tenant_id, provider, service_name, sku_pattern), so each sku_pattern
        # can map to exactly one category.
        ("GCP", "Cloud SQL", ".*Cloud SQL.*", "Database", "Cloud SQL", "hour"),
        ("GCP", "Firestore", ".*Firestore.*", "Database", "Firestore", "operations"),
        ("GCP", "Spanner", ".*Spanner.*", "Database", "Spanner", "hour"),
        ("GCP", "Bigtable", ".*Bigtable.*", "Database", "Bigtable", "hour"),
        ("GCP", "Memorystore", ".*Memorystore.*", "Database", "Redis/Memcached", "hour"),

        # Networking
        ("GCP", "Cloud CDN", ".*CDN.*", "Networking", "CDN", "gb_transfer"),
        ("GCP", "Cloud Load Balancing", ".*Load Balancing.*", "Networking", "LB", "hour"),
        ("GCP", "Cloud Interconnect", ".*Interconnect.*", "Networking", "Interconnect", "hour"),
        ("GCP", "Cloud VPN", ".*VPN.*", "Networking", "VPN", "hour"),
        ("GCP", "Cloud NAT", ".*Cloud NAT.*", "Networking", "NAT", "gb_transfer"),

        # AI/ML
        ("GCP", "Vertex AI", ".*Vertex.*", "AI/ML", "Vertex", "requests"),
        ("GCP", "BigQuery ML", ".*BigQuery ML.*", "AI/ML", "BQML", "bytes"),
        ("GCP", "AI Platform", ".*AI Platform.*", "AI/ML", "AI Platform", "hour"),
        ("GCP", "Vision API", ".*Vision API.*", "AI/ML", "Vision", "requests"),
        ("GCP", "Natural Language API", ".*Language API.*", "AI/ML", "NLP", "requests"),
        ("GCP", "Translation API", ".*Translate.*", "AI/ML", "Translation", "characters"),
        ("GCP", "Speech-to-Text", ".*Speech.*", "AI/ML", "Speech", "seconds"),

        # Data Analytics
        ("GCP", "BigQuery", "^(BigQuery|Analytical|Batch Query)", "Analytics", "BigQuery", "bytes"),
        ("GCP", "Dataflow", ".*Dataflow.*", "Analytics", "Dataflow", "vcpu_hours"),
        ("GCP", "Dataproc", ".*Dataproc.*", "Analytics", "Dataproc", "hour"),
        ("GCP", "Cloud Data Fusion", ".*Data Fusion.*", "Analytics", "Data Fusion", "hour"),
    ]

    count = 0
    for provider, service, sku_pattern, category, subcategory, unit_type in categories:
        existing = db.query(ProductCategory).filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.provider == provider,
            ProductCategory.service_name == service,
            ProductCategory.sku_pattern == sku_pattern,
        ).one_or_none()

        if not existing:
            mapping = ProductCategory(
                id=new_id(),
                tenant_id=tenant_id,
                provider=provider,
                service_name=service,
                sku_pattern=sku_pattern,
                category=category,
                subcategory=subcategory,
                unit_type=unit_type,
                created_at=utcnow(),
            )
            db.add(mapping)
            count += 1

    db.commit()
    return count


def seed_gcp_ai_classifications(db: Session, tenant_id: str = "tenant-demo") -> int:
    """Seed GCP AI service mappings."""

    classifications = [
        # Vertex AI - Models
        ("GCP", "Vertex AI", ".*textbison.*", "LLM", "PaLM", "Text", "tokens", "input_tokens"),
        ("GCP", "Vertex AI", ".*textbison.*output.*", "LLM", "PaLM", "Text", "tokens", "output_tokens"),

        # Vision API
        ("GCP", "Vision API", ".*detect.*", "Vision", "Vision API", "Standard", "requests", "per_request"),

        # Translation API
        ("GCP", "Translation API", ".*translate.*", "Translation", "Translation", "Standard", "characters", "per_character"),

        # Speech
        ("GCP", "Speech-to-Text", ".*recogn.*", "Speech", "Speech", "Standard", "seconds", "per_second"),

        # BigQuery ML
        ("GCP", "BigQuery ML", ".*bqml.*", "ML", "BQML", "Standard", "bytes", "per_byte"),
    ]

    count = 0
    # See note in seed_ai_service_classifications() re: column mapping.
    for provider, service, sku_pattern, ai_type, ai_subtype, variant, usage_unit, tier in classifications:
        existing = db.query(AIServiceClassification).filter(
            AIServiceClassification.tenant_id == tenant_id,
            AIServiceClassification.provider == provider,
            AIServiceClassification.service == service,
            AIServiceClassification.sku_pattern == sku_pattern,
        ).one_or_none()

        if not existing:
            classification = AIServiceClassification(
                id=new_id(),
                tenant_id=tenant_id,
                provider=provider,
                service=service,
                sku_pattern=sku_pattern,
                ai_type=ai_type,
                ai_vendor=ai_subtype,
                ai_model=variant,
                cost_unit=usage_unit,
                token_type=tier,
                created_at=utcnow(),
            )
            db.add(classification)
            count += 1

    db.commit()
    return count


def seed_all_mappings(tenant_id: str = "tenant-demo") -> dict[str, int]:
    """Seed all reference data."""
    db = SessionLocal()
    try:
        aws_categories_count = seed_aws_product_categories(db, tenant_id)
        azure_categories_count = seed_azure_product_categories(db, tenant_id)
        gcp_categories_count = seed_gcp_product_categories(db, tenant_id)
        aws_ai_count = seed_ai_service_classifications(db, tenant_id)
        azure_ai_count = seed_azure_ai_classifications(db, tenant_id)
        gcp_ai_count = seed_gcp_ai_classifications(db, tenant_id)

        return {
            "aws_product_categories": aws_categories_count,
            "azure_product_categories": azure_categories_count,
            "gcp_product_categories": gcp_categories_count,
            "aws_ai_classifications": aws_ai_count,
            "azure_ai_classifications": azure_ai_count,
            "gcp_ai_classifications": gcp_ai_count,
            "total": aws_categories_count + azure_categories_count + gcp_categories_count + aws_ai_count + azure_ai_count + gcp_ai_count,
        }
    finally:
        db.close()


if __name__ == "__main__":
    result = seed_all_mappings()
    print(f"Seeded mappings: {result}")
