#!/usr/bin/env python3
"""
Cronjob script for syncing appointments from the website.
This script is designed to run every 15 minutes via cron.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.appointment_sync import AppointmentSyncService
from datetime import datetime


def main():
    print(f"[{datetime.now()}] Starting appointment sync cronjob")

    try:
        sync_service = AppointmentSyncService()
        result = sync_service.sync_all_appointments()

        if result.get("status") == "success":
            print(f"[{datetime.now()}] Sync completed successfully:")
            print(
                f"  - Total appointments found: {result.get('total_website_appointments', 0)}"
            )
            print(
                f"  - New appointments added: {result.get('new_appointments_added', 0)}"
            )
            print(f"  - Appointments updated: {result.get('appointments_updated', 0)}")
        else:
            print(
                f"[{datetime.now()}] Sync failed: {result.get('message', 'Unknown error')}"
            )
            sys.exit(1)

    except Exception as e:
        print(f"[{datetime.now()}] Unexpected error during sync: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
