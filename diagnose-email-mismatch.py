#!/usr/bin/env python3
"""Diagnose why BigQuery emails aren't matching local database emails."""
import os
import sqlite3
from google.cloud import bigquery
from google.oauth2 import service_account

BQ_PROJECT = "ml-mps-app-mcs-df-app-p-72d7"
BQ_DATASET = "phi_team_interactivedbs_us_p"
BQ_TABLE = "T_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP"
BQ_TABLE_ID = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

# Get BigQuery data
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
credentials = service_account.Credentials.from_service_account_file(creds_path)
client = bigquery.Client(credentials=credentials, project=BQ_PROJECT)

query = f"""
SELECT DISTINCT USERNAME, CLIENT_ACCOUNT_NUMBER
FROM `{BQ_TABLE_ID}`
WHERE USERNAME IS NOT NULL AND CLIENT_ACCOUNT_NUMBER IS NOT NULL
"""

print("Fetching BigQuery data...")
bq_results = client.query(query).result()
bq_emails = {}
for row in bq_results:
    email = row.USERNAME.lower().strip()
    account = row.CLIENT_ACCOUNT_NUMBER.strip()
    bq_emails[email] = account

print(f"Found {len(bq_emails)} unique emails in BigQuery")
print("\nSample BigQuery emails:")
for email in list(bq_emails.keys())[:5]:
    print(f"  {email}")

# Get local database emails
print("\n" + "=" * 80)
print("Fetching local database emails...")
conn = sqlite3.connect("instance/cache.db")
cursor = conn.cursor()
cursor.execute("SELECT id, email FROM users WHERE email IS NOT NULL")
db_rows = cursor.fetchall()
db_emails = {row[1].lower().strip(): row[0] for row in db_rows}
conn.close()

print(f"Found {len(db_emails)} unique emails in local database")
print("\nSample database emails:")
for email in list(db_emails.keys())[:5]:
    print(f"  {email}")

# Find matches
print("\n" + "=" * 80)
print("Checking for matches...")
matches = []
for bq_email, account_num in bq_emails.items():
    if bq_email in db_emails:
        matches.append((bq_email, db_emails[bq_email], account_num))

print(f"Found {len(matches)} matching emails")
print("\nMatches:")
for bq_email, user_id, account_num in matches:
    print(f"  BigQuery: {bq_email}")
    print(f"  User ID: {user_id}")
    print(f"  Account: {account_num}")
    print()

# Check for partial matches
print("\n" + "=" * 80)
print("Checking for partial/domain mismatches...")
partial_matches = 0
for bq_email in bq_emails.keys():
    bq_username = bq_email.split("@")[0]
    for db_email in db_emails.keys():
        db_username = db_email.split("@")[0]
        if bq_username == db_username and bq_email != db_email:
            partial_matches += 1
            print(f"  BigQuery: {bq_email}")
            print(f"  Database: {db_email}")
            print(f"  (Same username, different domain)")
            print()
            if partial_matches >= 5:
                break
    if partial_matches >= 5:
        break

if partial_matches == 0:
    print("  No partial matches found")
