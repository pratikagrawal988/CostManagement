#!/bin/bash

# FinOps SaaS - Project Restructuring Script
# This script reorganizes the project into an enterprise-standard structure

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"

echo "=================================="
echo "FinOps SaaS Project Restructuring"
echo "=================================="
echo "Root: $PROJECT_ROOT"
echo ""

# Check if we're in the right directory
if [ ! -d "$PROJECT_ROOT/Recommendation-engine" ]; then
    echo "❌ Error: Recommendation-engine folder not found"
    exit 1
fi

# Backup current state
echo "📦 Creating backup..."
BACKUP_DIR="$PROJECT_ROOT/.backup-$(date +%s)"
mkdir -p "$BACKUP_DIR"
cp -r "$PROJECT_ROOT/Recommendation-engine" "$BACKUP_DIR/"
echo "✅ Backup created at: $BACKUP_DIR"
echo ""

# Create new root-level directories
echo "📁 Creating new directory structure..."
mkdir -p "$PROJECT_ROOT/backend/app/{api/v1/{cost,aws,azure,gcp,users,health},jobs/{aws,azure,gcp,shared},services,connectors/{aws,azure,gcp},seed/mappings,middleware,utils}"
mkdir -p "$PROJECT_ROOT/backend/tests/{unit,integration,fixtures}"
mkdir -p "$PROJECT_ROOT/backend/migrations/versions"
mkdir -p "$PROJECT_ROOT/frontend/src/{components/{Dashboard/{Executive,Finance,FinOps,Team,Cloud,Focus,AI},Admin/{CostSetup,UserManagement,BudgetManagement}},pages,hooks,services,types,styles}"
mkdir -p "$PROJECT_ROOT/frontend/tests/{unit,integration,fixtures}"
mkdir -p "$PROJECT_ROOT/infrastructure/{kubernetes/{RBAC},terraform/{aws,azure,gcp},scripts}"
mkdir -p "$PROJECT_ROOT/docs/{architecture,api,setup,guides,operations}"
mkdir -p "$PROJECT_ROOT/.github/workflows"
mkdir -p "$PROJECT_ROOT/scripts"
mkdir -p "$PROJECT_ROOT/config"
echo "✅ Directory structure created"
echo ""

# Move backend code
echo "🔄 Moving backend code..."

# Backend app files
echo "  Moving app files..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/__init__.py" "$PROJECT_ROOT/backend/app/"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/main.py" "$PROJECT_ROOT/backend/app/"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/database.py" "$PROJECT_ROOT/backend/app/"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/models.py" "$PROJECT_ROOT/backend/app/"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/settings.py" "$PROJECT_ROOT/backend/app/"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/schemas.py" "$PROJECT_ROOT/backend/app/"

# API Routes
echo "  Moving API routes..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/routes_cost.py" "$PROJECT_ROOT/backend/app/api/v1/cost/routes.py"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/routes_aws.py" "$PROJECT_ROOT/backend/app/api/v1/aws/routes.py" 2>/dev/null || echo "    (AWS routes not found - skipping)"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/routes_azure.py" "$PROJECT_ROOT/backend/app/api/v1/azure/routes.py" 2>/dev/null || echo "    (Azure routes not found - skipping)"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/routes_gcp.py" "$PROJECT_ROOT/backend/app/api/v1/gcp/routes.py" 2>/dev/null || echo "    (GCP routes not found - skipping)"

# Create __init__ files for API
echo "  Creating API router initialization..."
cat > "$PROJECT_ROOT/backend/app/api/__init__.py" << 'EOF'
"""API routes for FinOps SaaS"""
EOF

cat > "$PROJECT_ROOT/backend/app/api/v1/__init__.py" << 'EOF'
"""API v1 routes"""
from fastapi import APIRouter

def get_api_router():
    """Register all API routers"""
    router = APIRouter(prefix="/api/v1")

    # Cost routes
    from .cost.routes import router as cost_router
    router.include_router(cost_router, tags=["cost"])

    # AWS routes
    from .aws.routes import router as aws_router
    router.include_router(aws_router, tags=["aws"])

    # Azure routes
    from .azure.routes import router as azure_router
    router.include_router(azure_router, tags=["azure"])

    # GCP routes
    from .gcp.routes import router as gcp_router
    router.include_router(gcp_router, tags=["gcp"])

    # Health routes
    from .health.routes import router as health_router
    router.include_router(health_router, tags=["health"])

    return router
