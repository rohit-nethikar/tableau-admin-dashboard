"""BigQuery integration for syncing account numbers from the user account map table."""
import os
import logging
from typing import Dict, List, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
import json

logger = logging.getLogger(__name__)

# Ensure Google credentials are properly set if not already
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    creds_file = os.path.join(os.path.dirname(__file__), "bigquery-credentials.json")
    if os.path.exists(creds_file):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file
        logger.info(f"Set GOOGLE_APPLICATION_CREDENTIALS to {creds_file}")

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
    Updates account numbers for ALL sites that have custom views.
    Also creates placeholder users for custom view owners found in BigQuery
    but not yet in the users table.
    Returns a dict with sync statistics.
    """
    updated_count = 0
    skipped_count = 0
    created_count = 0

    try:
        with db_module.get_conn() as conn:
            # Get all local users with emails (across all sites)
            logger.info("Fetching local users from all sites...")
            local_users = conn.execute(
                "SELECT COUNT(DISTINCT LOWER(email)) as unique_emails FROM users WHERE email IS NOT NULL"
            ).fetchone()
            logger.info(f"Found {local_users[0]} unique email addresses in local users")

            # Get custom view owners (for special handling)
            custom_view_owners = set()
            cv_result = conn.execute(
                "SELECT DISTINCT LOWER(owner_name) FROM custom_views WHERE owner_name IS NOT NULL"
            ).fetchall()
            custom_view_owners = {row[0] for row in cv_result}
            logger.info(f"Found {len(custom_view_owners)} custom view owners")

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

            # Match and update - update ALL users with matching email across all sites
            logger.info("Matching and updating across all sites...")
            print(f"\n=== DEBUGGING: Matching {len(account_map)} BigQuery emails ===\n")

            matched_emails = []
            unmatched_emails = []

            for email, account_number in account_map.items():
                email_lower = email.lower().strip()
                # Check if this email exists in users
                check = conn.execute(
                    "SELECT id FROM users WHERE LOWER(email) = ? LIMIT 1",
                    (email_lower,)
                ).fetchone()

                if check:
                    # Update all users with this email, regardless of site
                    result = conn.execute(
                        "UPDATE users SET account_number = ? WHERE LOWER(email) = ?",
                        (account_number, email_lower)
                    )
                    updated_count += result.rowcount
                    matched_emails.append((email, account_number, result.rowcount))
                    if updated_count <= 10:  # Print first 10 matches
                        print(f"  MATCHED: {email} -> account {account_number} ({result.rowcount} users updated)")
                elif email_lower in custom_view_owners:
                    # Special case: create a placeholder user for custom view owners
                    # Get a list of sites with this custom view owner
                    sites = conn.execute(
                        "SELECT DISTINCT site FROM custom_views WHERE LOWER(owner_name) = ?",
                        (email_lower,)
                    ).fetchall()

                    for (site,) in sites:
                        conn.execute(
                            """INSERT OR IGNORE INTO users
                               (id, site, name, email, site_role, account_number)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (f"cv_owner_{email_lower}_{site}", site, email_lower, email, "SiteRole/Viewer", account_number)
                        )
                        created_count += 1

                    matched_emails.append((email, account_number, len(sites)))
                    if created_count <= 5:
                        print(f"  CREATED: {email} -> account {account_number} (placeholder user in {len(sites)} site(s))")
                else:
                    unmatched_emails.append(email)
                    skipped_count += 1
                    if len(unmatched_emails) <= 5:  # Print first 5 unmatched
                        print(f"  NO MATCH: {email}")

            conn.commit()

            print(f"\n=== SUMMARY ===")
            print(f"Total BQ mappings: {len(account_map)}")
            print(f"Matched to local users: {len([e for e in matched_emails if not e[0].lower() in custom_view_owners])}")
            print(f"Created placeholder users: {created_count}")
            print(f"No match found: {len(unmatched_emails)}")
            print(f"Total users updated/created: {updated_count + created_count}\n")

        logger.info(f"Sync complete: {updated_count} updated, {created_count} created, {skipped_count} skipped")
        return {
            "status": "success",
            "message": f"Synced {updated_count + created_count} account numbers from BigQuery ({created_count} new placeholder users)",
            "updated_count": updated_count + created_count,
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
