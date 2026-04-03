# HTTP API — CORS Handled by API Gateway

CORS is configured entirely in the SAM template. The Lambda function returns **zero** CORS headers.

## Architecture

```
Browser ──CORS headers injected──▶ API Gateway (HTTP API) ──▶ Lambda (clean, no CORS)
         ◀────────────────────────────────────────────────────◀
```

## Quick Start

### Deploy

```bash
sam deploy --guided
```

### Test

Serve the frontend over HTTP (required for CORS):

```bash
cd frontend
python -m http.server 8080
```

Open `http://localhost:8080/frontend.htm` — the test suite runs automatically.

### Local Testing

```bash
# Terminal 1 — API + Lambda
sam local start-api

# Terminal 2 — Frontend
cd frontend
python -m http.server 8080
```

Update `BASE_URL` in `frontend.htm` to `http://127.0.0.1:3000`.

## Test Scenarios

| # | Test | URL | Status | Responds | CORS |
|---|------|-----|--------|----------|------|
| 1 | 200 OK | `/api` | 200 | Lambda | API Gateway injects |
| 2 | Lambda Exception | `/api?except=true` | 500 | API Gateway | API Gateway injects |
| 3 | Lambda 500 | `/api?status=500` | 500 | Lambda | API Gateway injects |
| 4 | 404 Route | `/wrongpath` | 404 | API Gateway | **Not sent** (see Limitations) |
| 5 | Lambda Timeout | `/api?timeout=true` | 503 | API Gateway | API Gateway injects |

## Known Limitation: 404 Responses

HTTP API does **not** send CORS headers on 404 responses for unknown routes. This is a platform limitation — unlike REST API, HTTP API has no `GatewayResponses` customization.

If your frontend calls a wrong path, the browser will show a CORS error instead of the 404. The 404 status is still visible in the browser console.

**Mitigation:** Ensure correct paths in your frontend. For production, consider a catch-all route (`/{proxy+}`) that returns a proper 404 from Lambda with CORS headers — but this trades off the ability to test API Gateway 404 behavior.

## File Structure

```
http-api-cors/
├── README.md
├── template.yaml
├── backend/
│   └── app.py
└── frontend/
    └── frontend.htm
```

See [../../doc/CORS_AWS.md](../../doc/CORS_AWS.md) for a comprehensive overview of CORS strategies on AWS.
