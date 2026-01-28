# Current Architecture

## Overview

TD Lead Engine is a comprehensive real estate lead scoring and CRM system for TD Realty Ohio. It combines social media lead import, intent-based scoring, multi-channel notifications, and a React dashboard.

## CLI Commands

The `socialops` CLI (v2.0.0) provides:

### Core Commands
- `init` - Initialize the SQLite database and show setup wizard
- `import -s <source> -p <path>` - Import leads from various sources (14 connectors)
- `score` - Score all leads using 150+ intent signal phrases
- `show [--tier] [--source] [--status] [--limit]` - Display leads sorted by score
- `search <query>` - Search leads by name, email, phone, or notes
- `detail <lead_id>` - Show detailed information for a lead
- `stats` - Show database statistics (totals, tiers, sources, score stats)
- `sources` - List available import sources

### Lead Management
- `note <lead_id> <text>` - Add a timestamped note to a lead
- `status <lead_id> <status>` - Update lead status (new, contacted, responded, qualified, nurturing, converted, lost, archived)
- `convert <lead_id>` - Mark lead as converted with ML conversion tracking
- `tag <lead_id> <tags>` - Add comma-separated tags

### Export & Reports
- `export [--path] [--tier]` - Export leads to CSV
- `report [--type daily|weekly|monthly] [--format text|html|json]` - Generate reports

### Integration Setup
- `setup slack` - Configure Slack webhook notifications
- `setup zapier` - Configure Zapier webhooks
- `setup twilio` - Configure Twilio SMS
- `setup email` - Configure email (Gmail/SendGrid)
- `setup hubspot` - Configure HubSpot CRM sync
- `setup show` - Show integration status

### Automation
- `schedule list` - List scheduled tasks
- `schedule setup` - Create default schedule (daily scoring, digests, exports, backups)
- `schedule run <task_id>` - Run a specific task now

### Notifications
- `notify <lead_id> [--channel slack|sms|email|all]` - Send notification about a lead
- `test-notify <channel>` - Send test notification

### Utilities
- `test-score <text>` - Test scoring on arbitrary text
- `sync-hubspot` - Sync hot/warm leads to HubSpot

## Storage Layer

- **Database**: SQLite at `~/.td-lead-engine/leads.db`
- **Class**: `LeadDatabase` in `src/td_lead_engine/storage/database.py`

### Schema

**`leads` table:**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| source | TEXT NOT NULL | Import source (instagram, csv, etc.) |
| source_id | TEXT | Unique ID from source platform |
| name | TEXT | Contact name |
| email | TEXT | Email address (indexed) |
| phone | TEXT | Phone number (indexed) |
| username | TEXT | Social media username |
| profile_url | TEXT | Profile link |
| bio | TEXT | Bio/about text |
| notes | TEXT | Notes (appended over time) |
| messages_json | TEXT | JSON array of messages |
| comments_json | TEXT | JSON array of comments |
| score | INTEGER DEFAULT 0 | Calculated intent score (indexed DESC) |
| tier | TEXT DEFAULT 'cold' | hot/warm/lukewarm/cold/negative (indexed) |
| score_breakdown | TEXT | JSON object with matched signals |
| status | TEXT DEFAULT 'new' | Pipeline status (indexed) |
| tags | TEXT | Comma-separated tags |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last modification time |
| last_scored_at | TIMESTAMP | Last scoring time |
| last_contacted_at | TIMESTAMP | Last contact time |
| raw_data_json | TEXT | Original import data |

**Constraint:** `UNIQUE(source, source_id)`

**`interactions` table:**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| lead_id | INTEGER FK | References leads(id) (indexed) |
| interaction_type | TEXT NOT NULL | import, scored, contacted, response, note, status_change |
| content | TEXT | Interaction content |
| metadata_json | TEXT | Additional metadata |
| created_at | TIMESTAMP | Interaction time |

### Dedup Strategy

Multi-level matching (first match wins):
1. **Source + Source ID** (strongest) - Direct platform match
2. **Email** (strong) - Case-insensitive comparison
3. **Phone** (strong) - Last 10 digits extracted and compared
4. **Username + Source** (moderate) - Platform-specific username match

On duplicate, data is merged: prefers non-null values from existing record, appends bio/notes, deduplicates messages/comments arrays, logs merge as interaction.

