# TD Realty Ohio - Website Lead Ingestion API

## Endpoint

- **Production:** `https://leads.tdrealtyohio.com/v1/leads/ingest`
- **Local:** `http://localhost:8000/v1/leads/ingest`

## Authentication

All requests must include one of these headers:

### Option 1: HMAC Signature (Recommended)

```
X-TD-Signature: <HMAC-SHA256 of request body using TD_API_SECRET>
```

```javascript
const crypto = require('crypto');
function signPayload(payload, secret) {
  return crypto.createHmac('sha256', secret).update(JSON.stringify(payload)).digest('hex');
}
```

### Option 2: Shared Secret

```
X-TD-Secret: <your-api-secret>
```

## Request Schema

```json
{
  "lead_id": "optional-uuid",
  "timestamp": "2025-01-28T12:00:00Z",
  "event_name": "contact_submit",
  "source": "website",
  "contact": {
    "email": "john@example.com",
    "phone": "614-555-0100",
    "first_name": "John",
    "last_name": "Doe"
  },
  "event_data": {
    "form_id": "contact-form-hero",
    "page_path": "/sell-your-home",
    "referrer": "https://google.com",
    "message": "I want to sell my house in Powell",
    "calculator_type": "commission_savings",
    "calculator_inputs": { "home_price": 350000 },
    "calculator_result": { "savings": 7000 }
  },
  "attribution": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "columbus-sellers-2025",
    "utm_content": "1percent-commission",
    "utm_term": "sell house columbus",
    "gclid": "abc123",
    "landing_page": "/sell-your-home",
    "referrer_domain": "google.com"
  },
  "session": {
    "session_id": "sess_abc123",
    "device_type": "mobile",
    "browser": "Chrome",
    "city": "Columbus",
    "region": "OH"
  }
}
```

### Required Fields

- At least one of: `contact.email` or `contact.phone`
- `event_name` - one of: `contact_submit`, `calculator_submit`, `home_value_request`, `newsletter_signup`, `schedule_showing`, `schedule_consultation`, `page_view`, `property_inquiry`, `saved_search`, `blog_subscription`

## Responses

### Success (200)

```json
{ "success": true, "lead_id": "uuid", "is_new": true, "message": "Lead ingested successfully" }
```

### Duplicate (200)

```json
{ "success": true, "lead_id": "uuid", "is_new": false, "message": "Event added to existing lead" }
```

### Validation Error (400)

```json
{ "success": false, "error": "validation_error", "detail": "Invalid email format" }
```

### Auth Error (401)

```json
{ "success": false, "error": "auth_error", "detail": "Invalid or missing authentication" }
```

### Rate Limit (429)

```json
{ "success": false, "error": "rate_limit", "detail": "Rate limit exceeded", "retry_after": 60 }
```

## Idempotency

Provide `lead_id` (UUID) client-side for retry safety. Same `lead_id` + same `event_name` = ignored.

## Error Handling & Retry

| Status | Retry? | Action |
|--------|--------|--------|
| 200 | No | Success |
| 400 | No | Fix payload |
| 401 | No | Check auth |
| 429 | Yes | Wait `retry_after` seconds |
| 500 | Yes | Exponential backoff (1s, 2s, 4s, max 3 retries) |

## JavaScript Example

```javascript
async function submitLead(formData) {
  const payload = {
    event_name: 'contact_submit',
    source: 'website',
    contact: {
      email: formData.email,
      phone: formData.phone,
      first_name: formData.firstName,
      last_name: formData.lastName,
    },
    event_data: {
      form_id: formData.formId,
      page_path: window.location.pathname,
      referrer: document.referrer,
      message: formData.message,
    },
    attribution: getUTMParams(),
    session: { session_id: getSessionId(), device_type: getDeviceType() },
  };

  const response = await fetch('/v1/leads/ingest', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-TD-Secret': 'your-api-secret',
    },
    body: JSON.stringify(payload),
  });
  return response.json();
}

function getUTMParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get('utm_source'),
    utm_medium: params.get('utm_medium'),
    utm_campaign: params.get('utm_campaign'),
    utm_content: params.get('utm_content'),
    utm_term: params.get('utm_term'),
    gclid: params.get('gclid'),
    msclkid: params.get('msclkid'),
    fbclid: params.get('fbclid'),
    landing_page: window.location.pathname,
    referrer_domain: document.referrer ? new URL(document.referrer).hostname : null,
  };
}
```

## Rate Limits

- **Per IP:** 100 requests/minute
- **Per API key:** 1000 requests/minute

## Testing

```bash
curl -X POST http://localhost:8000/v1/leads/ingest \
  -H "Content-Type: application/json" \
  -H "X-TD-Secret: test-secret" \
  -d '{"event_name":"contact_submit","contact":{"email":"test@example.com"}}'
```

```bash
curl http://localhost:8000/health
```
