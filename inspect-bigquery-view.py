#!/usr/bin/env python3
"""Inspect BigQuery view structure and sample data."""
import os
from google.cloud import bigquery
from google.oauth2 import service_account

BQ_PROJECT = "ml-mps-app-mcs-df-app-p-72d7"
BQ_DATASET = "phi_team_interactivedbs_us_p"
BQ_VIEW = "V_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP"
BQ_VIEW_ID = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_VIEW}"

creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
credentials = service_account.Credentials.from_service_account_file(creds_path)
client = bigquery.Client(credentials=credentials, project=BQ_PROJECT)

print("=" * 80)
print(f"Inspecting BigQuery View: {BQ_VIEW_ID}")
print("=" * 80)

# Get view schema
print("\n1. VIEW SCHEMA (Column Names & Types):")
print("-" * 80)
try:
    table = client.get_table(BQ_VIEW_ID)
    for field in table.schema:
        print(f"  {field.name:40} {field.field_type}")
except Exception as e:
    print(f"  Error: {e}")
    exit(1)

# Get sample data
print("\n2. SAMPLE DATA (First 10 rows):")
print("-" * 80)
query = f"SELECT * FROM `{BQ_VIEW_ID}` LIMIT 10"
results = client.query(query).result()

if results.total_rows == 0:
    print("  [No data found in view]")
else:
    # Get column names
    column_names = [field.name for field in table.schema]

    # Print header
    header = " | ".join(f"{name:25}" for name in column_names)
    print("  " + header)
    print("  " + "-" * len(header))

    # Print rows
    for row in results:
        row_data = " | ".join(f"{str(row[col])[:25]:25}" for col in column_names)
        print("  " + row_data)

# Count rows
print("\n3. VIEW STATISTICS:")
print("-" * 80)
query_count = f"SELECT COUNT(*) as total_rows FROM `{BQ_VIEW_ID}`"
count_result = client.query(query_count).result()
for row in count_result:
    print(f"  Total rows: {row.total_rows}")

print("\n" + "=" * 80)