EOF

# Jobs
echo "  Moving job files..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/jobs.py" "$PROJECT_ROOT/backend/app/jobs/scheduler.py"
# Note: aws_cur_ingest.py, azure_jobs.py, gcp_jobs.py would need to be split
# by cloud provider - these should be organized by cloud provider

# Connectors
echo "  Moving connector files..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/connectors.py" "$PROJECT_ROOT/backend/app/connectors/base.py"

# Services
echo "  Moving service files..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/recommendations.py" "$PROJECT_ROOT/backend/app/services/recommendation_service.py" 2>/dev/null || echo "    (recommendations.py not found - skipping)"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/evaluator.py" "$PROJECT_ROOT/backend/app/services/evaluator.py" 2>/dev/null || echo "    (evaluator.py not found - skipping)"

# Seed data
echo "  Moving seed data files..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/seed.py" "$PROJECT_ROOT/backend/app/seed/seed_data.py"
cp "$PROJECT_ROOT/Recommendation-engine/backend/app/seed_cost_mappings.py" "$PROJECT_ROOT/backend/app/seed/mappings/service_mappings.py" 2>/dev/null || echo "    (seed_cost_mappings.py - checking...)"

# Tests
echo "  Moving test files..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/tests/test_engine.py" "$PROJECT_ROOT/backend/tests/integration/" 2>/dev/null || echo "    (test_engine.py not found - skipping)"

# Backend root files
echo "  Moving backend configuration..."
cp "$PROJECT_ROOT/Recommendation-engine/backend/requirements.txt" "$PROJECT_ROOT/backend/"
cp "$PROJECT_ROOT/Recommendation-engine/backend/Dockerfile" "$PROJECT_ROOT/backend/" 2>/dev/null || echo "    (Dockerfile not found - skipping)"
[ -f "$PROJECT_ROOT/Recommendation-engine/backend/.env.example" ] && cp "$PROJECT_ROOT/Recommendation-engine/backend/.env.example" "$PROJECT_ROOT/backend/"

echo "✅ Backend code moved"
echo ""

# Move frontend code
echo "🔄 Moving frontend code..."
echo "  Moving component files..."
cp "$PROJECT_ROOT/Recommendation-engine/frontend/src/pages/CostDashboards.jsx" "$PROJECT_ROOT/frontend/src/components/Dashboard/" 2>/dev/null || echo "    (CostDashboards.jsx - checking...)"
cp "$PROJECT_ROOT/Recommendation-engine/frontend/src/pages/AdminCostSetup.jsx" "$PROJECT_ROOT/frontend/src/components/Admin/CostSetup/" 2>/dev/null || echo "    (AdminCostSetup.jsx - checking...)"

echo "  Moving service and utility files..."
cp "$PROJECT_ROOT/Recommendation-engine/frontend/src/api.ts" "$PROJECT_ROOT/frontend/src/services/api.ts" 2>/dev/null || echo "    (api.ts not found - skipping)"

echo "  Moving frontend root files..."
cp "$PROJECT_ROOT/Recommendation-engine/frontend/package.json" "$PROJECT_ROOT/frontend/"
cp "$PROJECT_ROOT/Recommendation-engine/frontend/package-lock.json" "$PROJECT_ROOT/frontend/" 2>/dev/null || echo "    (package-lock.json not found - skipping)"
cp "$PROJECT_ROOT/Recommendation-engine/frontend/vite.config.ts" "$PROJECT_ROOT/frontend/" 2>/dev/null || echo "    (vite.config.ts not found - skipping)"
cp "$PROJECT_ROOT/Recommendation-engine/frontend/tsconfig.json" "$PROJECT_ROOT/frontend/" 2>/dev/null || echo "    (tsconfig.json not found - skipping)"
cp "$PROJECT_ROOT/Recommendation-engine/frontend/Dockerfile" "$PROJECT_ROOT/frontend/" 2>/dev/null || echo "    (Dockerfile not found - skipping)"

echo "✅ Frontend code moved"
echo ""

# Move configuration files
echo "🔄 Moving configuration files..."
cp "$PROJECT_ROOT/Recommendation-engine/config/schedules.yaml" "$PROJECT_ROOT/config/" 2>/dev/null || echo "    (schedules.yaml not found - skipping)"
cp "$PROJECT_ROOT/Recommendation-engine/docker-compose.yml" "$PROJECT_ROOT/infrastructure/" 2>/dev/null || echo "    (docker-compose.yml not found - skipping)"

