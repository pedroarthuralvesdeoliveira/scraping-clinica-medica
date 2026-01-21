from app.core.database import get_session
from app.models.dados_cliente import DadosCliente
from app.scraper.get_active_patients import GetActivePatients

import time


class PatientSeedService:
    def __init__(self):
        self.scraper = GetActivePatients()

    def seed_patients(self) -> dict:
        """
        Scrapes all active patients and seeds them into the database.
        Then, for each patient without a CPF, searches and updates it.
        """
        print("Starting patient seed process...")
        
        # 1. Scrape basic info from Excel
        result = self.scraper.get_all_active_patients()

        if result.get("status") != "success":
            return result

        patients_data = result.get("patients", [])
        print(f"Scraped {len(patients_data)} patients. Syncing basic info with database...")

        session = get_session()
        patients_to_sync_cpf = []
        
        try:
            added_count = 0
            updated_count = 0

            for patient_dict in patients_data:
                codigo_str = patient_dict.get("codigo")
                if not codigo_str:
                    continue
                
                try:
                    codigo = int(codigo_str)
                except ValueError:
                    continue

                existing_patient = session.query(DadosCliente).filter_by(codigo=codigo).first()

                if existing_patient:
                    existing_patient.nomewpp = patient_dict.get("nomewpp")
                    existing_patient.cad_telefone = patient_dict.get("cad_telefone")
                    updated_count += 1
                else:
                    new_patient = DadosCliente(
                        codigo=codigo,
                        nomewpp=patient_dict.get("nomewpp"),
                        cad_telefone=patient_dict.get("cad_telefone"),
                        telefone=f"55{patient_dict.get('cad_telefone')}@s.whatsapp.net",
                        atendimento_ia="MarcIA",
                        setor="Geral"
                    )
                    session.add(new_patient)
                    added_count += 1
                    existing_patient = new_patient

                # If CPF is missing, mark for sync
                if not existing_patient.cpf:
                    patients_to_sync_cpf.append(existing_patient.codigo)

            session.commit()
            print(f"Basic info sync completed: {added_count} added, {updated_count} updated.")

            # 2. Sync CPFs for those missing
            if patients_to_sync_cpf:
                print(f"Starting CPF synchronization for {len(patients_to_sync_cpf)} patients...")
                
                if self.scraper.prepare_patient_registration_search():
                    cpf_updated_count = 0
                    
                    for i, code in enumerate(patients_to_sync_cpf, 1):
                        print(f"[{i}/{len(patients_to_sync_cpf)}] Fetching CPF for code: {code}")
                        cpf = self.scraper.get_cpf_by_code(str(code))
                        
                        if cpf:
                            # Update in DB
                            db_patient = session.query(DadosCliente).filter_by(codigo=code).first()
                            if db_patient:
                                db_patient.cpf = cpf
                                cpf_updated_count += 1
                                print(f"  CPF encontrado e atualizado: {cpf}")
                                
                                # Periodical commit
                                if cpf_updated_count % 10 == 0:
                                    session.commit()
                                    print("  Commit periódico realizado.")
                        else:
                            print(f"  CPF não encontrado para o código: {code}")

                    session.commit()
                    print(f"CPF synchronization completed: {cpf_updated_count} CPFs updated.")

            return {
                "status": "success",
                "added": added_count,
                "updated": updated_count,
                "cpfs_updated": cpf_updated_count if 'cpf_updated_count' in locals() else 0,
                "total": len(patients_data),
            }

        except Exception as e:
            session.rollback()
            print(f"Error during seed/sync: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()


if __name__ == "__main__":
    service = PatientSeedService()
    result = service.seed_patients()
    print(result)
