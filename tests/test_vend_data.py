#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2026 Fetch.ai
#
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
Unit tests for the vend-data skill — no API credentials or network needed.

Tests the CLI contract: endpoint availability, price mapping, and the
x402 header decoder in isolation.

Run with:
    python3 tests/test_vend_data.py
    python3 -m pytest tests/test_vend_data.py -v
"""

import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "vend-data", "scripts"),
)

_SPEC = importlib.util.spec_from_file_location(
    "vend_data",
    os.path.join(
        os.path.dirname(__file__), "..", "skills", "vend-data", "scripts", "vend_data.py"
    ),
)
_vend_data = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_vend_data)


class TestEndpointTable(unittest.TestCase):
    """Every advertised endpoint must have a method, a path framg, and a price."""

    def test_all_endpoints_have_prices(self):
        for ep in _vend_data.ENDPOINTS:
            self.assertIn(ep, _vend_data.PRICES)

    def test_prices_are_positive(self):
        for ep, price in _vend_data.PRICES.items():
            self.assertGreater(price, 0)

    def test_domain_costs_more_than_basic(self):
        self.assertGreater(_vend_data.PRICES["domain-info"], _vend_data.PRICES["extract"])


class TestDryRunFlag(unittest.TestCase):
    """dry-run must never claim a payment was made."""

    def test_dry_run_note(self):
        for ep in _vend_data.ENDPOINTS:
            result = {
                "status": "dry_run",
                "endpoint": ep,
                "price_xno": _vend_data.PRICES.get(ep),
            }
            self.assertEqual(result["status"], "dry_run")
            self.assertNotIn("payment", json.dumps(result).lower().replace("payment_required", ""))


class TestPaymentHeaderDecoder(unittest.TestCase):
    """The x402 PAYMENT-REQUIRED header decoder returns JSON or {} on garbage."""

    def test_round_trip(self):
        import base64

        payload = {"accepts": []}
        raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        decoded = _vend_data.decode_payment_header(raw)
        self.assertEqual(decoded, payload)

    def test_garbage_returns_empty(self):
        self.assertEqual(_vend_data.decode_payment_header("not-a-valid-header"), {})

    def test_empty_returns_empty(self):
        self.assertEqual(_vend_data.decode_payment_header(""), {})


if __name__ == "__main__":
    unittest.main()
