# TD Lead Engine - Platform & Deployment Guide

## Executive Summary

Your lead engine is production-ready for a **single-user/small team deployment**. For growth, here's the optimal path:

| Phase | Timeline | Platform | Cost |
|-------|----------|----------|------|
| **Phase 1: MVP** | Now | Local + Render/Railway | $0-7/mo |
| **Phase 2: Growth** | 3-6 months | Render + Supabase | $25-50/mo |
| **Phase 3: Scale** | 6-12 months | AWS/Vercel + Postgres | $100-200/mo |

---

## Recommended Domain Strategy

### Primary Options for Lead Generation

| Domain | Purpose | Price | Rating |
|--------|---------|-------|--------|
| **ColumbusHomeValue.com** | CMA/Seller capture | ~$12/yr | ⭐⭐⭐⭐⭐ |
| **WhatIsMyHomeWorthColumbus.com** | Long-tail SEO | ~$12/yr | ⭐⭐⭐⭐ |
| **Columbus1PercentListing.com** | Discount positioning | ~$12/yr | ⭐⭐⭐⭐ |
| **CentralOhioHomes.com** | Broad buyer capture | ~$15/yr | ⭐⭐⭐⭐ |
| **SellColumbus.com** | Short, memorable | ~$20/yr | ⭐⭐⭐⭐⭐ |

### Domain Strategy Recommendation

```
tdrealtyohio.com          → Brand/Trust (keep as main site)
         ↓
ColumbusHomeValue.com     → Lead capture landing pages
         ↓
td-lead-engine (internal) → Scoring & CRM backend
```

**Why separate domains?**
1. Test aggressive marketing without brand risk
2. A/B test different value propositions
3. Segment traffic sources cleanly
4. Better tracking of paid vs organic

---

## Deployment Options

### Option 1: Railway (Recommended for Starting)

**Best for:** Getting started quickly, low cost, simple deployment

```bash
# One-click deploy
railway login
railway init
railway up
```

**Cost:** Free tier → $5/mo for always-on
**Pros:** Simple, fast, includes database
**Cons:** Limited for high traffic

### Option 2: Render

**Best for:** Production deployment with auto-scaling

```yaml
# render.yaml
services:
  - type: web
    name: td-lead-engine
    env: python
    buildCommand: pip install -e .
    startCommand: gunicorn apps.dashboard.server:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
```

**Cost:** Free tier → $7/mo for production
**Pros:** Auto-deploy from Git, SSL included
**Cons:** Cold starts on free tier

### Option 3: Vercel + Supabase (Best for Growth)

**Best for:** High traffic, serverless scaling

**Frontend (Vercel):**
```bash
cd apps/dashboard
vercel deploy
```

**Backend (Supabase):**
- Replace SQLite with Supabase Postgres
- Use Supabase Auth for security
- Real-time subscriptions for live updates

**Cost:** $25/mo (Supabase Pro) + Vercel free
**Pros:** Scales automatically, great DX
**Cons:** Requires code changes for Postgres

### Option 4: Self-Hosted (Most Control)

**Best for:** Maximum control, lowest long-term cost

```bash
# Docker deployment
docker-compose up -d
```

