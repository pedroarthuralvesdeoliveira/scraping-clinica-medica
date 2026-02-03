from datetime import datetime
from app.core.database import get_session
from app.models.agendamento import Agendamento
from app.models.enums import SistemaOrigem
from app.scraper.next_appointments import NextAppointmentsScraper
from app.services.doctor_service import get_or_create_professional
from app.models.dados_cliente import DadosCliente

class NextAppointmentsService:
    def __init__(self):
        self.scraper = NextAppointmentsScraper()

    def sync_next_appointments(self) -> dict:
        print("Starting next appointments sync process...")
        
        session = get_session()
        stats = {
            "total_scraped": 0,
            "added": 0,
            "updated": 0,
            "errors": 0
        }

        try:
            # Note: NextAppointmentsScraper currently handles its own login and sequence
            # It exports an Excel and parses it.
            result = self.scraper.get_next_appointments()
            
            if result.get("status") != "success":
                print(f"Scraper failed: {result.get('message')}")
                return result

            appointments_data = result.get("appointments", [])
            stats["total_scraped"] = len(appointments_data)

            for apt_data in appointments_data:
                try:
                    # Look for the patient in DB by their code
                    # NextAppointmentsScraper provides 'codigo'
                    codigo_str = apt_data.get("codigo")
                    if not codigo_str:
                        continue
                    
                    # We might need to handle which system this is for. 
                    # For now, let's assume we search across ACTIVE systems or the scraper's current system if it was set.
                    # Based on next_appointments.py, it seems to login to a specific URL.
                    
                    # Find patient
                    patient = session.query(DadosCliente).filter(
                        DadosCliente.codigo == int(codigo_str) if codigo_str.isdigit() else None
                    ).first()

                    # Find or create professional
                    prof_name = apt_data.get("profissional")
                    # We need to know the SistemaOrigem. NextAppointmentsScraper doesn't explicitly expose it in result.
                    # But the base URL in browser.py or the scraper logic might imply it.
                    # Looking at patient_history_scraper, it has set_sistema.
                    # For now, let's use a default or infer from session if possible.
                    # TODO: Make SistemaOrigem explicit in scrapers.
                    sistema = SistemaOrigem.OURO # Defaulting for now based on common usage in logs

                    prof_id = get_or_create_professional(session, prof_name, sistema)

                    # Check for existing appointment to avoid duplicates
                    # Unique constraint by (paciente_id, data_consulta, hora_consulta) or similar
                    existing = session.query(Agendamento).filter_by(
                        data_consulta=apt_data.get("data_consulta"),
                        hora_consulta=apt_data.get("hora_consulta"),
                        profissional=prof_name
                    ).first()
                    
                    if existing:
                        # Update status or other fields if changed
                        existing.status = apt_data.get("status")
                        existing.procedimento = apt_data.get("procedimento")
                        stats["updated"] += 1
                    else:
                        new_apt = Agendamento(
                            paciente_id=patient.id if patient else None,
                            profissional_id=prof_id,
                            sistema_origem=sistema,
                            
                            # Fields from scraper
                            codigo=int(codigo_str) if codigo_str.isdigit() else None,
                            nome_paciente=apt_data.get("nome_paciente"),
                            telefone=apt_data.get("telefone"),
                            cpf=patient.cpf if patient else None,
                            
                            data_consulta=apt_data.get("data_consulta"),
                            hora_consulta=apt_data.get("hora_consulta"),
                            profissional=prof_name,
                            procedimento=apt_data.get("procedimento"),
                            status=apt_data.get("status"),
                            primeira_consulta=apt_data.get("primeira_consulta"),
                            especialidade=apt_data.get("especialidade"),
                            observacoes=apt_data.get("observacoes")
                        )
                        session.add(new_apt)
                        stats["added"] += 1

                except Exception as e:
                    print(f"Error processing appointment for code {apt_data.get('codigo')}: {e}")
                    stats["errors"] += 1

            session.commit()
            return {"status": "success", "stats": stats}

        except Exception as e:
            session.rollback()
            print(f"Critical error in sync_next_appointments: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()

if __name__ == "__main__":
    service = NextAppointmentsService()
    print(service.sync_next_appointments())
