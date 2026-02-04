from app.services.doctor_service import get_or_create_professional
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

    def seed_history(self, offset: int = 0, limit: int | None = None, sistema_filter: str | None = None) -> dict:
        """
        Seeds appointment history from the scraper.
        
        Args:
            offset: Number of patients to skip (for parallel processing)
            limit: Maximum number of patients to process (None = all)
            sistema_filter: Filter by system ('ouro', 'of', or None for both)
        """
        print(f"Starting appointment history seed process (offset={offset}, limit={limit}, sistema={sistema_filter or 'all'})...")
        
        session = get_session()
        stats = {
            "total_patients_processed": 0,
            "appointments_added": 0,
            "appointments_skipped_existing": 0,
            "errors": 0
        }

        try:
            # Filter systems based on parameter
            if sistema_filter:
                sistema_filter = sistema_filter.lower()
                if sistema_filter == 'ouro':
                    systems = [SistemaOrigem.OURO]
                elif sistema_filter == 'of':
                    systems = [SistemaOrigem.OF]
                else:
                    systems = [SistemaOrigem.OURO, SistemaOrigem.OF]
            else:
                systems = [SistemaOrigem.OURO, SistemaOrigem.OF]

            for sistema_enum in systems:
                sistema_str = sistema_enum.value
                print(f"\n--- Processing System: {sistema_str.upper()} ---")

                self.scraper.set_sistema(sistema_str)

                # Build query with offset and limit for parallel processing
                query = session.query(DadosCliente).filter(
                    DadosCliente.sistema_origem == sistema_enum,
                    DadosCliente.codigo.isnot(None)
                ).order_by(DadosCliente.id)  # Consistent ordering for offset
                
                if offset > 0:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)
                
                patients = query.all()

                print(f"Found {len(patients)} patients to process in {sistema_str} (offset={offset}, limit={limit}).")

                for patient in patients:
                    try:
                        stats["total_patients_processed"] += 1
                        print(f"Scraping history for patient {patient.codigo} (ID: {patient.id})...")

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
                                
                                # Robust Time Parsing
                                if not hora_str:
                                    continue
                                    
                                hora_str_clean = hora_str.strip()
                                time_formats = ["%H:%M:%S", "%H:%M"]
                                hora_consulta = None
                                
                                for fmt in time_formats:
                                    try:
                                        hora_consulta = datetime.strptime(hora_str_clean, fmt).time()
                                        break
                                    except ValueError:
                                        continue
                                
                                if not hora_consulta:
                                    # Fallback: take the first two parts if there are more than 2
                                    parts = hora_str_clean.split(':')
                                    if len(parts) >= 2:
                                        try:
                                            fake_hora = f"{parts[0]:0>2}:{parts[1]:0>2}"
                                            hora_consulta = datetime.strptime(fake_hora, "%H:%M").time()
                                        except:
                                            pass
                                
                                if not hora_consulta:
                                    print(f"!!! [DEBUG-FIX] Could not parse time '{hora_str}' for date {dta_str}")
                                    continue
                                    
                            except Exception as e:
                                print(f"!!! [DEBUG-FIX] Date/Time error for {dta_str} {hora_str}: {e}")
                                continue

                            prof_name = apt_data.get("profissional")
                            # TODO: baixar médicos por relatório cadastro de profissionais e relacionar aqui
                            prof_id = get_or_create_professional(session, prof_name, sistema_enum)  

                            # Check for duplicates based on client, date, time
                            exists = session.query(Agendamento).filter_by(
                                paciente_id=patient.id,
                                data_consulta=data_consulta,
                                hora_consulta=hora_consulta,
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
                                paciente_id=patient.id,
                                profissional_id=prof_id,
                                sistema_origem=sistema_enum.value,  # Convert enum to string
                                
                                # Denormalized fields from Patient (with defaults for NOT NULL columns)
                                cpf=patient.cpf or "",  # NOT NULL
                                telefone=patient.cad_telefone or patient.telefone or "",  # NOT NULL
                                nome_paciente=patient.nomewpp or "",  # NOT NULL
                                data_nascimento=patient.data_nascimento or datetime(1900, 1, 1).date(),  # NOT NULL - sentinel date
                                profissional=prof_name or "",  # NOT NULL
                                especialidade="",  # NOT NULL
                                
                                # Scraped fields
                                data_consulta=data_consulta,  # NOT NULL
                                hora_consulta=hora_consulta,  # NOT NULL
                                # profissional=apt_data.get("profissional"),
                                procedimento=apt_data.get("tipo"), # Mapping 'tipo' to 'procedimento'
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
