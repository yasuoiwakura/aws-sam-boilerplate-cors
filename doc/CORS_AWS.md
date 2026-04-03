# CORS on AWS API Gateway

## The Problem

When a frontend hosted on a different origin calls an API Gateway endpoint, the browser enforces CORS (Cross-Origin Resource Sharing). If CORS headers are missing, the request is blocked — even if the backend works correctly.

## How CORS Works on API Gateway

There are **two types** of CORS requests:

- **Simple requests** — GET, HEAD, POST with standard content types. Browser sends the request and checks response headers.
- **Preflight requests** — For PUT, DELETE, custom headers, or `application/json`. Browser sends an `OPTIONS` request first to check if the actual request is allowed.

Both the preflight response **and** the actual response must include `Access-Control-Allow-Origin`.

## Where CORS Headers Must Be Present

CORS headers must exist in **three places**:

| Location | Purpose |
|----------|---------|
| OPTIONS method response | Handles preflight check |
| Actual method response (GET/POST/etc.) | Browser checks response headers |
| Gateway error responses (4xx/5xx) | Auth failures, throttling, WAF blocks |

Missing any one of these causes a CORS error in the browser.

---

## Strategy 1: `Globals.Api.Cors` (SAM shorthand)

```yaml
Globals:
  Api:
    Cors:
      AllowOrigin: "'*'"
      AllowHeaders: "'Content-Type,Authorization'"
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
```

| Pros | Cons |
|------|------|
| Simple, minimal config | CORS headers only on OPTIONS, **not on actual responses** |
| SAM auto-creates OPTIONS methods | **Does NOT cover 4xx/5xx errors** from API Gateway |
| No Lambda changes needed | Requires Lambda to still return CORS headers on success |

---

## Strategy 2: `AWS::Serverless::Api.Cors` property

```yaml
Api:
  Type: AWS::Serverless::Api
  Properties:
    StageName: Prod
    Cors:
      AllowOrigin: "'*'"
      AllowHeaders: "'Content-Type,Authorization'"
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
```

| Pros | Cons |
|------|------|
| Clean, SAM-native | Same problem: CORS only on OPTIONS preflight |
| Works with `RestApiId` references | **Lambda must still return CORS headers** on every response |
| | **No CORS on gateway errors** (4xx/5xx) |

---

## Strategy 3: OpenAPI `DefinitionBody` with inline OPTIONS mock

Define the OPTIONS method explicitly in the OpenAPI spec with a MOCK integration that returns CORS headers.

| Pros | Cons |
|------|------|
| Full control over every method | Complex, verbose |
| OPTIONS mock integration defined explicitly | **Still doesn't cover gateway errors** |
| Lambda stays clean | Hard to maintain |

---

## Strategy 4: `Cors` + `GatewayResponses` (Recommended for REST API)

```yaml
Api:
  Type: AWS::Serverless::Api
  Properties:
    StageName: Prod
    Cors:
      AllowOrigin: "'*'"
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowHeaders: "'Content-Type,Authorization'"
    GatewayResponses:
      DEFAULT_4XX:
        ResponseParameters:
          Headers:
            Access-Control-Allow-Origin: "'*'"
            Access-Control-Allow-Headers: "'Content-Type,Authorization'"
      DEFAULT_5XX:
        ResponseParameters:
          Headers:
            Access-Control-Allow-Origin: "'*'"
            Access-Control-Allow-Headers: "'Content-Type,Authorization'"
```

| Pros | Cons |
|------|------|
| **Covers gateway errors** (auth failures, throttling, etc.) | Lambda must still return CORS headers on success (for REST API with proxy integration) |
| Browser sees real error instead of CORS error | |
| Works with any Lambda function | |

### Why GatewayResponses matter

If API Gateway returns a 4xx or 5xx error (missing auth, throttling, WAF blocking, malformed request), it **does not include CORS headers** by default. The browser shows a CORS error instead of the actual error, making debugging impossible.

`GatewayResponses` injects CORS headers into all error responses from API Gateway itself.

---

## Strategy 5: HTTP API (Simplest overall)

```yaml
Api:
  Type: AWS::Serverless::HttpApi
  Properties:
    CorsConfiguration:
      AllowOrigins: ["*"]
      AllowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      AllowHeaders: ["Content-Type", "Authorization"]
```

| Pros | Cons |
|------|------|
| **CORS is fully automatic** — no OPTIONS method needed | Different API type (HTTP API vs REST API) |
| CORS headers on **all responses** including errors | Fewer features than REST API (no API keys, usage plans, request validation) |
| **Lambda stays completely clean** — no CORS headers needed | |
| Cheaper and faster than REST API | |

---

## Multiple Origins

REST APIs don't natively support multiple origins — `Access-Control-Allow-Origin` only accepts a single value or `*`. To support multiple specific origins, you must check the request's `Origin` header dynamically:

```python
ALLOWED_ORIGINS = [
    "https://app.example.com",
    "https://staging.example.com",
    "http://localhost:3000",
]

origin = event.get("headers", {}).get("origin", "")
cors_origin = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
```

---

## Common CORS Mistakes

1. **Missing headers on actual response** — OPTIONS preflight works, but GET/POST response doesn't include `Access-Control-Allow-Origin`. Browser blocks it.
2. **Wildcard with credentials** — `Access-Control-Allow-Origin: *` with cookies/auth headers is rejected. Must specify exact origin.
3. **Missing Content-Type in allowed headers** — If frontend sends `Content-Type: application/json`, it must be in `Access-Control-Allow-Headers`.
4. **Forgetting to deploy** — REST API changes require redeployment. CORS config sits idle until deployed.
5. **API Gateway errors bypass CORS** — 4xx/5xx from API Gateway don't include CORS headers without `GatewayResponses`.

---

## Debugging

```bash
# Test OPTIONS preflight directly
curl -v -X OPTIONS \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://abc123.execute-api.us-east-1.amazonaws.com/Prod/

# Test actual request
curl -v -X GET \
  -H "Origin: https://app.example.com" \
  https://abc123.execute-api.us-east-1.amazonaws.com/Prod/

# Look for Access-Control-Allow-Origin in BOTH responses
```

---

## Key Takeaway

| API Type | CORS Effort | Lambda CORS Headers Needed? | Gateway Errors Covered? |
|----------|-------------|----------------------------|------------------------|
| REST API with `Cors` only | Low | Yes | No |
| REST API with `Cors` + `GatewayResponses` | Medium | Yes | Yes |
| REST API with OpenAPI `DefinitionBody` | High | No (OPTIONS only) | No |
| HTTP API | None | No | Yes |

For REST API: use **Strategy 4** (`Cors` + `GatewayResponses`).
For simplest setup: use **HTTP API** (Strategy 5).
