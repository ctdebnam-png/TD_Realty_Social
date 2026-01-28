-- Migration: 001_website_leads.sql
-- Add website lead support with attribution and event tracking

-- Add columns to existing leads table for website lead support
ALTER TABLE leads ADD COLUMN lead_source TEXT DEFAULT 'manual';
ALTER TABLE leads ADD COLUMN first_seen_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN last_seen_at TIMESTAMP;

-- Attribution table for tracking where leads come from
CREATE TABLE IF NOT EXISTS lead_attribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    gclid TEXT,
    msclkid TEXT,
    fbclid TEXT,
    landing_page TEXT,
    referrer TEXT,
    referrer_domain TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

-- Events table for tracking all website interactions
CREATE TABLE IF NOT EXISTS lead_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    event_value TEXT,
    calculator_type TEXT,
    inputs_summary TEXT,
    page_path TEXT,
    session_id TEXT,
    device_type TEXT,
    city TEXT,
    region TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_lead_events_lead_id ON lead_events(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_events_event_name ON lead_events(event_name);
CREATE INDEX IF NOT EXISTS idx_lead_events_created_at ON lead_events(created_at);
CREATE INDEX IF NOT EXISTS idx_lead_attribution_lead_id ON lead_attribution(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_attribution_utm_campaign ON lead_attribution(utm_campaign);
CREATE INDEX IF NOT EXISTS idx_leads_lead_source ON leads(lead_source);
