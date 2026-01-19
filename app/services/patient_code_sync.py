from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_session
from app.models.agendamento import Agendamento
from app.models.dados_cliente import DadosCliente
from app.scraper.patient_history_scraper import PatientHistoryScraper


class PatientCodeSyncService:
    def __init__(self):
        self.scraper = PatientHistoryScraper()

    def sync_patient_codes(self) -> dict:
        """
        Syncs patient codes from website to database.
        Updates the 'codigo' column for all CPFs in the database.
        """
        session = get_session()
        try:
            cpfs = session.query(DadosCliente.cpf).distinct().all()
            cpfs = [cpf[0] for cpf in cpfs]

            print(f"Found {len(cpfs)} unique CPFs to sync codes for")

            updated_count = 0
            failed_count = 0

            for i, cpf in enumerate(cpfs, 1):
                print(f"[{i}/{len(cpfs)}] Processing CPF: {cpf}")

                try:
                    codigo = int(self.scraper.get_patient_code(cpf))

                    if codigo:
                        session.query(DadosCliente).filter(
                            DadosCliente.cpf == cpf
                        ).update({"codigo": codigo})
                        updated_count += 1
                        print(f"  Updated code: {codigo}")
                    else:
                        print(f"  No code found for CPF: {cpf}")
                        failed_count += 1

                except Exception as e:
                    print(f"  Error processing CPF {cpf}: {e}")
                    failed_count += 1
                    continue

            session.commit()

            return {
                "status": "success",
                "total_cpfs": len(cpfs),
                "updated": updated_count,
                "failed": failed_count,
            }

        except Exception as e:
            session.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            session.close()

    def sync_patient_code(self, cpf: str) -> dict:
        """
        Syncs patient code for a single CPF.
        """
        session = get_session()
        try:
            codigo = self.scraper.get_patient_code(cpf)

            if codigo:
                session.query(DadosCliente).filter(DadosCliente.cpf == cpf).update(
                    {"codigo": codigo}
                )
                session.commit()
                return {"status": "success", "cpf": cpf, "codigo": codigo}
            else:
                return {"status": "not_found", "cpf": cpf}

        except Exception as e:
            session.rollback()
            return {"status": "error", "cpf": cpf, "message": str(e)}
        finally:
            session.close()


if __name__ == "__main__":
    sync = PatientCodeSyncService()
    result = sync.sync_patient_codes()
    print(result)
