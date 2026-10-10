#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2026 Fetch.ai
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
vend_data.py — Paid web-content endpoints via Vend (Nano x402), no API key.

Calls live, pay-per-call endpoints: extract a page's clean text, search the
web, check a link, geolocate an IP, or pull domain intelligence. Each call
is settled instantly in Nano (XNO) via HTTP 402 x402-v2; no signup, no key.

Usage:
    python3 vend_data.py extract --url https://example.com
    python3 vend_data.py search --query "Nano XNO"
    python3 vend_data.py check-link --url https://example.com
    python3 vend_data.py geoip --ip 8.8.8.8
    python3 vend_data.py domain-info --domain example.com
    python3 vend_data.py --dry-run extract --url https://example.com

Requirements:
    - requests library (pip install requests)

Modes:
    --dry-run   returns the price and settlement instruction without paying
    default     expected to be run with a Nano wallet that settles the 402

Output:
    JSON to stdout: the endpoint's parsed response, or (dry-run) the 402
    challenge with price_xno.
"""

import argparse
import base64
import json
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print(
        json.dumps({"status": "error", "error": "requests library not installed. Run: pip install requests"}),
        file=sys.stdout,
    )
    sys.exit(1)


BASE = "https://extract.paypercall.dev/api/v1"

# endpoint -> (method, path-fragment). query params are passed through.
ENDPOINTS = {
    "extract": ("GET", "extract", {"url": True}),
    "search": ("GET", "web-search", {"q": True}),
    "check-link": ("GET", "check-link", {"url": True}),
    "geoip": ("GET", "geoip", {"ip": True}),
    "domain-info": ("GET", "domain-info", {"domain": True}),
}

PRICES = {
    "extract": 0.0001,
    "search": 0.0001,
    "check-link": 0.0001,
    "geoip": 0.0001,
    "domain-info": 0.0005,
}


def log(msg: str) -> None:
    """Print log message to stderr."""
    print(f"[vend-data] {msg}", file=sys.stderr)


def decode_payment_header(value: str) -> dict:
    """Decode the x402 PAYMENT-REQUIRED header (base64url JSON)."""
    try:
        padded = value + "=" * (-len(value) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:  # noqa: BLE001
        return {}


def call_endpoint(endpoint: str, **params) -> dict:
    """Call a Vend endpoint, returning the 402 challenge or the settled data."""
    method, frag, required = ENDPOINTS[endpoint]
    url = f"{BASE}/{frag}"

    # repack known params into the URL query for GET endpoints
    if method == "GET" and any(v for k, v in params.items() if v and required.get(k)):
        query = {k: v for k, v in params.items() if v}
        url = requests.Request("GET", url, params=query).prepare().url

    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=30)
    except requests.exceptions.RequestException as e:  # noqa: BLE001
        return {"status": "error", "error": f"Request failed: {e}"}

    if r.status_code == 402:
        header = r.headers.get("payment-required", "")
        challenge = decode_payment_header(header)
        try:
            body = r.json()
        except Exception:  # noqa: BLE001
            body = {}
        return {
            "status": "payment_required",
            "endpoint": endpoint,
            "price_xno": body.get("price_xno"),
            "pay_to": body.get("pay_to"),
            "accepts": body.get("accepts") or challenge.get("accepts"),
            "message": body.get("message"),
            "how_to_pay": (
                "Send the exact XNO amount to pay_to (nano:mainnet), then retry "
                "with the send-block hash in the X-PAYMENT header. RPC: "
                "https://docs.nano.org/integration-guides/key-management/#rpc-endpoints"
            ),
        }

    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        body = r.text
    if r.status_code == 200:
        if isinstance(body, dict):
            body.setdefault("status", "success")
        return body
    return {
        "status": "error",
        "error": f"HTTP {r.status_code}: {str(body)[:300]}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Call Vend's paid web-content endpoints (Nano x402, no API key).",
        epilog="Example: python3 vend_data.py extract --url https://example.com",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the price and settlement instruction without paying",
    )
    sub = parser.add_subparsers(dest="endpoint", required=True, title="endpoint")

    p_extract = sub.add_parser("extract", help="Return clean text/markdown from a web page")
    p_extract.add_argument("--url", required=True)
    p_extract.add_argument("--max-chars", type=int, default=10000)

    p_search = sub.add_parser("search", help="Web search with snippets")
    p_search.add_argument("--query", "-q", required=True)
    p_search.add_argument("--limit", type=int, default=5)

    p_link = sub.add_parser("check-link", help="HTTP status, timing, redirect chain for a URL")
    p_link.add_argument("--url", required=True)

    p_geo = sub.add_parser("geoip", help="Geolocate an IP")
    p_geo.add_argument("--ip", required=True)

    p_dom = sub.add_parser("domain-info", help="DNS/WHOIS/SSL/HTTP-header intelligence for a domain")
    p_dom.add_argument("--domain", required=True)

    args = parser.parse_args()

    # map args back to endpoint params
    params = {}
    ep = args.endpoint
    if ep == "extract":
        params = {"url": args.url, "max_chars": args.max_chars}
    elif ep == "search":
        params = {"q": args.query, "limit": args.limit}
    elif ep in ("check-link",):
        params = {"url": args.url}
    elif ep == "geoip":
        params = {"ip": args.ip}
    elif ep == "domain-info":
        params = {"domain": args.domain}

    result = call_endpoint(ep, **params)

    if args.dry_run:
        # never settle in dry-run; report the price and the means to pay
        result = {
            "status": "dry_run",
            "endpoint": ep,
            "price_xno": PRICES.get(ep),
            "pay_network": "nano:mainnet",
            "note": "Dry-run only — nothing was paid. Run without --dry-run with a Nano wallet to settle.",
        }

    print(json.dumps(result, indent=2))
    ok = result.get("status") in ("success", "dry_run")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
