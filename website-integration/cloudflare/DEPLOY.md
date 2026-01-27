# TD Realty Ohio CRM - Deployment Guide

Complete setup guide for deploying the CRM to tdrealtyohio.com using Cloudflare's free tier.

## Cost: $0/month

All services used are within Cloudflare's free tier:
- **D1 Database**: 5GB storage, 5M reads/day, 100k writes/day
- **Workers**: 100,000 requests/day
- **Cloudflare Access**: 50 users (perfect for a 3-agent team)

---

## Prerequisites

1. Node.js installed on your computer
2. Cloudflare account (free)
3. tdrealtyohio.com domain managed by Cloudflare

---

## Step 1: Install Wrangler CLI

```bash
npm install -g wrangler
```

## Step 2: Login to Cloudflare

```bash
wrangler login
```

This opens a browser window - authorize the CLI.

## Step 3: Create the D1 Database

```bash
cd cloudflare
wrangler d1 create td-realty-db
```

**IMPORTANT**: Copy the `database_id` from the output. It looks like:
```
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## Step 4: Update wrangler.toml

Edit `cloudflare/wrangler.toml` and replace `YOUR_DATABASE_ID_HERE` with your actual database_id:

```toml
[[d1_databases]]
binding = "DB"
database_name = "td-realty-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # Your actual ID
```

## Step 5: Initialize the Database

```bash
wrangler d1 execute td-realty-db --file=d1/schema.sql
```

This creates all tables and pre-populates Central Ohio neighborhood data.

## Step 6: Deploy the Worker

```bash
wrangler deploy
```

Note the Worker URL in the output (e.g., `https://td-realty-crm.YOUR-SUBDOMAIN.workers.dev`)

## Step 7: Update CRM Dashboard API URL

Edit `crm/index.html` and update the `API_URL` on line 458:

```javascript
API_URL: 'https://td-realty-crm.YOUR-SUBDOMAIN.workers.dev/api',
```

Replace `YOUR-SUBDOMAIN` with your actual Cloudflare Workers subdomain.

## Step 8: Deploy Website

Commit and push your changes:

```bash
git add crm/ cloudflare/
git commit -m "Add CRM dashboard and Cloudflare deployment"
git push
```

Cloudflare Pages will automatically deploy.

---

## Step 9: Set Up Password Protection (Cloudflare Access)

Protect your CRM so only your team can access it:

### 9a. Go to Cloudflare Zero Trust Dashboard

1. Log into Cloudflare Dashboard
2. Click **Zero Trust** in the left sidebar (or go to https://one.dash.cloudflare.com)

### 9b. Create an Access Application

1. Go to **Access** → **Applications**
2. Click **Add an application**
3. Select **Self-hosted**

### 9c. Configure the Application

**Application Configuration:**
- Application name: `TD Realty CRM`
- Session Duration: `24 hours`

**Application Domain:**
- Subdomain: (leave empty)
- Domain: `tdrealtyohio.com`
- Path: `crm`

Click **Next**

### 9d. Add Access Policy

**Policy name:** `Team Access`
**Action:** `Allow`

**Configure rules - Include:**
- Selector: `Emails`
- Value: Add your email and your agents' emails (one per line):
  ```
  you@email.com
  agent1@email.com
  agent2@email.com
  ```

Click **Next**, then **Add application**

### 9e. Test It

1. Open an incognito/private browser window
2. Go to `https://tdrealtyohio.com/crm/`
3. You should see a Cloudflare Access login screen
4. Enter your email
5. Check your email for a verification code
6. Enter the code - you're in!

---

## Step 10: Add Your Agents

After logging into the CRM, add your two agents via the browser console or curl:

```bash
curl -X POST https://td-realty-crm.YOUR-SUBDOMAIN.workers.dev/api/agents \
  -H "Content-Type: application/json" \
  -d '{"email": "agent1@email.com", "name": "Agent One", "role": "agent"}'

curl -X POST https://td-realty-crm.YOUR-SUBDOMAIN.workers.dev/api/agents \
  -H "Content-Type: application/json" \
  -d '{"email": "agent2@email.com", "name": "Agent Two", "role": "agent"}'
```

---

## Optional: Connect Website Lead Forms

Add this script to your existing contact forms to automatically capture leads:

```html
<script>
document.querySelector('#contact-form').addEventListener('submit', async (e) => {
    // Don't prevent default - let form submit normally

    // Capture lead in CRM
    await fetch('https://td-realty-crm.YOUR-SUBDOMAIN.workers.dev/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            first_name: e.target.querySelector('[name="first_name"]').value,
            last_name: e.target.querySelector('[name="last_name"]').value,
            email: e.target.querySelector('[name="email"]').value,
            phone: e.target.querySelector('[name="phone"]').value,
            source: 'website',
            lead_type: 'buyer',
            notes: e.target.querySelector('[name="message"]')?.value || ''
        })
    });
});
</script>
```

---

## Troubleshooting

### "Database not found" error
- Verify database_id in wrangler.toml matches `wrangler d1 list` output

### "Access denied" on /crm/
- Check Cloudflare Access policy includes your email
- Clear cookies and try incognito mode

### API returns 500 errors
- Check Worker logs: `wrangler tail`
- Verify D1 schema was applied: `wrangler d1 execute td-realty-db --command "SELECT name FROM sqlite_master WHERE type='table'"`

### CORS errors in browser console
- The Worker includes CORS headers; ensure you're using the full Worker URL

---

## Quick Reference

| Service | URL |
|---------|-----|
| CRM Dashboard | https://tdrealtyohio.com/crm/ |
| API Health Check | https://td-realty-crm.YOUR-SUBDOMAIN.workers.dev/api/health |
| Cloudflare Dashboard | https://dash.cloudflare.com |
| Zero Trust Dashboard | https://one.dash.cloudflare.com |

---

## Support

- Cloudflare D1 docs: https://developers.cloudflare.com/d1/
- Cloudflare Workers docs: https://developers.cloudflare.com/workers/
- Cloudflare Access docs: https://developers.cloudflare.com/cloudflare-one/applications/
