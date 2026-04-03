# SAM Boilerplate — CORS on AWS API Gateway

This repository documents the problem of CORS on AWS API Gateway and provides working boilerplate for different approaches.

## The Problem

When a browser-based frontend calls an API on a different origin, the browser enforces CORS. API Gateway must include `Access-Control-Allow-Origin` headers on **every** response — success, error, and preflight. Missing CORS headers cause the browser to block the response, even if the backend works correctly.

CORS only matters when frontend and backend have different origins — e.g. local file (`file://`), localhost dev, or CloudFront CDN → API Gateway. Same-origin setups (Docker, reverse proxy) have no CORS problem. See [doc/CORS_AWS.md](doc/CORS_AWS.md) for details.

## HTTP API vs REST API — TL;DR

| | HTTP API | REST API |
|---|----------|----------|
| **CORS config** | `CorsConfiguration` — one block, done | `Cors` property + `GatewayResponses` (for errors) |
| **Lambda needs CORS headers?** | **No** — API Gateway injects them automatically | **Yes** — with Lambda proxy integration, Lambda must return CORS headers on every response |
| **Preflight (OPTIONS)** | Automatic | Auto-created by SAM or manual |
| **CORS on errors (5xx)** | Automatic | Via `GatewayResponses` |
| **CORS on 404 (unknown route)** | **Not sent** — HTTP API limitation | Via `GatewayResponses` |
| **Cost / Latency** | Lower | Higher |

**Bottom line:** HTTP API is the only approach where CORS is **100% API Gateway-side** with zero Lambda changes. REST API with Lambda proxy integration always requires Lambda to return CORS headers on success responses.

## Current Approach: HTTP API

See [`simple-http-api-cors/`](simple-http-api-cors/) for a working boilerplate:

- CORS handled entirely by API Gateway HTTP API
- Lambda returns zero CORS headers
- Frontend test suite verifies CORS on 200, 500, 503, and 404 responses
- Documents the known limitation: HTTP API does not send CORS headers on 404 responses for unknown routes

## Further Reading

- [`doc/CORS_AWS.md`](doc/CORS_AWS.md) — Comprehensive overview of all CORS strategies on AWS API Gateway, including pros/cons, debugging tips, and common pitfalls.

## Additional Resources

TODO examples or CORS relevance
