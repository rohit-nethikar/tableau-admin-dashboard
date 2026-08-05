"""BigQuery integration for syncing account numbers from the user account map table."""
import os
import logging
from typing import Dict, List, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
import json

logger = logging.getLogger(__name__)

# BigQuery view details
BQ_PROJECT = "ml-mps-app-mcs-df-app-p-72d7"
BQ_DATASET = "phi_team_interactivedbs_us_p"
BQ_VIEW = "V_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP"
BQ_VIEW_ID = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_VIEW}"

# Column names
EMAIL_COLUMN = "USERNAME"  # Contains email addresses in BigQuery table
ACCOUNT_NUMBER_COLUMN = "CLIENT_ACCOUNT_NUMBER"


def get_bigquery_client() -> Optional[bigquery.Client]:
    """
    Initialize BigQuery client with authentication.
    Tries multiple auth methods:
    1. Service account JSON file via GOOGLE_APPLICATION_CREDENTIALS env var
    2. Application Default Credentials (ADC) - for environments with implicit auth
    """
    try:
        # Method 1: GOOGLE_APPLICATION_CREDENTIALS env var (most common)
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if os.path.exists(credentials_path):
                logger.info(f"Using BigQuery credentials from {credentials_path}")
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                return bigquery.Client(credentials=credentials, project=BQ_PROJECT)

        # Method 2: Application Default Credentials
        logger.info("Using Application Default Credentials for BigQuery")
        return bigquery.Client(project=BQ_PROJECT)

    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        return None


def fetch_account_numbers_from_bigquery() -> Dict[str, str]:
    """
    Query BigQuery table to fetch email -> account_number mapping.
    Returns a dict: {email: account_number}
    """
    client = get_bigquery_client()
    if not client:
        logger.error("BigQuery client not initialized")
        return {}

    try:
        query = f"""
        SELECT DISTINCT {EMAIL_COLUMN}, {ACCOUNT_NUMBER_COLUMN}
        FROM `{BQ_VIEW_ID}`
        WHERE {EMAIL_COLUMN} IS NOT NULL
          AND {ACCOUNT_NUMBER_COLUMN} IS NOT NULL
        """

        logger.info(f"Querying BigQuery view: {query}")
        query_job = client.query(query, job_config=bigquery.QueryJobConfig(use_query_cache=False))
        print(f"Query job ID: {query_job.job_id}")

        results = query_job.result(timeout=300)  # 5 minute timeout
        print(f"Query returned {results.total_rows} rows")

        account_map = {}
        row_count = 0
        for row in results:
            row_count += 1
            try:
                # Access BigQuery Row by attribute name
                email = getattr(row, EMAIL_COLUMN, "").lower().strip()
                account_number = getattr(row, ACCOUNT_NUMBER_COLUMN, "").strip()
                if email and account_number:
                    account_map[email] = account_number
            except Exception as row_err:
                logger.debug(f"Error processing row {row_count}: {row_err}")

            if row_count % 100000 == 0:
                logger.info(f"Processed {row_count} rows, found {len(account_map)} unique mappings so far")
                print(f"Progress: {row_count} rows processed, {len(account_map)} mappings found")

        logger.info(f"Fetched {len(account_map)} account mappings from BigQuery (processed {row_count} rows)")
        print(f"Total mappings: {len(account_map)}")
        return account_map

    except Exception as e:
        logger.error(f"Error querying BigQuery: {e}")
        import traceback
        traceback.print_exc()
        return {}


def sync_account_numbers_to_database(db_module) -> Dict[str, any]:
    """
    Sync account numbers from BigQuery to local SQLite database.
    Returns a dict with sync statistics.
    """
    updated_count = 0
    skipped_count = 0

    try:
        with db_module.get_conn() as conn:
            # Get all local users with emails
            logger.info("Fetching local users...")
            local_users = conn.execute(
                "SELECT id, LOWER(email) as email_lower FROM users WHERE email IS NOT NULL"
            ).fetchall()
            local_user_map = {row[1]: row[0] for row in local_users}
            logger.info(f"Found {len(local_user_map)} local users")

            # Fetch BigQuery data
            logger.info("Fetching account mappings from BigQuery...")
            account_map = fetch_account_numbers_from_bigquery()

            if not account_map:
                logger.warning("No account mappings fetched from BigQuery")
                return {
                    "status": "error",
                    "message": "No account mappings found in BigQuery",
                    "updated_count": 0,
                    "skipped_count": 0
                }

            logger.info(f"Fetched {len(account_map)} mappings from BigQuery")

            # Match and update
            logger.info("Matching and updating...")
            for email, account_number in account_map.items():
                email_lower = email.lower().strip()
                if email_lower in local_user_map:
                    user_id = local_user_map[email_lower]
                    conn.execute(
                        "UPDATE users SET account_number = ? WHERE id = ?",
                        (account_number, user_id)
                    )
                    updated_count += 1
                else:
                    skipped_count += 1

            conn.commit()

        logger.info(f"Sync complete: {updated_count} updated, {skipped_count} skipped")
        return {
            "status": "success",
            "message": f"Synced {updated_count} account numbers from BigQuery",
            "updated_count": updated_count,
            "skipped_count": skipped_count
        }

    except Exception as e:
        logger.error(f"Error syncing to database: {e}")
        return {
            "status": "error",
            "message": f"Database sync failed: {str(e)}",
            "updated_count": updated_count,
            "skipped_count": skipped_count
        }
