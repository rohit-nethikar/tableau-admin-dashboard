#!/usr/bin/env python3
"""Test BigQuery query speed on the view."""
import os
import time
from google.cloud import bigquery
from google.oauth2 import service_account

BQ_PROJECT = "ml-mps-app-mcs-df-app-p-72d7"
BQ_DATASET = "phi_team_interactivedbs_us_p"
BQ_VIEW = "V_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP"
BQ_VIEW_ID = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_VIEW}"

creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
credentials = service_account.Credentials.from_service_account_file(creds_path)
client = bigquery.Client(credentials=credentials, project=BQ_PROJECT)

EMAIL_COLUMN = "USERNAME"
ACCOUNT_NUMBER_COLUMN = "CLIENT_ACCOUNT_NUMBER"

print("Testing BigQuery query speed...")
print("=" * 80)

query = f"""
SELECT DISTINCT {EMAIL_COLUMN}, {ACCOUNT_NUMBER_COLUMN}
FROM `{BQ_VIEW_ID}`
WHERE {EMAIL_COLUMN} IS NOT NULL
  AND {ACCOUNT_NUMBER_COLUMN} IS NOT NULL
"""

print(f"Query:\n{query}\n")

print("Starting query...")
start_time = time.time()

try:
    query_job = client.query(query)
    print(f"Query job created: {query_job.job_id}")

    print("Waiting for results...")
    results = query_job.result(timeout=600)  # 10 minutes

    elapsed = time.time() - start_time
    print(f"Query completed in {elapsed:.1f} seconds")
    print(f"Total rows returned: {results.total_rows}")

    # Count distinct values
    count = 0
    for row in results:
        count += 1

    print(f"Processed {count} rows")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"Error after {elapsed:.1f} seconds: {e}")
    import traceback
    traceback.print_exc()
