import sys
import os

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.patient_seed import PatientSeedService
from app.services.history_seed import AppointmentHistoryService

def main():
    print("========================================================")
    print("STARTING FULL SYNC PROCESS")
    print("========================================================")

    # Stage 1: Patients
    # print("\n>>> STAGE 1: Syncing Patients (Excel Extraction + Phone Enrichment)...")
    # try:
    #     patient_service = PatientSeedService()
    #     p_result = patient_service.seed_patients()
    #     print("Patient Sync Completed.")
    #     print("Result:", p_result)
    # except Exception as e:
    #     print(f"CRITICAL ERROR in Stage 1: {e}")
    #     print("Proceeding to Stage 2 with existing patients...")

    # Stage 2: History
    print("\n>>> STAGE 2: Syncing Appointment History...")
    try:
        history_service = AppointmentHistoryService()
        h_result = history_service.seed_history()
        print("History Sync Completed.")
        print("Result:", h_result)
    except Exception as e:
        print(f"CRITICAL ERROR in Stage 2: {e}")

    print("\n========================================================")
    print("FULL SYNC PROCESS FINISHED")
    print("========================================================")

if __name__ == "__main__":
    main()
