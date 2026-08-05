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
    serve(app, host=settings.host, port=settings.port)

except Exception as e:
    print(f"\nERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
