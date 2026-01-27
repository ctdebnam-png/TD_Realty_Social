# TD Lead Engine

Social media lead scoring engine for real estate. Imports contacts from Instagram, Facebook, and CSV files, then scores them based on buying/selling intent signals tuned for Central Ohio.

## Quick Start

```bash
# Install
pip install -e .

# Initialize database
socialops init

# Import contacts
socialops import --source csv --path ./data/samples/contacts.csv

# Score all leads
socialops score

# View top leads
socialops show
```

## Features

| Component | Description |
|-----------|-------------|
| `src/td_lead_engine/core` | Scoring engine with 50+ intent phrases tuned for Central Ohio real estate |
| `src/td_lead_engine/connectors` | Importers for Instagram, Facebook, and manual CSVs |
| `src/td_lead_engine/storage` | SQLite database with full deduplication |
| `src/td_lead_engine/cli` | Command line tool (`socialops`) |
| `apps/dashboard` | React web UI (optional) |

## Scoring System

Leads are scored based on intent signals found in their notes, bio, messages, and comments:

| Tier | Score Range | Description |
|------|-------------|-------------|
| Hot | 150+ | High intent - preapproved buyers, ready sellers |
| Warm | 75-149 | Good potential - active search, life events |
| Lukewarm | 25-74 | Some interest - early research phase |
| Cold | <25 | Minimal signals |
| Negative | <0 | Competitor/agent signals detected |

### Intent Signal Categories

- **Buyer Active** - "preapproved", "house hunting", "ready to buy"
- **Buyer Passive** - "thinking about buying", "saving for a house"
- **Seller Active** - "listing my house", "what's my home worth"
- **Seller Passive** - "thinking about selling", "good time to sell"
- **Timeline** - "lease is up", "before school starts", "this month"
- **Life Events** - "getting married", "having a baby", "relocating"
- **Location** - Powell, Dublin, Westerville, German Village, etc.
- **Investor** - "investment property", "rental property", "flip"
- **Negative** - "as a realtor", competitor brand mentions

## CLI Commands

```bash
# Initialize database
socialops init

# Import from social media export
socialops import --source instagram --path ~/Downloads/instagram-export.zip
socialops import --source facebook --path ~/Downloads/facebook-export.zip

# Import from CSV
socialops import --source csv --path ./contacts.csv

# Score all leads
socialops score

# View leads
socialops show                    # Top 20 leads
socialops show --tier hot         # Hot leads only
socialops show -n 50              # Top 50 leads

# Search leads
socialops search "powell"

# View lead details
socialops detail 1

# Test scoring
socialops test-score "First time homebuyer looking in Powell, preapproved"

# Add notes
socialops note 1 "Called, left voicemail"

# Update status
socialops set-status 1 contacted

# Export to CSV
socialops export --path leads.csv
socialops export --tier hot --path hot_leads.csv

# Database stats
socialops stats
```

## Importing Data

### From Instagram

1. Go to Instagram Settings > Privacy and Security > Download Data
2. Request your data (JSON format)
3. Download the zip file when ready
4. Import: `socialops import --source instagram --path ./instagram-export.zip`

### From Facebook

1. Go to Facebook Settings > Your Facebook Information > Download Your Information
2. Select JSON format
3. Download the zip file
4. Import: `socialops import --source facebook --path ./facebook-export.zip`

### From CSV

Create a CSV with these columns (all optional except one identifier):

```csv
name,email,phone,notes
Amy Thompson,amy@email.com,614-555-0101,"First time homebuyer in Powell"
```

Import: `socialops import --source csv --path ./contacts.csv`

## Dashboard (Optional)

The React dashboard provides a visual interface for managing leads.

### Setup

```bash
cd apps/dashboard

# Install dependencies
npm install

# Run development server
npm run dev
```

For the API backend:

```bash
pip install flask flask-cors
python server.py
```

Then open http://localhost:3000

## Sample Data

A sample contacts file is included for testing:

```bash
socialops import --source csv --path ./data/samples/contacts.csv
socialops score
socialops show
```

Sample output:

| Score | Tier | Name | Signals |
|-------|------|------|---------|
| 235 | hot | Amy Thompson | first time homebuyer, preapproved, Powell |
| 195 | hot | Jennifer White | getting married, first home, preapproved |
| 175 | hot | Amanda Lee | expecting, outgrown, Clintonville |
| 155 | hot | Michael Taylor | ready to sell, German Village, home worth |
| 107 | warm | Mike Chen | lease is up, need more space |
| -100 | negative | David Martinez | as a realtor, Keller Williams |

## Project Structure

```
td-lead-engine/
├── src/td_lead_engine/
│   ├── core/
│   │   ├── signals.py      # Intent signals and weights
│   │   └── scorer.py       # Scoring engine
│   ├── connectors/
│   │   ├── instagram.py    # Instagram export parser
│   │   ├── facebook.py     # Facebook export parser
│   │   └── csv_import.py   # CSV/manual import
│   ├── storage/
│   │   ├── models.py       # Data models
│   │   └── database.py     # SQLite with deduplication
│   └── cli/
│       └── main.py         # CLI commands
├── apps/dashboard/         # React web UI
├── data/samples/           # Sample data files
├── pyproject.toml
└── README.md
```

## Database Location

By default, the database is stored at:
- `~/.td-lead-engine/leads.db`

You can specify a custom path with `--db`:
```bash
socialops --db ./custom/path.db show
```

## License

MIT