echo "✅ Configuration files moved"
echo ""

# Create __init__ files for Python packages
echo "📝 Creating Python package initializers..."
for dir in "$PROJECT_ROOT/backend/app/api/v1"/{cost,aws,azure,gcp,users,health}; do
    touch "$dir/__init__.py"
done
for dir in "$PROJECT_ROOT/backend/app/jobs"/{aws,azure,gcp,shared}; do
    touch "$dir/__init__.py"
done
for dir in "$PROJECT_ROOT/backend/app/connectors"/{aws,azure,gcp}; do
    touch "$dir/__init__.py"
done
for dir in "$PROJECT_ROOT/backend/app"/{services,middleware,utils} "$PROJECT_ROOT/backend/tests"/{unit,integration,fixtures}; do
    touch "$dir/__init__.py"
done
echo "✅ Python package initializers created"
echo ""

# Create README files for each major section
echo "📝 Creating documentation files..."

cat > "$PROJECT_ROOT/backend/README.md" << 'EOF'
# FinOps SaaS - Backend API

FastAPI-based backend for multi-cloud cost aggregation and analysis.

## Directory Structure

- `app/` - Main application code
  - `api/` - API routes organized by resource
  - `jobs/` - Background jobs and scheduling
  - `services/` - Business logic
  - `connectors/` - Cloud provider integrations
  - `models.py` - Database models
  - `main.py` - FastAPI application

- `tests/` - Unit and integration tests
- `migrations/` - Database migrations

## Getting Started

```bash
pip install -r requirements.txt
python -m app.main
```

See `docs/` for detailed documentation.
EOF

cat > "$PROJECT_ROOT/frontend/README.md" << 'EOF'
# FinOps SaaS - Frontend UI

React-based frontend for FinOps cost management platform.

## Directory Structure

- `src/components/` - Reusable React components
  - `Dashboard/` - Dashboard components
  - `Admin/` - Admin panel components
  - `Common/` - Shared components

- `src/pages/` - Page components
- `src/services/` - API client services
- `src/hooks/` - Custom React hooks
- `src/types/` - TypeScript type definitions

## Getting Started

```bash
npm install
npm run dev
```

See `docs/` for detailed documentation.
EOF

cat > "$PROJECT_ROOT/infrastructure/README.md" << 'EOF'
# FinOps SaaS - Infrastructure

Infrastructure as Code and deployment configurations.

## Contents

- `docker-compose.yml` - Local development environment
- `kubernetes/` - Kubernetes manifests for production
- `terraform/` - Infrastructure provisioning scripts
- `scripts/` - Deployment and maintenance scripts

See `docs/guides/DEPLOYMENT.md` for detailed instructions.
EOF

echo "✅ Documentation files created"
echo ""

# Create .gitignore files
echo "📝 Creating .gitignore files..."

cat > "$PROJECT_ROOT/backend/.gitignore" << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.coverage
.pytest_cache/
htmlcov/
.env
.env.local
*.db
*.sqlite
*.sqlite3
.DS_Store
EOF

cat > "$PROJECT_ROOT/frontend/.gitignore" << 'EOF'
node_modules/
dist/
.env
.env.local
.env.*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.DS_Store
EOF

echo "✅ .gitignore files created"
echo ""

# Summary
echo "=================================="
echo "✅ Restructuring Complete!"
echo "=================================="
echo ""
echo "Summary:"
echo "  - Backend moved to: ./backend"
echo "  - Frontend moved to: ./frontend"
echo "  - Infrastructure moved to: ./infrastructure"
echo "  - Documentation moved to: ./docs"
echo "  - Backup saved to: $BACKUP_DIR"
echo ""
echo "Next Steps:"
echo "  1. Review the new structure"
echo "  2. Update import statements in Python files"
echo "  3. Update import statements in JavaScript files"
echo "  4. Update docker-compose.yml paths"
echo "  5. Run tests to verify everything works"
echo "  6. Commit changes with: git add . && git commit -m 'refactor: reorganize project structure'"
echo "  7. Delete old Recommendation-engine folder if everything works"
echo ""
echo "See PROJECT_RESTRUCTURING_PLAN.md for detailed information."
echo ""
