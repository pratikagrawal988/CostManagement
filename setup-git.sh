#!/bin/bash

# FinOps Git Setup Script
# Usage: bash setup-git.sh

set -e

echo "🚀 FinOps Git Setup"
echo "===================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Prompt for GitHub details
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your GitHub organization name (or leave blank for personal): " GITHUB_ORG
GITHUB_ORG=${GITHUB_ORG:-$GITHUB_USERNAME}

echo ""
echo "Setting up two repositories under: github.com/$GITHUB_ORG/"
echo ""

# Repository 1: Production Code
REPO1_NAME="finops-recommendation-engine"
REPO1_PATH="/Users/pratikagrawal/Documents/Claude/Projects/FinOps/Recommendation-engine"

echo "📦 Repository 1: $REPO1_NAME"
echo "Path: $REPO1_PATH"

if [ ! -d "$REPO1_PATH" ]; then
    echo "❌ Directory not found: $REPO1_PATH"
    exit 1
fi

cd "$REPO1_PATH"

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "✏️  Creating .gitignore..."
    cat > .gitignore << 'GITIGNORE'
# Environment & Secrets
.env
.env.local
.env.*.local
secrets/
.vault

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
*.egg-info/
dist/
build/
.pytest_cache/

# Node/Frontend
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
dist/
.vite/
.next/
.nuxt/
.cache/

# Database
*.db
*.sqlite
*.sqlite3
postgres_data/
data/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Docker
.dockerignore

# Logs
logs/
*.log
GITIGNORE
    echo "✅ .gitignore created"
else
    echo "ℹ️  .gitignore already exists"
fi

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "✏️  Initializing git repository..."
    git init
    git config user.name "$GITHUB_USERNAME"
    git config user.email "$(git config --global user.email || echo 'your-email@example.com')"
else
    echo "ℹ️  Git repository already initialized"
fi

echo "✏️  Staging files..."
git add .

echo "✏️  Creating initial commit..."
git commit -m "Initial commit: FinOps Recommendation Engine backend + frontend" || echo "ℹ️  Nothing new to commit"

echo "✏️  Setting main branch..."
git branch -M main

echo ""
echo "✅ Repository 1 prepared!"
echo ""
echo "Next steps for $REPO1_NAME:"
echo "1. Create repository on GitHub: https://github.com/$GITHUB_ORG/$REPO1_NAME"
echo "2. Run: git remote add origin https://github.com/$GITHUB_ORG/$REPO1_NAME.git"
echo "3. Run: git push -u origin main"
echo ""

# Repository 2: Product Docs
REPO2_NAME="finops-product-docs"
REPO2_PATH="/Users/pratikagrawal/Documents/Claude/Projects/FinOps/Recommendation-engine-catalog"

echo "📚 Repository 2: $REPO2_NAME"
echo "Path: $REPO2_PATH"

if [ ! -d "$REPO2_PATH" ]; then
    echo "❌ Directory not found: $REPO2_PATH"
    exit 1
fi

cd "$REPO2_PATH"

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "✏️  Creating .gitignore..."
    cat > .gitignore << 'GITIGNORE'
# Large generated files
data/csp_catalog/
*.log
__pycache__/

# IDE
.vscode/
.idea/
*.swp
.DS_Store
GITIGNORE
    echo "✅ .gitignore created"
else
    echo "ℹ️  .gitignore already exists"
fi

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "✏️  Initializing git repository..."
    git init
    git config user.name "$GITHUB_USERNAME"
    git config user.email "$(git config --global user.email || echo 'your-email@example.com')"
else
    echo "ℹ️  Git repository already initialized"
fi

echo "✏️  Staging files..."
git add .

echo "✏️  Creating initial commit..."
git commit -m "Initial commit: FinOps product docs, specs, UI mockups" || echo "ℹ️  Nothing new to commit"

echo "✏️  Setting main branch..."
git branch -M main

echo ""
echo "✅ Repository 2 prepared!"
echo ""
echo "Next steps for $REPO2_NAME:"
echo "1. Create repository on GitHub: https://github.com/$GITHUB_ORG/$REPO2_NAME"
echo "2. Run: git remote add origin https://github.com/$GITHUB_ORG/$REPO2_NAME.git"
echo "3. Run: git push -u origin main"
echo ""

echo "===================="
echo "✅ Setup Complete!"
echo "===================="
echo ""
echo "Summary:"
echo "- Repository 1: $REPO1_NAME (PUBLIC - product code)"
echo "- Repository 2: $REPO2_NAME (PRIVATE - internal docs)"
echo ""
echo "📖 Read GIT_STRATEGY.md for detailed setup instructions"
echo ""
