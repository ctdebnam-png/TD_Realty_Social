#!/bin/bash
# Add CRM to tdrealtyohio.com website
# Run after deploy.sh completes

set -e

echo "🌐 Adding CRM to tdrealtyohio.com"
echo "================================="

# Clone website repo if not exists
if [ ! -d "tdrealtyohio.com" ]; then
    echo "Cloning website repo..."
    git clone https://github.com/ctdebnam-png/tdrealtyohio.com
fi

cd tdrealtyohio.com

# Copy CRM dashboard
echo "Copying CRM dashboard..."
cp -r ../crm ./

# Commit and push
git add crm/
git commit -m "Add CRM dashboard

- Lead management with auto-scoring
- Task tracking
- Transaction pipeline
- Central Ohio market data"

git push origin main

echo ""
echo "✅ CRM added to website!"
echo ""
echo "Final step: Set up Cloudflare Access"
echo "1. Go to: https://one.dash.cloudflare.com"
echo "2. Access → Applications → Add application"
echo "3. Self-hosted: tdrealtyohio.com/crm"
echo "4. Add your team's email addresses"
echo ""
echo "Then visit: https://tdrealtyohio.com/crm/"
