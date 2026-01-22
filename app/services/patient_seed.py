import re
from app.core.database import get_session
from app.models.dados_cliente import DadosCliente
from app.models.telefones_paciente import TelefonesPaciente
from app.models.enums import SistemaOrigem
from app.scraper.get_active_patients import GetActivePatients

class PatientSeedService:
    def __init__(self):
        self.scraper = GetActivePatients()

    def _extract_phones(self, phone_str: str) -> list[str]:
        if not phone_str:
            return []
        normalized = re.sub(r'[;/|\\,]+', '|', str(phone_str))
        parts = normalized.split('|')
        phones = []
        for part in parts:
            digits = "".join(filter(str.isdigit, part))
            if digits:
                phones.append(digits)
        return list(dict.fromkeys(phones))

    def seed_patients(self) -> dict:
        print("Starting global patient seed process...")
        
        # Lista de sistemas para iterar
        sistemas_para_rodar = [SistemaOrigem.OURO, SistemaOrigem.OF]
        
        # Variáveis locais para contagem (Evita erro de tipagem em dicionário misto)
        grand_total_added = 0
        grand_total_updated = 0
        grand_total_phones = 0
        grand_total_cpfs = 0
        grand_total_scraped = 0
        details_by_system = {}

        session = get_session()

        try:
            for sistema_enum in sistemas_para_rodar:
                sistema_str = sistema_enum.value
                print(f"\n--- Processando Sistema: {sistema_str.upper()} ---")
                
                # 1. Configura e Loga no Sistema Correto
                self.scraper.set_sistema(sistema_str)
                
                result = self.scraper.get_all_active_patients()

                if result.get("status") != "success":
                    print(f"Erro ao baixar do sistema {sistema_str}: {result.get('message')}")
                    continue

                patients_data = result.get("patients", [])
                count_scraped = len(patients_data)
                print(f"Scraped {count_scraped} patients from {sistema_str}.")
                
                # Acumula no total geral
                grand_total_scraped += count_scraped
                
                sys_added = 0
                sys_updated = 0
                sys_phones = 0
                patients_to_sync_cpf = []

                for patient_dict in patients_data:
                    codigo_str = patient_dict.get("codigo")
                    if not codigo_str:
                        continue
                    try:
                        codigo = int(codigo_str)
                    except ValueError:
                        continue

                    existing_patient = session.query(DadosCliente).filter_by(
                        codigo=codigo, 
                        sistema_origem=sistema_enum
                    ).first()

                    raw_nomewpp = patient_dict.get("nomewpp")
                    raw_cad_telefone = patient_dict.get("cad_telefone")
                    extracted_phones = self._extract_phones(raw_cad_telefone)

                    formatted_wpp = None
                    if extracted_phones:
                        formatted_wpp = f"55{extracted_phones[0]}@s.whatsapp.net"

                    if existing_patient:
                        existing_patient.nomewpp = raw_nomewpp
                        existing_patient.cad_telefone = raw_cad_telefone
                        sys_updated += 1
                    else:
                        new_patient = DadosCliente(
                            codigo=codigo,
                            sistema_origem=sistema_enum, 
                            nomewpp=raw_nomewpp,
                            cad_telefone=raw_cad_telefone,
                            telefone=formatted_wpp,
                            atendimento_ia="MarcIA",
                            setor="Geral"
                        )
                        session.add(new_patient)
                        sys_added += 1
                        existing_patient = new_patient

                    session.flush() # Para ter o ID

                    for i, phone_num in enumerate(extracted_phones):
                        phone_exists = session.query(TelefonesPaciente).filter_by(
                            cliente_codigo=existing_patient.id,
                            numero=phone_num
                        ).first()

                        if not phone_exists:
                            tipo = "whatsapp" if len(phone_num) >= 10 else "telefone fixo"
                            new_phone = TelefonesPaciente(
                                cliente_codigo=existing_patient.id,
                                numero=phone_num,
                                tipo=tipo,
                                is_principal=(i == 0)
                            )
                            session.add(new_phone)
                            sys_phones += 1

                    if not existing_patient.cpf:
                        patients_to_sync_cpf.append(existing_patient.codigo)

                session.commit()
                
                grand_total_added += sys_added
                grand_total_updated += sys_updated
                grand_total_phones += sys_phones
                
                details_by_system[sistema_str] = {
                    "added": sys_added, 
                    "updated": sys_updated,
                    "phones": sys_phones
                }
                
                print(f"Sync {sistema_str} concluído: {sys_added} novos, {sys_updated} atualizados.")

                if patients_to_sync_cpf:
                    print(f"Iniciando busca de CPF para {len(patients_to_sync_cpf)} pacientes em {sistema_str}...")
                    
                    if self.scraper.prepare_patient_registration_search():
                        sys_cpf_updated = 0
                        for i, code in enumerate(patients_to_sync_cpf, 1):
                            cpf = self.scraper.get_cpf_by_code(str(code))
                            if cpf:
                                db_patient = session.query(DadosCliente).filter_by(
                                    codigo=code, 
                                    sistema_origem=sistema_enum
                                ).first()
                                
                                if db_patient:
                                    db_patient.cpf = cpf
                                    sys_cpf_updated += 1
                                    if sys_cpf_updated % 10 == 0:
                                        session.commit()
                        
                        session.commit()
                        grand_total_cpfs += sys_cpf_updated
                        print(f"CPFs atualizados em {sistema_str}: {sys_cpf_updated}")

            # Retorna o dicionário completo apenas no final
            return {
                "status": "success",
                "added": grand_total_added,
                "updated": grand_total_updated,
                "phones_added": grand_total_phones,
                "cpfs_updated": grand_total_cpfs,
                "total_scraped": grand_total_scraped,
                "details_by_system": details_by_system
            }

        except Exception as e:
            session.rollback()
            print(f"Critical error: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()
            self.scraper.quit()