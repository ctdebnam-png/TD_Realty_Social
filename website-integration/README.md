# Website Integration Package

This folder contains everything needed to add the CRM to your tdrealtyohio.com website.

## Quick Start

### 1. Copy files to your website repo

```bash
# Clone your website if you haven't
git clone https://github.com/ctdebnam-png/tdrealtyohio.com
cd tdrealtyohio.com

# Copy the CRM dashboard
cp -r /path/to/TD_Realty_Social/website-integration/crm ./

# Copy the Cloudflare deployment files
cp -r /path/to/TD_Realty_Social/website-integration/cloudflare ./
```

### 2. Follow the deployment guide

See `cloudflare/DEPLOY.md` for complete step-by-step instructions.

## What's Included

```
website-integration/
├── crm/
│   └── index.html          # CRM dashboard (goes to tdrealtyohio.com/crm/)
├── cloudflare/
│   ├── DEPLOY.md           # Complete deployment guide
│   ├── wrangler.toml       # Worker configuration
│   ├── workers/
│   │   └── api.js          # Cloudflare Worker API
│   └── d1/
│       └── schema.sql      # Database schema
└── README.md               # This file
```

## Architecture

```
tdrealtyohio.com (Cloudflare Pages)
├── /crm/                   → CRM Dashboard (password protected)
│   └── index.html          → Alpine.js single-page app
│
└── Worker API              → td-realty-crm.workers.dev
    └── D1 Database         → Leads, tasks, transactions
```

## Features

- Lead management with automatic scoring
- Task tracking with due dates
- Transaction pipeline
- Central Ohio market data (20 neighborhoods)
- Team management for 3 agents

## Cost

**$0/month** - All within Cloudflare free tier limits.
