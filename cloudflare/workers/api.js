/**
 * TD Realty Ohio - Cloudflare Workers API
 * Handles all backend operations for the CRM
 */

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    try {
      if (path.startsWith('/api/leads')) {
        return await handleLeads(request, env, path);
      } else if (path.startsWith('/api/tasks')) {
        return await handleTasks(request, env, path);
      } else if (path.startsWith('/api/transactions')) {
        return await handleTransactions(request, env, path);
      } else if (path.startsWith('/api/market')) {
        return await handleMarketData(request, env, path);
      } else if (path.startsWith('/api/analytics')) {
        return await handleAnalytics(request, env, path);
      } else if (path === '/api/health') {
        return jsonResponse({ status: 'ok', timestamp: new Date().toISOString() });
      }
      return jsonResponse({ error: 'Not found' }, 404);
    } catch (error) {
      return jsonResponse({ error: error.message }, 500);
    }
  },

  async scheduled(event, env, ctx) {
    if (event.cron === '0 6 * * *') {
      await collectMarketData(env);
    }
  }
};

async function handleLeads(request, env, path) {
  const method = request.method;
  
  if (method === 'GET' && path === '/api/leads') {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const limit = parseInt(url.searchParams.get('limit') || '50');

    let query = 'SELECT * FROM leads WHERE 1=1';
    const params = [];
    if (status) {
      query += ' AND status = ?';
      params.push(status);
    }
    query += ' ORDER BY created_at DESC LIMIT ?';
    params.push(limit);

    const results = await env.DB.prepare(query).bind(...params).all();
    return jsonResponse({ leads: results.results });
  }

  if (method === 'POST' && path === '/api/leads') {
    const data = await request.json();
    const score = calculateLeadScore(data);
    const tier = getLeadTier(score);

    const result = await env.DB.prepare(
      "INSERT INTO leads (first_name, last_name, email, phone, source, lead_type, status, score, tier, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))"
    ).bind(
      data.first_name, data.last_name, data.email, data.phone || '',
      data.source || 'website', data.lead_type || 'buyer', 'new', score, tier, data.notes || ''
    ).run();

    return jsonResponse({ success: true, id: result.meta.last_row_id, score, tier });
  }

  if (method === 'PUT' && path.match(/\/api\/leads\/\d+/)) {
    const id = path.split('/').pop();
    const data = await request.json();

    await env.DB.prepare(
      "UPDATE leads SET status = COALESCE(?, status), notes = COALESCE(?, notes), updated_at = datetime('now') WHERE id = ?"
    ).bind(data.status, data.notes, id).run();

    return jsonResponse({ success: true });
  }

  return jsonResponse({ error: 'Invalid request' }, 400);
}

async function handleTasks(request, env, path) {
  if (request.method === 'GET') {
    const results = await env.DB.prepare(
      "SELECT * FROM tasks WHERE status = 'pending' ORDER BY due_date ASC"
    ).all();
    return jsonResponse({ tasks: results.results });
  }

  if (request.method === 'POST') {
    const data = await request.json();
    const result = await env.DB.prepare(
      "INSERT INTO tasks (title, description, task_type, priority, status, lead_id, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))"
    ).bind(data.title, data.description || '', data.task_type || 'follow_up', data.priority || 'medium', 'pending', data.lead_id || null, data.due_date).run();
    return jsonResponse({ success: true, id: result.meta.last_row_id });
  }

  return jsonResponse({ error: 'Invalid request' }, 400);
}

async function handleTransactions(request, env, path) {
  if (request.method === 'GET') {
    const results = await env.DB.prepare('SELECT * FROM transactions ORDER BY closing_date DESC').all();
    return jsonResponse({ transactions: results.results });
  }

  if (request.method === 'POST') {
    const data = await request.json();
    const commission = data.sale_price * (data.commission_rate || 0.03);
    const result = await env.DB.prepare(
      "INSERT INTO transactions (property_address, city, state, zip, sale_price, transaction_type, status, commission_rate, commission_amount, closing_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))"
    ).bind(data.property_address, data.city, 'OH', data.zip, data.sale_price, data.transaction_type || 'sale', data.status || 'pending', data.commission_rate || 0.03, commission, data.closing_date).run();
    return jsonResponse({ success: true, id: result.meta.last_row_id });
  }

  return jsonResponse({ error: 'Invalid request' }, 400);
}

async function handleMarketData(request, env, path) {
  if (path === '/api/market/summary') {
    const summary = await env.DB.prepare('SELECT * FROM market_trends ORDER BY date DESC LIMIT 1').first();
    return jsonResponse({
      centralOhio: {
        medianPrice: summary?.median_price || 285000,
        avgDaysOnMarket: summary?.avg_dom || 21,
        inventoryMonths: summary?.inventory_months || 1.8,
        priceChangeYoY: summary?.price_change_yoy || 5.2
      }
    });
  }

  if (path === '/api/market/neighborhoods') {
    const results = await env.DB.prepare('SELECT * FROM neighborhood_stats ORDER BY name').all();
    return jsonResponse({ neighborhoods: results.results });
  }

  return jsonResponse({ error: 'Invalid request' }, 400);
}

async function handleAnalytics(request, env, path) {
  if (path === '/api/analytics/dashboard') {
    const today = new Date().toISOString().split('T')[0];
    const monthStart = today.substring(0, 7) + '-01';

    const leads = await env.DB.prepare(
      "SELECT COUNT(*) as total, SUM(CASE WHEN tier = 'hot' THEN 1 ELSE 0 END) as hot, SUM(CASE WHEN tier = 'warm' THEN 1 ELSE 0 END) as warm, SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) as new_leads FROM leads"
    ).first();

    const tasks = await env.DB.prepare(
      "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'pending' AND due_date <= ? THEN 1 ELSE 0 END) as overdue FROM tasks"
    ).bind(today).first();

    const transactions = await env.DB.prepare(
      "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'closed' THEN commission_amount ELSE 0 END) as commission FROM transactions WHERE closing_date >= ?"
    ).bind(monthStart).first();

    return jsonResponse({
      leads: { total: leads.total || 0, hot: leads.hot || 0, warm: leads.warm || 0, new: leads.new_leads || 0 },
      tasks: { total: tasks.total || 0, overdue: tasks.overdue || 0 },
      transactions: { total: transactions.total || 0, commission: transactions.commission || 0 }
    });
  }

  return jsonResponse({ error: 'Invalid request' }, 400);
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

function calculateLeadScore(data) {
  let score = 0;
  const sourceScores = { 'zillow': 30, 'realtor': 25, 'google_ads': 25, 'facebook': 15, 'website': 20, 'referral': 35, 'open_house': 30, 'sign_call': 25 };
  score += sourceScores[data.source] || 10;
  if (data.lead_type === 'seller') score += 20;
  if (data.lead_type === 'buyer') score += 15;
  if (data.preapproved) score += 30;
  const timelineScores = { 'immediately': 40, 'within_30_days': 30, 'within_90_days': 20, 'within_6_months': 10 };
  score += timelineScores[data.timeline] || 0;
  if (data.working_with_agent === false) score += 20;
  return Math.min(score, 200);
}

function getLeadTier(score) {
  if (score >= 150) return 'hot';
  if (score >= 75) return 'warm';
  if (score >= 25) return 'lukewarm';
  return 'cold';
}

async function collectMarketData(env) {
  console.log('Collecting market data...');
}
