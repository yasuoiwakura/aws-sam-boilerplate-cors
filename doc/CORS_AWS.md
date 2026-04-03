# CORS on AWS API Gateway

## The Problem

When a frontend hosted on a different origin calls an API Gateway endpoint, the browser enforces CORS (Cross-Origin Resource Sharing). If CORS headers are missing, the request is blocked — even if the backend works correctly.

## When Does CORS Matter?

CORS only applies when frontend and backend are on different origins (domain, port, or protocol).

### CORS applies
- **Local file** (`file://frontend.htm`) — browsers send no `Origin` header, CORS always fails
- **Local dev** — frontend on `localhost:8080`, API on `*.execute-api.amazonaws.com`
- **Production** — CloudFront CDN (`app.example.com`) → API Gateway (`*.execute-api.amazonaws.com`)

### CORS does NOT apply
- **Full-stack local** — frontend and backend on same origin
- **Docker stack** — single domain, reverse proxy routes both
- **Private cloud** — reverse proxy handles CORS and domain unification

In the last three cases, the browser sees a single origin and CORS is never triggered.

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
| OPTIONS response is API Gateway managed | **Lambda must still return CORS headers on actual responses** (GET/POST/etc.) when using Lambda proxy integration |
| | Hard to maintain |

---

## Strategy 4: `Cors` + `GatewayResponses` (REST API with error coverage)

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
| **Covers gateway errors** (auth failures, throttling, etc.) | **Lambda MUST return CORS headers on success** — with Lambda proxy integration there is no integration response, so API Gateway cannot inject headers into Lambda responses ([AWS docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html#apigateway-enable-cors-proxy)) |
| Browser sees real error instead of CORS error | `Cors` property only creates OPTIONS method, not headers on GET/POST/etc. |
| Works with any Lambda function | Not truly Lambda-independent |

### Why GatewayResponses matter

If API Gateway returns a 4xx or 5xx error (missing auth, throttling, WAF blocking, malformed request), it **does not include CORS headers** by default. The browser shows a CORS error instead of the actual error, making debugging impossible.

`GatewayResponses` injects CORS headers into all error responses from API Gateway itself.

### Why Lambda still needs CORS headers

With **Lambda proxy integration** (SAM's default), API Gateway passes the Lambda response directly to the client without modification. The [AWS documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html#apigateway-enable-cors-proxy) states:

> *"For a Lambda proxy integration or HTTP proxy integration, your backend is responsible for returning the `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, and `Access-Control-Allow-Headers` headers, because a proxy integration doesn't return an integration response."*

This means:
- `Cors` → handles OPTIONS preflight only
- `GatewayResponses` → handles API Gateway errors only
- **Lambda** → must return CORS headers on every success response

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

| API Type | OPTIONS Preflight | Lambda CORS Headers on Success? | Gateway Errors Covered? |
|----------|-------------------|--------------------------------|------------------------|
| REST API with `Cors` only | Yes (auto-created) | **Yes** — proxy integration passes Lambda response through | No |
| REST API with `Cors` + `GatewayResponses` | Yes (auto-created) | **Yes** — proxy integration passes Lambda response through | Yes |
| REST API with OpenAPI `DefinitionBody` | Yes (manual mock) | **Yes** — proxy integration passes Lambda response through | No |
| REST API with non-proxy integration | Yes | No (API Gateway injects headers) | Configurable via integration responses |
| HTTP API | Yes (automatic) | **No** — API Gateway handles CORS entirely | Yes |

**For REST API with Lambda proxy integration:** there is **no fully Lambda-independent CORS solution**. Lambda must return CORS headers on success. `GatewayResponses` only covers API Gateway-level errors.

**For truly Lambda-independent CORS:** use **HTTP API** (Strategy 5) or REST API with **non-proxy integration** (requires manual response mapping in API Gateway).
