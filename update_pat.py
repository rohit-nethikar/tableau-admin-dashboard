#!/usr/bin/env python3
"""Update the PAT credentials in the database without resetting other settings."""
import sys
import getpass

import db
import crypto
import tableau_client
from config import settings

def update_pat():
    print("\n=== Tableau Admin Dashboard - Update PAT ===\n")

    # Get new credentials
    pat_name = input("Enter new PAT name: ").strip()
    if not pat_name:
        print("Error: PAT name is required")
        return False

    pat_secret = getpass.getpass("Enter new PAT secret: ")
    if not pat_secret:
        print("Error: PAT secret is required")
        return False

    # Validate the credentials
    print("\nValidating credentials against Tableau Server...")
    try:
        with tableau_client.signed_in_server(
            settings.server_url,
            settings.default_site,
            pat_name,
            pat_secret
        ):
            print("✓ Credentials validated successfully!")
    except Exception as exc:
        print(f"✗ Error: Could not sign in with these credentials: {exc}")
        return False

    # Update the database
    print("\nUpdating database...")
    try:
        db.set_config("pat_name", pat_name)
        db.set_config("pat_encrypted", crypto.encrypt_value(pat_secret))
        print("✓ PAT credentials updated successfully!")
        print("\nRestart your app for changes to take effect.")
        return True
    except Exception as exc:
        print(f"✗ Error updating database: {exc}")
        return False

if __name__ == "__main__":
    success = update_pat()
    sys.exit(0 if success else 1)
