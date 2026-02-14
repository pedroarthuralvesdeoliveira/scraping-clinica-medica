from app.core.database import get_session
from app.models.dados_cliente import DadosCliente
from app.scraper.get_active_patients import GetActivePatients
import time

class PatientCPFSyncService:
    def __init__(self):
        self.scraper = GetActivePatients()

    def sync_cpfs(self) -> dict:
        """
        Syncs patient CPFs by searching their codes in the registration screen.
        """
        print("Starting CPF sync process...")
        
        session = get_session()
        try:
            # Fetch patients with missing CPF
            patients = session.query(DadosCliente).filter(
                (DadosCliente.cpf == None) | (DadosCliente.cpf == "")
            ).all()

            if not patients:
                print("No patients found with missing CPF.")
                return {"status": "success", "message": "No patients to sync."}

            print(f"Found {len(patients)} patients with missing CPF.")

            # Initialize scraper and navigate to the search modal
            self.scraper._login()
            self.scraper._close_modal()
            if not self.scraper.prepare_patient_registration_search():
                raise Exception("Could not prepare patient search modal.")

            updated_count = 0
            failed_count = 0

            for i, patient in enumerate(patients, 1):
                print(f"[{i}/{len(patients)}] Syncing CPF for code: {patient.codigo} ({patient.nomewpp})")
                
                try:
                    cpf = self.scraper.get_cpf_by_code(str(patient.codigo))
                    
                    if cpf:
                        patient.cpf = cpf
                        updated_count += 1
                        print(f"  Found and updated CPF: {cpf}")
                        
                        # Commit every 10 updates
                        if updated_count % 10 == 0:
                            session.commit()
                            print("  Periodic commit performed.")
                    else:
                        print(f"  CPF not found for code: {patient.codigo}")
                        failed_count += 1
                
                except Exception as e:
                    print(f"  Error syncing code {patient.codigo}: {e}")
                    failed_count += 1
                    # Optional: Re-prepare if session seems lost
                    if "disconnected" in str(e).lower() or "session" in str(e).lower():
                        self.scraper._login()
                        self.scraper._close_modal()
                        self.scraper.prepare_patient_registration_search()

            session.commit()
            print(f"CPF sync completed: {updated_count} updated, {failed_count} failed.")

            return {
                "status": "success",
                "total_processed": len(patients),
                "updated": updated_count,
                "failed": failed_count,
            }

        except Exception as e:
            session.rollback()
            print(f"Critical error during CPF sync: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()

if __name__ == "__main__":
    service = PatientCPFSyncService()
    result = service.sync_cpfs()
    print(result)
