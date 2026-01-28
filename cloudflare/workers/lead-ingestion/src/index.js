/**
 * Cloudflare Worker for lead ingestion.
 * Forwards validated requests to the origin API with edge rate limiting.
 */

const ORIGIN_API = 'https://leads.tdrealtyohio.com';

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    const url = new URL(request.url);
    if (url.pathname !== '/v1/leads/ingest') {
      return new Response('Not found', { status: 404 });
    }

    // Validate auth headers exist
    const signature = request.headers.get('X-TD-Signature');
    const secret = request.headers.get('X-TD-Secret');
    if (!signature && !secret) {
      return Response.json(
        { success: false, error: 'auth_error', detail: 'Missing authentication' },
        { status: 401 }
      );
    }

    // Rate limiting via KV
    const clientIP = request.headers.get('CF-Connecting-IP');
    const rateLimitKey = `rate:${clientIP}`;
    const currentCount = parseInt(await env.RATE_LIMIT.get(rateLimitKey) || '0');

    if (currentCount >= 100) {
      return Response.json(
        { success: false, error: 'rate_limit', detail: 'Rate limit exceeded', retry_after: 60 },
        { status: 429 }
      );
    }

    await env.RATE_LIMIT.put(rateLimitKey, String(currentCount + 1), { expirationTtl: 60 });

    // Forward to origin
    const originResponse = await fetch(`${ORIGIN_API}/v1/leads/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-TD-Signature': signature || '',
        'X-TD-Secret': secret || '',
        'X-Forwarded-For': clientIP,
      },
      body: request.body,
    });

    return originResponse;
  },
};

function handleCORS() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-TD-Signature, X-TD-Secret',
      'Access-Control-Max-Age': '86400',
    },
  });
}
