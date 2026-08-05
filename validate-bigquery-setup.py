#!/usr/bin/env python3
"""Validate BigQuery setup and credentials."""
import os
import sys
import json

print("=" * 60)
print("BigQuery Setup Validation")
print("=" * 60)

# Check 1: Environment variable is set
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
print(f"\n✓ GOOGLE_APPLICATION_CREDENTIALS env var: {creds_path}")

if not creds_path:
    print("  ✗ ERROR: Environment variable not set!")
    sys.exit(1)

# Check 2: Credentials file exists
print(f"\n✓ Checking if credentials file exists: {creds_path}")
if not os.path.exists(creds_path):
    print(f"  ✗ ERROR: File not found at {creds_path}")
    sys.exit(1)

print("  ✓ File exists!")

# Check 3: Validate JSON format
print(f"\n✓ Validating JSON format...")
try:
    with open(creds_path, 'r') as f:
        creds = json.load(f)
    print("  ✓ Valid JSON!")
    print(f"  ✓ Service account: {creds.get('client_email', 'N/A')}")
    print(f"  ✓ Project ID: {creds.get('project_id', 'N/A')}")
except json.JSONDecodeError as e:
    print(f"  ✗ ERROR: Invalid JSON - {e}")
    sys.exit(1)

# Check 4: Try to import BigQuery library
print(f"\n✓ Checking if google-cloud-bigquery is installed...")
try:
    import google.cloud.bigquery as bigquery
    print("  ✓ Library installed!")
except ImportError:
    print("  ✗ ERROR: google-cloud-bigquery not installed")
    print("  Run: pip install google-cloud-bigquery")
    sys.exit(1)

# Check 5: Try to create BigQuery client
print(f"\n✓ Testing BigQuery client connection...")
try:
    from google.oauth2 import service_account
    credentials = service_account.Credentials.from_service_account_file(creds_path)
    client = bigquery.Client(credentials=credentials, project=creds.get("project_id"))
    print("  ✓ BigQuery client created successfully!")
    print(f"  ✓ Connected to project: {client.project}")
except Exception as e:
    print(f"  ✗ ERROR: Failed to create BigQuery client - {e}")
    sys.exit(1)

# Check 6: Try to query the target table
print(f"\n✓ Testing query to BigQuery table...")
try:
    BQ_TABLE_ID = "ml-mps-app-mcs-df-app-p-72d7.phi_team_interactivedbs_us_p.T_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP"
    query = f"SELECT COUNT(*) as record_count FROM `{BQ_TABLE_ID}` LIMIT 1"
    query_job = client.query(query)
    results = query_job.result()
    for row in results:
        print(f"  ✓ Table query successful!")
        print(f"  ✓ Records in table: {row.record_count}")
except Exception as e:
    print(f"  ✗ ERROR: Failed to query table - {e}")
    print(f"  Note: This could be a permissions issue or table name issue")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All validation checks passed!")
print("=" * 60)
print("\nYou can now run the BigQuery sync endpoint:")
print("  POST http://localhost:5000/custom-views/sync-bigquery-account-numbers")
