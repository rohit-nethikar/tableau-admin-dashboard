#!/usr/bin/env python3
"""Simple app runner with better error reporting."""
import sys
import traceback

print("Starting Flask app...")
print(f"Python: {sys.version}")

try:
    print("Step 1: Importing app module...")
    from app import app
    print("  OK")

    print("Step 2: Getting server settings...")
    from config import settings
    print(f"  OK - Server will run on {settings.host}:{settings.port}")

    print("Step 3: Starting Waitress server...")
    from waitress import serve
    # Waitress defaults to a 1 GiB request body cap, which rejects a multi-GB
    # .twbx upload (Workbook Compare) before it ever reaches Flask. Raise it.
    serve(app, host=settings.host, port=settings.port, max_request_body_size=10 * 1024 ** 3)

except Exception as e:
    print(f"\nERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
