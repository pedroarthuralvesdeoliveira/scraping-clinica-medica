from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_session
from app.models.agendamento import Agendamento
from app.models.dados_cliente import DadosCliente
from app.scraper.patient_history_scraper import PatientHistoryScraper


class PatientCodeSyncService:
    def __init__(self):
        self.scraper = PatientHistoryScraper()

    def _sync_data(self, search_type: str, items: List[str]) -> dict:
        """
        Generic method to sync patient codes by different search types.
        """
        session = get_session()
        try:
            print(f"Found {len(items)} items to sync codes for using type: {search_type}")

            # Initialize search screen once
            if not self.scraper.prepare_patient_search(patient_type=search_type):
                return {"status": "error", "message": f"Could not initialize patient search screen for {search_type}"}

            updated_count = 0
            failed_count = 0

            for i, value in enumerate(items, 1):
                print(f"[{i}/{len(items)}] Processing {search_type}: {value}")

                try:
                    codigo_text = self.scraper.get_patient_by_type(search_type, value)
                    
                    # If failed, try to re-prepare search screen Once (session might have expired)
                    if codigo_text is None:
                        print("  Search failed, attempting to re-prepare session...")
                        if self.scraper.prepare_patient_search(force_login=True, patient_type=search_type):
                            codigo_text = self.scraper.get_patient_by_type(search_type, value)

                    if codigo_text:
                        codigo = int(codigo_text)
                        
                        # Update based on search type
                        filter_attr = DadosCliente.cpf if search_type == "cpf" else DadosCliente.nomewpp
                        session.query(DadosCliente).filter(
                            filter_attr == value
                        ).update({"codigo": codigo})
                        
                        updated_count += 1
                        print(f"  Updated code: {codigo}")
                        
                        # Every 10 updates, commit to database to avoid losing progress
                        if updated_count % 10 == 0:
                            session.commit()
                    else:
                        print(f"  No code found for {search_type}: {value}")
                        failed_count += 1

                except Exception as e:
                    print(f"  Error processing {search_type} {value}: {e}")
                    failed_count += 1
                    continue

            session.commit()

            return {
                "status": "success",
                "total_items": len(items),
                "updated": updated_count,
                "failed": failed_count,
            }

        except Exception as e:
            session.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()

    def sync_patient_names(self): 
        session = get_session()
        try:
            names = session.query(DadosCliente.nomewpp).filter(DadosCliente.codigo == None, DadosCliente.cpf == None).all()
            names = [name[0] for name in names if name[0]]
        finally:
            session.close() # Close session before starting the long-running sync
            
        return self._sync_data("nome", names)

    def sync_patient_codes(self) -> dict:
        """
        Syncs patient codes from website to database using CPF.
        """
        session = get_session()
        try:
            cpfs = session.query(DadosCliente.cpf).filter(DadosCliente.codigo == None).distinct().all()
            cpfs = [cpf[0] for cpf in cpfs if cpf[0]]
        finally:
            session.close() # Close session before starting the long-running sync
            
        return self._sync_data("cpf", cpfs)

    def sync_patient_name(self, nome: str) -> dict:
        """
        Syncs patient code for a single name.
        """
        session = get_session()
        try:
            codigo = self.scraper.get_patient_by_type("nome", nome)

            if codigo:
                session.query(DadosCliente).filter(DadosCliente.nomewpp == nome).update(
                    {"codigo": codigo}
                )
                session.commit()
                return {"status": "success", "nome": nome, "codigo": codigo}
            else:
                return {"status": "not_found", "nome": nome}

        except Exception as e:
            session.rollback()
            return {"status": "error", "nome": nome, "message": str(e)}
        finally:
            session.close()

    def sync_patient_code(self, cpf: str) -> dict:
        """
        Syncs patient code for a single CPF.
        """
        session = get_session()
        try:
            codigo = self.scraper.get_patient_by_type("cpf", cpf)

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
    # result = sync.sync_patient_codes()
    result = sync.sync_patient_names()
    print(result)
