# TD Realty Ohio CRM - Deployment Guide

## Overview

This CRM integrates directly into your existing tdrealtyohio.com website using:
- **Cloudflare D1** (free SQLite database)
- **Cloudflare Workers** (free API tier - 100k requests/day)
- **Cloudflare Access** (free password protection for up to 50 users)

**Total monthly cost: $0** (within free tier limits)

## Quick Setup (15 minutes)

### Step 1: Create the Database

```bash
# Install Wrangler if you haven't
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create the D1 database
wrangler d1 create td-realty-db

# Note the database_id from the output - you'll need it
```

### Step 2: Initialize Database Schema

```bash
# From the cloudflare directory in this repo
wrangler d1 execute td-realty-db --file=d1/schema.sql
```

### Step 3: Deploy the API Worker

1. Update `wrangler.toml` with your database_id from Step 1
2. Deploy:

```bash
wrangler deploy
```

### Step 4: Add CRM to Your Website

Copy the `crm/` folder to your tdrealtyohio.com repo:

```
tdrealtyohio.com/
├── index.html
├── sellers/
├── buyers/
├── crm/              <-- Add this folder
│   └── index.html    <-- The CRM dashboard
├── assets/
└── ...
```

### Step 5: Set Up Password Protection (Cloudflare Access)

1. Go to Cloudflare Dashboard → Zero Trust → Access → Applications
2. Click "Add an Application" → Self-hosted
3. Configure:
   - Application name: `TD Realty CRM`
   - Session duration: `24 hours`
   - Application domain: `tdrealtyohio.com`
   - Path: `/crm/*`
4. Add a policy:
   - Policy name: `Team Access`
   - Action: `Allow`
   - Include: `Emails` → add your email and your agents' emails
5. Save

### Step 6: Configure API URL

Edit `crm/index.html` and update the API_URL:

```javascript
API_URL: 'https://td-realty-crm.your-subdomain.workers.dev/api',
```

Or if using a custom domain route:
```javascript
API_URL: '/api',
```

### Step 7: Deploy Your Website

```bash
# In your tdrealtyohio.com repo
git add crm/
git commit -m "Add CRM dashboard"
git push
```

Cloudflare Pages will automatically deploy.

## Accessing the CRM

1. Go to: `https://tdrealtyohio.com/crm/`
2. Cloudflare Access will prompt for authentication
3. Enter your email and verify via code sent to your inbox
4. You're in!

## Adding Your Agents

After first login, add your two agents via the API:

```bash
# Using curl or in the browser console
curl -X POST https://your-worker.workers.dev/api/agents \
  -H "Content-Type: application/json" \
  -d '{"email": "agent1@email.com", "name": "Agent Name", "role": "agent"}'
```

## Connecting Lead Forms

Add this to your existing website forms to automatically create leads:

```html
<script>
document.querySelector('#contact-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            email: formData.get('email'),
            phone: formData.get('phone'),
            source: 'website',
            lead_type: 'buyer',
            notes: formData.get('message')
        })
    });
    
    // Continue with your normal form submission
});
</script>
```

## Daily Automation

The Worker runs a scheduled job daily at 6 AM to:
- Collect market data
- Generate task reminders
- Update lead scores

## Troubleshooting

### "Database not found" error
- Make sure database_id in wrangler.toml matches your D1 database

### "Access denied" on /crm/
- Check Cloudflare Access policy includes your email
- Clear browser cache and cookies

### API returns 500 errors
- Check Worker logs: `wrangler tail`
- Verify D1 schema was applied correctly

## Architecture

```
tdrealtyohio.com (Cloudflare Pages)
│
├── /crm/           → Static dashboard (password protected)
│   └── index.html  → Alpine.js dashboard
│
└── /api/*          → Cloudflare Worker (API)
    └── D1 Database → Lead, task, transaction data
```

## Free Tier Limits

- **D1**: 5GB storage, 5M reads/day, 100k writes/day
- **Workers**: 100k requests/day
- **Access**: 50 users

For a 3-agent team, you'll never exceed these limits.

## Support

Questions? Check:
- Cloudflare D1 docs: https://developers.cloudflare.com/d1/
- Cloudflare Workers docs: https://developers.cloudflare.com/workers/
- Cloudflare Access docs: https://developers.cloudflare.com/cloudflare-one/applications/
