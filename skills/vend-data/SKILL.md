---
name: vend-data
description: >
  Call Vend's paid web-content endpoints — extract a page's clean text,
  search the web, check a link, geolocate an IP, or pull domain intelligence —
  settled instantly in Nano (XNO) via HTTP 402 x402-v2, with no API key and no
  signup. Use when an agent needs web data without maintaining its own scraper,
  API keys, or shared IP footprint. Run --dry-run to see the exact price first.
license: Apache-2.0
compatibility: Python 3.8+, network access
metadata:
  version: "1.0.0"
  author: "Vend API Merchant"
  last-updated: "2026-09-21"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# Vend Data

## Overview

Vend is a pay-per-call API merchant whose endpoints return clean web data as
JSON: extract a page's readable text, run a web search, check a link's status,
geolocate an IP, or pull WHOIS/DNS/SSL intelligence for a domain. Payment is
settled instantly in Nano (XNO) through a standard HTTP 402 x402-v2 challenge —
**no API key, no signup, no per-call gas**. `--dry-run` shows the exact price
of a call without paying anything.

## When to Use

- User asks to "extract", "read", or "summarize" the content of a web page
- User asks for current web search results ("what's the latest on X")
- User asks whether a URL is up, its status code, or response time
- User asks to geolocate an IP address (country, city, ISP, ASN)
- User asks about a domain's DNS, WHOIS, SSL/TLS, or HTTP headers
- You need web data but want to avoid maintaining a scraper or a key

## Prerequisites

- Python 3.8+ with `requests` (`pip install requests`)
- A Nano (XNO) wallet that can send a payment (only needed for real, non-dry-run called)

## Quick Steps

### 1. See what a call costs, without paying (recommended first)

```bash
python3 scripts/vend_data.py --dry-run extract --url https://example.com
python3 scripts/vend_data.py --dry-run search --query "Nano XNO"
```

Dry-run prints the endpoint, its `price_xno`, and the settlement network — it
never sends a payment.

### 2. Extract a page's clean text

```bash
python3 scripts/vend_data.py extract --url https://example.com
```

### 3. Web search

```bash
python3 scripts/vend_data.py search --query "latest Nano news" --limit 5
```

### 4. Other endpoints

```bash
python3 scripts/vend_data.py check-link --url https://example.com   # status, timing, redirects
python3 scripts/vend_data.py geoip --ip 8.8.8.8                     # country, city, ISP, ASN
python3 scripts/vend_data.py domain-info --domain example.com        # DNS, WHOIS, SSL/TLS, headers
```

### 5. Parse dry-run output

```json
{
  "status": "dry_run",
  "endpoint": "extract",
  "price_xno": 0.0001,
  "pay_network": "nano:mainnet",
  "note": "Dry-run only — nothing was paid. Run without --dry-run with a Nano wallet to settle."
}
```

## How Payment Works

Each endpoint is served over x402 v2. Calling it unpaid returns **HTTP 402**
with a `PAYMENT-REQUIRED` header and JSON naming the exact Nano account and
amount:

```json
{
  "error": "payment_required",
  "price_xno": 0.0001,
  "pay_to": "nano_1yo6c1t64a...",
  "accepts": [
    {
      "scheme": "exact",
      "network": "nano:mainnet",
      "asset": "XNO",
      "amount": "100000000000000000000000000",
      "payTo": "nano_1yo6c1t64a...",
      "maxTimeoutSeconds": 60
    }
  ]
}
```

The caller sends the exact XNO amount to `pay_to` on `nano:mainnet`, then
retries with the send-block hash in the `X-PAYMENT` header. Settlement is ~1
second, no network fee, no minimum. `--dry-run` shows the price without paying.

## Prices

| Endpoint | Price (XNO) |
|----------|-------------|
| `extract` | 0.0001 |
| `search` | 0.0001 |
| `check-link` | 0.0001 |
| `geoip` | 0.0001 |
| `domain-info` | 0.0005 |

A call's response includes `price_xno` so a caller can budget exactly.

## Edge Cases

- **No wallet available**: use `--dry-run` — it returns the price and the
  settlement instruction without paying. Or use `curl` against the demo/402
  path to confirm the output shape.
- **429 / rate limit**: endpoints are per-call priced; retry with backoff.
- **Blocked/empty page**: `extract` may return a short or empty body for
  JS-heavy pages or ones that block scrapers; `check-link` reports the real
  HTTP status so you know why.
- **Network offline**: `requests` failures return `{status: error}` to stderr
  style JSON and exit 1.

## References

- Docs + full endpoint table: https://extract.paypercall.dev/ (llms.txt at that root)
- OpenAPI spec: https://extract.paypercall.dev/openapi.json
- x402 spec: https://docs.x402.org
