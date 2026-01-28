/**
 * API client for the TD Lead Engine backend.
 *
 * Uses the FastAPI website_api service by default,
 * falls back to the Flask dashboard server.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchLeads(filters = {}) {
  const params = new URLSearchParams();
  if (filters.source) params.append('source', filters.source);
  if (filters.tier) params.append('tier', filters.tier);
  if (filters.status) params.append('status', filters.status);
  if (filters.utm_campaign) params.append('utm_campaign', filters.utm_campaign);
  if (filters.limit) params.append('limit', String(filters.limit));
  if (filters.offset) params.append('offset', String(filters.offset));

  const response = await fetch(`${API_BASE}/v1/leads?${params}`);
  return response.json();
}

export async function fetchLead(id) {
  const response = await fetch(`${API_BASE}/v1/leads/${id}`);
  return response.json();
}

export async function fetchLeadEvents(id) {
  const response = await fetch(`${API_BASE}/v1/leads/${id}/events`);
  return response.json();
}

export async function fetchLeadAttribution(id) {
  const response = await fetch(`${API_BASE}/v1/leads/${id}/attribution`);
  return response.json();
}

export async function updateLeadStatus(id, status) {
  const response = await fetch(`${API_BASE}/v1/leads/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return response.json();
}

export async function addLeadNote(id, note) {
  const response = await fetch(`${API_BASE}/v1/leads/${id}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note }),
  });
  return response.json();
}
