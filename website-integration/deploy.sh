#!/bin/bash
# TD Realty Ohio CRM - One-Click Deployment Script
# Run this on your local machine after: wrangler login

set -e

echo "🏠 TD Realty Ohio CRM Deployment"
echo "================================"

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null && ! command -v npx &> /dev/null; then
    echo "❌ Please install wrangler: npm install -g wrangler"
    exit 1
fi

WRANGLER="wrangler"
if ! command -v wrangler &> /dev/null; then
    WRANGLER="npx wrangler"
fi

# Step 1: Login if needed
echo ""
echo "📋 Step 1: Checking authentication..."
if ! $WRANGLER whoami 2>/dev/null | grep -q "@"; then
    echo "Please login to Cloudflare..."
    $WRANGLER login
fi
echo "✅ Authenticated"

# Step 2: Create D1 Database
echo ""
echo "📋 Step 2: Creating D1 database..."
DB_OUTPUT=$($WRANGLER d1 create td-realty-db 2>&1 || true)

if echo "$DB_OUTPUT" | grep -q "already exists"; then
    echo "Database already exists, getting ID..."
    DB_ID=$($WRANGLER d1 list --json | grep -A5 "td-realty-db" | grep '"uuid"' | cut -d'"' -f4)
else
    DB_ID=$(echo "$DB_OUTPUT" | grep "database_id" | cut -d'"' -f2)
fi

if [ -z "$DB_ID" ]; then
    echo "❌ Could not get database ID. Please check Cloudflare dashboard."
    exit 1
fi
echo "✅ Database ID: $DB_ID"

# Step 3: Update wrangler.toml
echo ""
echo "📋 Step 3: Updating wrangler.toml..."
cd "$(dirname "$0")/cloudflare"
sed -i.bak "s/YOUR_DATABASE_ID_HERE/$DB_ID/" wrangler.toml
echo "✅ Updated wrangler.toml"

# Step 4: Initialize database schema
echo ""
echo "📋 Step 4: Initializing database..."
$WRANGLER d1 execute td-realty-db --file=d1/schema.sql
echo "✅ Database initialized with Central Ohio neighborhoods"

# Step 5: Deploy Worker
echo ""
echo "📋 Step 5: Deploying Worker API..."
DEPLOY_OUTPUT=$($WRANGLER deploy 2>&1)
WORKER_URL=$(echo "$DEPLOY_OUTPUT" | grep -o "https://[^[:space:]]*workers.dev" | head -1)
echo "✅ Worker deployed"

# Step 6: Update CRM dashboard with Worker URL
echo ""
echo "📋 Step 6: Updating CRM dashboard..."
cd ../crm
if [ -n "$WORKER_URL" ]; then
    sed -i.bak "s|https://td-realty-crm.tdrealtyohio.workers.dev|$WORKER_URL|" index.html
    echo "✅ Updated API URL to: $WORKER_URL/api"
fi

echo ""
echo "=========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Worker URL: $WORKER_URL"
echo ""
echo "Next steps:"
echo "1. Copy the 'crm' folder to your tdrealtyohio.com repo"
echo "2. Set up Cloudflare Access (see cloudflare/DEPLOY.md)"
echo ""
echo "Quick test:"
echo "  curl $WORKER_URL/api/health"
echo ""
