#!/usr/bin/env python3
"""Inspect BigQuery table structure and sample data."""
import os
from google.cloud import bigquery
from google.oauth2 import service_account

BQ_PROJECT = "ml-mps-app-mcs-df-app-p-72d7"
BQ_DATASET = "phi_team_interactivedbs_us_p"
BQ_TABLE = "T_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP"
BQ_TABLE_ID = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
credentials = service_account.Credentials.from_service_account_file(creds_path)
client = bigquery.Client(credentials=credentials, project=BQ_PROJECT)

print("=" * 80)
print(f"Inspecting BigQuery Table: {BQ_TABLE_ID}")
print("=" * 80)

# Get table schema
print("\n1. TABLE SCHEMA (Column Names & Types):")
print("-" * 80)
table = client.get_table(BQ_TABLE_ID)
for field in table.schema:
    print(f"  {field.name:40} {field.field_type}")

# Get sample data
print("\n2. SAMPLE DATA (First 10 rows):")
print("-" * 80)
query = f"SELECT * FROM `{BQ_TABLE_ID}` LIMIT 10"
results = client.query(query).result()

if results.total_rows == 0:
    print("  [No data found in table]")
else:
    # Print header
    column_names = [field.name for field in table.schema]
    print("  " + " | ".join(f"{name:20}" for name in column_names))
    print("  " + "-" * (len(" | ".join(f"{name:20}" for name in column_names))))

    # Print rows
    for row in results:
        print("  " + " | ".join(f"{str(row[col])[:20]:20}" for col in column_names))

# Count rows
print("\n3. TABLE STATISTICS:")
print("-" * 80)
query_count = f"SELECT COUNT(*) as total_rows FROM `{BQ_TABLE_ID}`"
count_result = client.query(query_count).result()
for row in count_result:
    print(f"  Total rows: {row.total_rows}")

print("\n" + "=" * 80)