## Scoring System

- **Engine**: `LeadScorer` in `src/td_lead_engine/core/scorer.py`
- **Signals**: 150+ intent phrases in `src/td_lead_engine/core/signals.py`

### Signal Categories and Weights

| Category | Weight Range | Description |
|----------|-------------|-------------|
| BUYER_ACTIVE | 75-95 | Actively searching to buy |
| BUYER_PASSIVE | 40-60 | Considering buying |
| SELLER_ACTIVE | 50-95 | Ready to sell |
| SELLER_PASSIVE | 40-55 | Considering selling |
| INVESTOR | 45-70 | Investment interest |
| TIMELINE | 35-75 | Urgency indicators |
| LOCATION | 10-30 | Central Ohio mentions |
| LIFE_EVENT | 50-70 | Major life changes |
| FINANCIAL | 30-75 | Financial readiness |
| NEGATIVE | -30 to -100 | Competitor/agent signals |

### Tier Thresholds

| Tier | Score Range | Description |
|------|------------|-------------|
| Hot | 150+ | High-intent buyers/sellers |
| Warm | 75-149 | Good potential |
| Lukewarm | 25-74 | Some interest |
| Cold | 0-24 | Minimal signals |
| Negative | < 0 | Competitor/agent detected |

### Algorithm
1. Pre-compiles regex patterns with word boundaries for all signals
2. Case-insensitive matching across all text fields (notes, bio, messages, comments)
3. Deduplicates same-phrase matches
4. Sums weights, groups by category
5. Returns `ScoringResult` with total, matches, category breakdown, tier

## Dashboard

### `apps/dashboard/server.py` (Flask, port 5000)

Routes:
- `GET /api/leads` - List leads with tier/limit filters
- `GET /api/leads/<id>` - Single lead with signals breakdown
- `PUT /api/leads/<id>/status` - Update lead status
- `POST /api/leads/<id>/note` - Add note
- `GET /api/stats` - Database statistics
- `GET /api/search?q=` - Search leads
- `POST /api/test-score` - Test scoring

### `src/td_lead_engine/api/app.py` (Flask REST API)

Full REST API with API key authentication, 30+ routes including leads CRUD, scoring, analytics, pipeline, routing, webhooks.

### `src/td_lead_engine/web/app.py` (Flask Web App)

Full web dashboard with login, leads management, pipeline Kanban, calendar, showings, transactions, reviews.

### Dashboard reads data via direct SQLite connection through `LeadDatabase` class.

## Connectors

14 import connectors in `src/td_lead_engine/connectors/`:

| Connector | Class | File Format |
|-----------|-------|-------------|
| instagram | InstagramConnector | ZIP export |
| facebook | FacebookConnector | ZIP export |
| csv | CSVConnector | CSV file |
| manual | ManualConnector | Manual entry |
| zillow | ZillowConnector | CSV |
| realtor.com | RealtorDotComConnector | CSV |
| homes.com | HomesDotComConnector | CSV |
| google_business | GoogleBusinessConnector | Takeout folder |
| google_contacts | GoogleContactsConnector | CSV |
| google_forms | GoogleFormsConnector | CSV |
| google_ads | GoogleAdsConnector | CSV |
| linkedin | LinkedInConnector | CSV |
| sales_navigator | SalesNavigatorConnector | CSV |
| nextdoor | NextdoorConnector | JSON |

All connectors extend `BaseConnector` and produce `RawLead` objects via `import_from_path()`.

## Deployment

### Docker Compose Services
1. **lead-engine** - Main API (port 5000)
2. **scheduler** - Background tasks daemon
3. **webhook-receiver** - Inbound webhooks (port 5001)
4. **redis** - Caching (optional, profile: full/cache)
5. **postgres** - Production DB (optional, profile: full/postgres)
6. **nginx** - Reverse proxy (optional, profile: full/production)

### Cloudflare Workers
- `cloudflare/workers/api.js` - Serverless API with D1 database
- `website-integration/cloudflare/` - Drop-in CRM package

## Notifications

Existing notification infrastructure:
- Slack webhooks via `WebhookManager`
- Twilio SMS via `TwilioSMSIntegration`
- Email via Gmail SMTP or SendGrid
- HubSpot CRM sync
- Zapier webhook triggers
