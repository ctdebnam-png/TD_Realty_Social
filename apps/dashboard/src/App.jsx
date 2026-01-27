import { useState, useEffect } from 'react'

// Sample data for demo (when API isn't available)
const SAMPLE_LEADS = [
  { id: 1, name: 'Amy Thompson', email: 'amy@email.com', phone: '614-555-0101', score: 235, tier: 'hot', source: 'instagram', signals: ['first time homebuyer', 'preapproved', 'Powell'] },
  { id: 2, name: 'Mike Chen', email: 'mike.chen@email.com', phone: '614-555-0102', score: 107, tier: 'hot', source: 'facebook', signals: ['lease is up', 'need more space'] },
  { id: 3, name: 'Sarah Johnson', email: 'sarah.j@email.com', phone: '614-555-0103', score: 85, tier: 'warm', source: 'manual', signals: ['thinking about selling', 'Westerville'] },
  { id: 4, name: 'James Wilson', email: 'jwilson@email.com', phone: '614-555-0104', score: 72, tier: 'lukewarm', source: 'instagram', signals: ['looking for a house', 'dublin'] },
  { id: 5, name: 'Emily Davis', email: 'emily.d@email.com', phone: '614-555-0105', score: 65, tier: 'lukewarm', source: 'facebook', signals: ['down payment', 'saving for a house'] },
  { id: 6, name: 'Robert Brown', email: 'rbrown@email.com', phone: '614-555-0106', score: 55, tier: 'lukewarm', source: 'manual', signals: ['investment property'] },
  { id: 7, name: 'Lisa Garcia', email: 'lisa.g@email.com', phone: '614-555-0107', score: 45, tier: 'lukewarm', source: 'instagram', signals: ['relocating', 'columbus'] },
  { id: 8, name: 'John Smith', email: 'john.s@email.com', phone: '614-555-0108', score: 20, tier: 'cold', source: 'facebook', signals: ['ohio'] },
  { id: 9, name: 'David Martinez', email: 'david.m@email.com', phone: '614-555-0109', score: -100, tier: 'negative', source: 'instagram', signals: ['as a realtor'] },
]

function App() {
  const [leads, setLeads] = useState(SAMPLE_LEADS)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  // Calculate stats from leads
  useEffect(() => {
    const newStats = {
      total: leads.length,
      hot: leads.filter(l => l.tier === 'hot').length,
      warm: leads.filter(l => l.tier === 'warm').length,
      lukewarm: leads.filter(l => l.tier === 'lukewarm').length,
      cold: leads.filter(l => l.tier === 'cold').length,
      negative: leads.filter(l => l.tier === 'negative').length,
    }
    setStats(newStats)
  }, [leads])

  // Try to fetch from API
  useEffect(() => {
    const fetchLeads = async () => {
      try {
        const response = await fetch('/api/leads')
        if (response.ok) {
          const data = await response.json()
          if (data.leads && data.leads.length > 0) {
            setLeads(data.leads)
          }
        }
      } catch (e) {
        // API not available, use sample data
        console.log('Using sample data (API not available)')
      }
    }
    fetchLeads()
  }, [])

  // Filter leads
  const filteredLeads = leads.filter(lead => {
    // Tier filter
    if (filter !== 'all' && lead.tier !== filter) return false

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase()
      const matchesName = lead.name?.toLowerCase().includes(searchLower)
      const matchesEmail = lead.email?.toLowerCase().includes(searchLower)
      const matchesPhone = lead.phone?.includes(search)
      const matchesSignals = lead.signals?.some(s => s.toLowerCase().includes(searchLower))
      if (!matchesName && !matchesEmail && !matchesPhone && !matchesSignals) return false
    }

    return true
  })

  return (
    <div className="app">
      <header className="header">
        <h1>TD Lead Engine</h1>
        <div className="header-stats">
          <div className="header-stat">
            <div className="value">{stats?.total || 0}</div>
            <div className="label">Total Leads</div>
          </div>
          <div className="header-stat">
            <div className="value">{stats?.hot || 0}</div>
            <div className="label">Hot</div>
          </div>
          <div className="header-stat">
            <div className="value">{stats?.warm || 0}</div>
            <div className="label">Warm</div>
          </div>
        </div>
      </header>

      <main className="main">
        {/* Stats Grid */}
        <div className="stats-grid">
          <div className="stat-card hot">
            <div className="value">{stats?.hot || 0}</div>
            <div className="label">Hot Leads (150+)</div>
          </div>
          <div className="stat-card warm">
            <div className="value">{stats?.warm || 0}</div>
            <div className="label">Warm Leads (75-149)</div>
          </div>
          <div className="stat-card lukewarm">
            <div className="value">{stats?.lukewarm || 0}</div>
            <div className="label">Lukewarm (25-74)</div>
          </div>
          <div className="stat-card cold">
            <div className="value">{stats?.cold || 0}</div>
            <div className="label">Cold (&lt;25)</div>
          </div>
        </div>

        {/* Filters */}
        <div className="filters">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`filter-btn ${filter === 'hot' ? 'active' : ''}`}
            onClick={() => setFilter('hot')}
          >
            Hot
          </button>
          <button
            className={`filter-btn ${filter === 'warm' ? 'active' : ''}`}
            onClick={() => setFilter('warm')}
          >
            Warm
          </button>
          <button
            className={`filter-btn ${filter === 'lukewarm' ? 'active' : ''}`}
            onClick={() => setFilter('lukewarm')}
          >
            Lukewarm
          </button>
          <button
            className={`filter-btn ${filter === 'cold' ? 'active' : ''}`}
            onClick={() => setFilter('cold')}
          >
            Cold
          </button>
          <input
            type="text"
            className="search-input"
            placeholder="Search leads..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Leads Table */}
        {loading ? (
          <div className="loading">
            <div className="spinner"></div>
            <p>Loading leads...</p>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="empty-state">
            <h3>No leads found</h3>
            <p>Try adjusting your filters or import some leads.</p>
          </div>
        ) : (
          <div className="leads-table">
            <table>
              <thead>
                <tr>
                  <th>Score</th>
                  <th>Tier</th>
                  <th>Contact</th>
                  <th>Signals</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <span className={`score-badge ${lead.tier}`}>
                        {lead.score}
                      </span>
                    </td>
                    <td>
                      <span className={`tier-badge ${lead.tier}`}>
                        {lead.tier}
                      </span>
                    </td>
                    <td>
                      <div className="contact-info">
                        <div className="name">{lead.name || 'Unknown'}</div>
                        <div className="secondary">
                          {lead.email || lead.phone || 'No contact'}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="signals">
                        {lead.signals?.map((signal, i) => (
                          <span key={i} className="signal-tag">{signal}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <span className="source-badge">{lead.source}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
