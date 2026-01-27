-- TD Realty Ohio CRM Database Schema for Cloudflare D1

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    role TEXT DEFAULT 'agent',
    license_number TEXT,
    photo_url TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    secondary_phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT DEFAULT 'OH',
    zip TEXT,
    source TEXT,
    source_detail TEXT,
    lead_type TEXT DEFAULT 'buyer',
    status TEXT DEFAULT 'new',
    score INTEGER DEFAULT 0,
    tier TEXT DEFAULT 'cold',
    assigned_agent INTEGER REFERENCES agents(id),
    preapproved INTEGER DEFAULT 0,
    budget_min REAL,
    budget_max REAL,
    timeline TEXT,
    working_with_agent INTEGER,
    property_interest TEXT,
    notes TEXT,
    tags TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Lead activities
CREATE TABLE IF NOT EXISTS lead_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    activity_type TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT DEFAULT 'follow_up',
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    lead_id INTEGER REFERENCES leads(id),
    assigned_to INTEGER REFERENCES agents(id),
    due_date TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Contacts (past clients, referrals, vendors)
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT DEFAULT 'OH',
    zip TEXT,
    contact_type TEXT DEFAULT 'client',
    tags TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_address TEXT NOT NULL,
    city TEXT,
    state TEXT DEFAULT 'OH',
    zip TEXT,
    sale_price REAL,
    list_price REAL,
    transaction_type TEXT DEFAULT 'sale',
    status TEXT DEFAULT 'pending',
    client_id INTEGER REFERENCES contacts(id),
    agent_id INTEGER REFERENCES agents(id),
    listing_date TEXT,
    contract_date TEXT,
    closing_date TEXT,
    commission_rate REAL DEFAULT 0.03,
    commission_amount REAL,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Market trends (populated by scheduled jobs)
CREATE TABLE IF NOT EXISTS market_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    area TEXT DEFAULT 'central_ohio',
    median_price REAL,
    avg_price REAL,
    avg_dom INTEGER,
    active_listings INTEGER,
    new_listings INTEGER,
    closed_sales INTEGER,
    inventory_months REAL,
    price_change_yoy REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Neighborhood statistics
CREATE TABLE IF NOT EXISTS neighborhood_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT,
    zip_codes TEXT,
    median_price REAL,
    avg_price REAL,
    avg_dom INTEGER,
    price_per_sqft REAL,
    yoy_change REAL,
    school_rating REAL,
    walkability INTEGER,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Email campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'drip',
    status TEXT DEFAULT 'draft',
    subject TEXT,
    content TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_closing ON transactions(closing_date);

-- Insert initial agent (you!)
INSERT OR IGNORE INTO agents (email, name, role) VALUES 
    ('admin@tdrealtyohio.com', 'TD Realty Admin', 'admin');

-- Insert Central Ohio neighborhoods
INSERT OR IGNORE INTO neighborhood_stats (name, city, zip_codes, median_price, avg_dom, school_rating) VALUES
    ('Short North', 'Columbus', '43215', 425000, 14, 7.5),
    ('German Village', 'Columbus', '43206', 485000, 18, 7.8),
    ('Grandview Heights', 'Grandview Heights', '43212', 395000, 12, 8.2),
    ('Upper Arlington', 'Upper Arlington', '43221,43220', 525000, 21, 9.1),
    ('Worthington', 'Worthington', '43085', 385000, 16, 8.8),
    ('Dublin', 'Dublin', '43016,43017', 445000, 19, 9.0),
    ('Powell', 'Powell', '43065', 485000, 22, 9.2),
    ('Westerville', 'Westerville', '43081,43082', 345000, 15, 8.5),
    ('New Albany', 'New Albany', '43054', 625000, 28, 9.4),
    ('Gahanna', 'Gahanna', '43230', 315000, 14, 8.0),
    ('Hilliard', 'Hilliard', '43026', 335000, 13, 8.3),
    ('Grove City', 'Grove City', '43123', 285000, 11, 7.6),
    ('Reynoldsburg', 'Reynoldsburg', '43068', 265000, 12, 7.2),
    ('Pickerington', 'Pickerington', '43147', 345000, 17, 8.6),
    ('Canal Winchester', 'Canal Winchester', '43110', 315000, 14, 8.1),
    ('Delaware', 'Delaware', '43015', 295000, 18, 8.0),
    ('Bexley', 'Bexley', '43209', 545000, 16, 9.0),
    ('Clintonville', 'Columbus', '43214', 345000, 10, 7.4),
    ('Victorian Village', 'Columbus', '43201', 395000, 12, 7.3),
    ('Italian Village', 'Columbus', '43201', 385000, 11, 7.3);

-- Insert sample market trend data
INSERT OR IGNORE INTO market_trends (date, area, median_price, avg_price, avg_dom, active_listings, inventory_months, price_change_yoy) VALUES
    (date('now'), 'central_ohio', 285000, 315000, 21, 2450, 1.8, 5.2);
