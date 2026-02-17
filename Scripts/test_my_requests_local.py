#!/usr/bin/env python3
"""
Test get_requests_by_status method locally
"""

import sys
sys.path.insert(0, 'Projects/FinanceBot')

from sheets import SheetsManager
import config

print("Initializing SheetsManager...")
try:
    sheets = SheetsManager()
    print("✅ Connected to Google Sheets")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    sys.exit(1)

print("\nTesting get_requests_by_status...")
try:
    created = sheets.get_requests_by_status(config.STATUS_CREATED)
    paid = sheets.get_requests_by_status(config.STATUS_PAID)

    print(f"\n📋 Found {len(created)} CREATED requests")
    print(f"💚 Found {len(paid)} PAID requests")

    if created:
        print("\nSample CREATED request:")
        req = created[0]
        print(f"  Date: {req.get('date')}")
        print(f"  Amount: {req.get('amount')} (type: {type(req.get('amount'))})")
        print(f"  Currency: {req.get('currency')}")
        print(f"  Sheet: {req.get('sheet_name')}")
        print(f"  Purpose: {req.get('purpose')[:50]}...")

    if paid:
        print("\nSample PAID request:")
        req = paid[0]
        print(f"  Date: {req.get('date')}")
        print(f"  Amount: {req.get('amount')} (type: {type(req.get('amount'))})")
        print(f"  Currency: {req.get('currency')}")
        print(f"  Sheet: {req.get('sheet_name')}")
        print(f"  Executor: {req.get('executor')}")

    print("\n✅ Test passed!")

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