**Requirements:**
- VPS ($5-20/mo: DigitalOcean, Linode, Vultr)
- Domain + SSL (Let's Encrypt = free)
- Basic Linux administration

---

## Integration Priority List

### Must-Have (Set Up First)

| Integration | Purpose | Setup Time | Cost |
|-------------|---------|------------|------|
| **Slack** | Instant hot lead alerts | 10 min | Free |
| **Zapier** | Connect to 5000+ apps | 15 min | Free tier |
| **Google Forms** | Landing page capture | 5 min | Free |

### High-Value (Set Up Next)

| Integration | Purpose | Setup Time | Cost |
|-------------|---------|------------|------|
| **Twilio SMS** | Text notifications | 20 min | ~$0.01/msg |
| **SendGrid** | Email notifications | 15 min | Free 100/day |
| **HubSpot** | Full CRM sync | 30 min | Free tier |

### Advanced (When Scaling)

| Integration | Purpose | Setup Time | Cost |
|-------------|---------|------------|------|
| **Follow Up Boss** | Real estate CRM | 1 hour | $69/mo |
| **Calendly** | Auto-scheduling | 15 min | Free tier |
| **Mailchimp** | Drip campaigns | 30 min | Free tier |

---

## Immediate Action Items (Outside This Environment)

### Today

1. **Register Domain** (15 min)
   - Go to Namecheap or Google Domains
   - Register `ColumbusHomeValue.com` or similar
   - Cost: ~$12/year

2. **Set Up Slack Webhook** (10 min)
   - Create Slack app at api.slack.com
   - Add incoming webhook
   - Run: `socialops config slack`

3. **Create Google Form** (10 min)
   - Create "Home Value Request" form
   - Fields: Name, Email, Phone, Address
   - Link to your domain

### This Week

4. **Deploy to Render/Railway** (30 min)
   - Push code to GitHub (if not already)
   - Connect to Render/Railway
   - Set environment variables

5. **Set Up Zapier** (20 min)
   - Create account at zapier.com
   - Set up "Hot Lead → SMS" Zap
   - Set up "New Lead → Google Sheets" Zap

6. **Import Existing Contacts** (30 min)
   - Export Instagram followers
   - Export Facebook friends/messages
   - Export any existing contact lists
   - Run through lead engine

### This Month

7. **Landing Page** (2-4 hours)
   - Create simple landing page on new domain
   - "What's Your Columbus Home Worth?" form
   - Connect form to lead engine via Zapier

8. **Twilio SMS** (30 min)
   - Sign up for Twilio
   - Get phone number
   - Configure hot lead alerts

9. **Track Conversions** (ongoing)
   - Mark leads as converted when they become clients
   - System will learn which signals predict success
   - Adjust scoring weights based on data

---

## Cost Breakdown (Monthly)

### MVP Setup ($0-20/mo)
```
Domain:         ~$1/mo (billed yearly)
Hosting:        $0-7/mo (Render/Railway free tier)
Slack:          Free
Zapier:         Free (100 tasks/mo)
Google Forms:   Free
───────────────────────
Total:          $1-8/mo
```

### Growth Setup ($30-60/mo)
```
Domain:         ~$1/mo
Hosting:        $7-25/mo (Render/Supabase)
Twilio:         ~$5/mo (phone + SMS)
SendGrid:       Free (or $15 for more)
Zapier:         $20/mo (multi-step Zaps)
───────────────────────
Total:          $33-66/mo
```

### Professional Setup ($100-200/mo)
```
Domain:         ~$2/mo (multiple)
Hosting:        $50-100/mo (dedicated resources)
HubSpot:        Free tier or $45/mo
Twilio:         ~$10/mo
Zapier:         $50/mo
Follow Up Boss: $69/mo (optional)
───────────────────────
Total:          $131-276/mo
```

---

## Architecture Recommendations

### Current Architecture (Good for MVP)
```
┌─────────────────┐     ┌─────────────────┐
│  Social Media   │────▶│   Lead Engine   │
│  (Instagram,    │     │   (Python CLI)  │
│   Facebook)     │     └────────┬────────┘
└─────────────────┘              │
                                 ▼
┌─────────────────┐     ┌─────────────────┐
│  Landing Pages  │────▶│    SQLite DB    │
│  (Google Forms) │     └────────┬────────┘
└─────────────────┘              │
                                 ▼
                        ┌─────────────────┐
                        │   Dashboard     │
                        │   (React)       │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Notifications  │
                        │ (Slack/SMS/Email)│
                        └─────────────────┘
```

### Future Architecture (For Scaling)
```
┌─────────────────────────────────────────────────────────────┐
│                        LEAD SOURCES                          │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│  Instagram  │  Facebook   │  Zillow     │  Landing Pages     │
│  Export     │  Export     │  Premier    │  (Vercel)          │
└──────┬──────┴──────┬──────┴──────┬──────┴──────────┬─────────┘
       │             │             │                 │
       └─────────────┴─────────────┴─────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │      API Gateway            │
              │   (Rate Limiting, Auth)     │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │      Lead Engine API        │
              │   (FastAPI on Render)       │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  PostgreSQL │  │    Redis    │  │  S3/R2      │
    │  (Supabase) │  │   (Cache)   │  │  (Backups)  │
    └─────────────┘  └─────────────┘  └─────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │      Webhook System         │
              │                             │
              ├─────────┬─────────┬─────────┤
              │  Slack  │  Twilio │ HubSpot │
              └─────────┴─────────┴─────────┘
```

---

## Security Checklist

Before going public:

- [ ] Enable HTTPS (automatic on Render/Vercel)
- [ ] Add authentication to dashboard
- [ ] Set up environment variables (not hardcoded)
- [ ] Enable CORS restrictions
- [ ] Add rate limiting to API
- [ ] Regular database backups
- [ ] Review data privacy (GDPR if applicable)

---

## Success Metrics to Track

| Metric | Target | How to Track |
|--------|--------|--------------|
| Leads per week | 50+ | Daily digest |
| Hot lead conversion | 20%+ | Conversion tracker |
| Response time to hot leads | <1 hour | Slack timestamps |
| Cost per lead | <$5 | Track ad spend / leads |
| Time to first contact | <24 hours | Status tracking |

---

## Quick Commands Reference

```bash
# Initialize
socialops init

# Import sources
socialops import --source instagram --path ./export.zip
socialops import --source csv --path ./contacts.csv
socialops import --source zillow --path ./leads.csv

# Score and view
socialops score
socialops show --tier hot

# Configure integrations
socialops config slack
socialops config twilio
socialops config zapier

# Reports
socialops report --daily
socialops report --weekly
socialops export --tier hot --path hot_leads.csv

# Test scoring
socialops test-score "First time homebuyer in Powell, preapproved"
```

---

## Support & Next Steps

1. **Questions?** Review the README.md for detailed CLI docs
2. **Issues?** Check logs in `~/.td-lead-engine/`
3. **Scaling?** Consider PostgreSQL migration when >50K leads

**Recommended Reading:**
- Zillow Premier Agent best practices
- Facebook lead ads setup
- Google Ads lead forms
- Real estate email drip campaigns
