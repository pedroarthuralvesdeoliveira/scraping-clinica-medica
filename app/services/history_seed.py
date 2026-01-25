import time
from datetime import datetime
from app.core.database import get_session
from app.models.dados_cliente import DadosCliente
from app.models.agendamento import Agendamento
from app.models.enums import SistemaOrigem
from app.scraper.patient_history_scraper import PatientHistoryScraper

class AppointmentHistoryService:
    def __init__(self):
        self.scraper = PatientHistoryScraper()

    def seed_history(self) -> dict:
        print("Starting appointment history seed process...")
        
        session = get_session()
        stats = {
            "total_patients_processed": 0,
            "appointments_added": 0,
            "appointments_skipped_existing": 0,
            "errors": 0
        }

        try:
            # Group by system to minimize system switching overhead (if any) and for logic clarity
            systems = [SistemaOrigem.OURO, SistemaOrigem.OF]

            for sistema_enum in systems:
                sistema_str = sistema_enum.value
                print(f"\n--- Processing System: {sistema_str.upper()} ---")

                # Set scraper system
                self.scraper.set_sistema(sistema_str)

                # Fetch patient codes for this system
                patients = session.query(DadosCliente).filter(
                    DadosCliente.sistema_origem == sistema_enum,
                    DadosCliente.codigo.isnot(None)
                ).all()

                print(f"Found {len(patients)} patients in {sistema_str}.")

                for patient in patients:
                    try:
                        stats["total_patients_processed"] += 1
                        print(f"Scraping history for patient {patient.codigo} (ID: {patient.id})...")

                        # Scrape history using Code
                        result = self.scraper.get_patient_history(str(patient.codigo), search_type="codigo")
                        
                        if result.get("status") != "success":
                            print(f"Failed to scrape history for patient {patient.codigo}: {result.get('message')}")
                            stats["errors"] += 1
                            continue

                        appointments = result.get("appointments", [])
                        
                        for apt_data in appointments:
                            # Extract data from scraped dict
                            # Format: {'profissional': '...', 'data_atendimento': 'dd/mm/aaaa', 'hora': 'HH:MM', 'tipo': '...', 'retorno_ate': '...'}
                            
                            dta_str = apt_data.get("data_atendimento")
                            hora_str = apt_data.get("hora")
                            
                            if not dta_str or not hora_str:
                                continue

                            try:
                                data_consulta = datetime.strptime(dta_str, "%d/%m/%Y").date()
                                hora_consulta = datetime.strptime(hora_str, "%H:%M").time()
                            except ValueError as ve:
                                print(f"Date/Time parse error: {ve}")
                                continue

                            # Check for duplicates based on client, date, time
                            exists = session.query(Agendamento).filter_by(
                                id_cliente=patient.id,
                                data_consulta=data_consulta,
                                hora_consulta=hora_consulta
                            ).first()

                            if exists:
                                # Update? Maybe update retorno_ate if changed?
                                # For now, just skip or maybe update fields that might change.
                                # Let's update retorno_ate just in case
                                ret_str = apt_data.get("retorno_ate")
                                if ret_str:
                                    try:
                                        exists.retorno_ate = datetime.strptime(ret_str, "%d/%m/%Y").date()
                                    except:
                                        pass
                                stats["appointments_skipped_existing"] += 1
                                continue

                            # Create new appointment
                            new_apt = Agendamento(
                                id_cliente=patient.id,
                                sistema_origem=sistema_enum,
                                codigo=patient.codigo, # Redundant but compliant with schema
                                
                                # Denormalized fields from Patient
                                cpf=patient.cpf,
                                telefone=patient.cad_telefone or patient.telefone,
                                nome_paciente=patient.nomewpp, # Fallback name
                                data_nascimento=patient.data_nascimento,
                                
                                # Scraped fields
                                data_consulta=data_consulta,
                                hora_consulta=hora_consulta,
                                profissional=apt_data.get("profissional"),
                                procedimento=apt_data.get("tipo"), # Mapping 'tipo' to 'procedimento' or 'especialidade'? Schema has both.
                                # 'tipo' in scraper seems to be like "CONSULTA", "RETORNO", etc.
                                # 'especialidade' is NOT in scraper data. 
                                especialidade="", 
                                status="Realizado", # Assumption for history items
                                
                                observacoes=f"Scraped type: {apt_data.get('tipo')}"
                            )

                            # Handle retorno_ate
                            ret_str = apt_data.get("retorno_ate")
                            if ret_str:
                                try:
                                    new_apt.retorno_ate = datetime.strptime(ret_str, "%d/%m/%Y").date()
                                except:
                                    pass

                            session.add(new_apt)
                            stats["appointments_added"] += 1

                        session.commit() # Commit per patient or batch? Per patient is safer for now.
                    
                    except Exception as e:
                        print(f"Error processing patient {patient.codigo}: {e}")
                        session.rollback()
                        stats["errors"] += 1

            return {"status": "success", "stats": stats}

        except Exception as e:
            session.rollback()
            print(f"Critical error in seed_history: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()

if __name__ == "__main__":
    service = AppointmentHistoryService()
    result = service.seed_history()
    print(result)
