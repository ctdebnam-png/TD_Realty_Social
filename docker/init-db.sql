-- TD Lead Engine - PostgreSQL Schema
-- Initialize database for production deployment

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),

    -- Contact info
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    username VARCHAR(100),

    -- Scoring
    score INTEGER DEFAULT 0,
    tier VARCHAR(20) DEFAULT 'cold',
    score_breakdown JSONB,

    -- Content
    bio TEXT,
    notes TEXT,

    -- Metadata
    profile_url TEXT,
    followers INTEGER DEFAULT 0,
    following INTEGER DEFAULT 0,
    engagement_rate REAL DEFAULT 0.0,

    -- Status tracking
    status VARCHAR(50) DEFAULT 'new',
    tags TEXT[] DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_scored_at TIMESTAMP WITH TIME ZONE,
    last_contacted_at TIMESTAMP WITH TIME ZONE,
    converted_at TIMESTAMP WITH TIME ZONE,

    -- Raw data storage
    raw_data JSONB,

    -- Constraints
    CONSTRAINT unique_source_id UNIQUE (source, source_id),
    CONSTRAINT valid_tier CHECK (tier IN ('hot', 'warm', 'lukewarm', 'cold', 'negative'))
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone) WHERE phone IS NOT NULL;

-- Full text search index
CREATE INDEX IF NOT EXISTS idx_leads_name_trgm ON leads USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_leads_bio_trgm ON leads USING gin(bio gin_trgm_ops);

-- Activities/interactions tracking
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,

    activity_type VARCHAR(50) NOT NULL,  -- 'note', 'email', 'call', 'sms', 'status_change', 'score_change'
    description TEXT,
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_activities_lead_id ON activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at DESC);

-- Webhooks configuration
CREATE TABLE IF NOT EXISTS webhooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    events TEXT[] NOT NULL,  -- Events to trigger on
    secret VARCHAR(255),

    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    failure_count INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled tasks
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    schedule VARCHAR(100) NOT NULL,  -- Cron expression
    config JSONB,

    is_active BOOLEAN DEFAULT true,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    last_result TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Metrics tracking
CREATE TABLE IF NOT EXISTS daily_metrics (
    date DATE PRIMARY KEY,
    leads_imported INTEGER DEFAULT 0,
    leads_scored INTEGER DEFAULT 0,
    hot_leads_found INTEGER DEFAULT 0,
    warm_leads_found INTEGER DEFAULT 0,
    imports_by_source JSONB DEFAULT '{}',
    avg_score REAL DEFAULT 0.0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Conversion tracking
CREATE TABLE IF NOT EXISTS conversions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,

    conversion_type VARCHAR(50) NOT NULL,  -- 'client', 'listing', 'buyer', 'referral'
    value DECIMAL(12, 2),  -- Transaction value if applicable
    notes TEXT,

    converted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversions_lead_id ON conversions(lead_id);
CREATE INDEX IF NOT EXISTS idx_conversions_type ON conversions(conversion_type);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhooks_updated_at
    BEFORE UPDATE ON webhooks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_metrics_updated_at
    BEFORE UPDATE ON daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default scheduled tasks
INSERT INTO scheduled_tasks (name, task_type, schedule, config, is_active) VALUES
    ('daily_score_all', 'score_all', '0 6 * * *', '{}', true),
    ('daily_digest', 'daily_digest', '0 8 * * *', '{"include_stats": true}', true),
    ('weekly_backup', 'backup', '0 2 * * 0', '{"compress": true}', true),
    ('hourly_hot_check', 'export_hot', '0 * * * *', '{"notify": true}', true)
ON CONFLICT (name) DO NOTHING;

-- View for lead summary
CREATE OR REPLACE VIEW lead_summary AS
SELECT
    tier,
    source,
    COUNT(*) as count,
    AVG(score) as avg_score,
    MAX(score) as max_score,
    MIN(created_at) as earliest_lead,
    MAX(created_at) as latest_lead
FROM leads
GROUP BY tier, source
ORDER BY tier, count DESC;

-- View for daily stats
CREATE OR REPLACE VIEW daily_stats AS
SELECT
    DATE(created_at) as date,
    COUNT(*) as leads_added,
    COUNT(CASE WHEN tier = 'hot' THEN 1 END) as hot_leads,
    COUNT(CASE WHEN tier = 'warm' THEN 1 END) as warm_leads,
    AVG(score) as avg_score
FROM leads
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tdengine;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tdengine;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO tdengine;
