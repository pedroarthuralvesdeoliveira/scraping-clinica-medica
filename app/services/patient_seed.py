from app.models.telefones_paciente import TelefonesPaciente
from app.core.database import get_session
from app.models.dados_cliente import DadosCliente
from app.scraper.get_active_patients import GetActivePatients

import time


class PatientSeedService:
    def __init__(self):
        self.scraper = GetActivePatients()

    def _extract_phones(self, phone_str: str) -> list[str]:
        """
        Recebe uma string suja (ex: "45 9999-8888 / 45 9888-7777")
        e retorna uma lista de apenas números (ex: ["4599998888", "4598887777"]).
        """
        import re

        if not phone_str:
            return []
        
        # Substitui separadores comuns por um único separador para split
        # Ex: "123 / 456" -> "123|456"
        normalized = re.sub(r'[;/|\\,]+', '|', str(phone_str))
        parts = normalized.split('|')
        
        phones = []
        for part in parts:
            # Mantém apenas dígitos
            digits = "".join(filter(str.isdigit, part))
            if digits:
                phones.append(digits)
        
        # Remove duplicados preservando ordem
        return list(dict.fromkeys(phones))

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
            phones_added_count = 0

            for patient_dict in patients_data:
                codigo_str = patient_dict.get("codigo")
                if not codigo_str:
                    continue
                
                try:
                    codigo = int(codigo_str)
                except ValueError:
                    continue

                existing_patient = session.query(DadosCliente).filter_by(codigo=codigo).first()

                raw_nomewpp = patient_dict.get("nomewpp")
                raw_cad_telefone = patient_dict.get("cad_telefone")
                extracted_phones = self._extract_phones(raw_cad_telefone)

                formatted_wpp = None
                if extracted_phones:
                    primeiro_numero = extracted_phones[0]
                    formatted_wpp = f"55{primeiro_numero}@s.whatsapp.net"

                if existing_patient:
                    existing_patient.nomewpp = patient_dict.get("nomewpp")
                    existing_patient.cad_telefone = raw_cad_telefone
                    updated_count += 1
                else:
                    new_patient = DadosCliente(
                        codigo=codigo,
                        nomewpp=raw_nomewpp,
                        cad_telefone=raw_cad_telefone,
                        telefone=formatted_wpp,
                        atendimento_ia="MarcIA",
                        setor="Geral"
                    )
                    session.add(new_patient)
                    added_count += 1
                    existing_patient = new_patient

                session.flush()

                for i, phone_num in enumerate(extracted_phones):
                    # Verifica se esse número já existe para este paciente
                    phone_exists = session.query(TelefonesPaciente).filter_by(
                        cliente_codigo=existing_patient.id,
                        numero=phone_num
                    ).first()

                    if not phone_exists:
                        # Define tipo básico e se é principal
                        # Lógica simples: Se tem 10+ dígitos (DDD+N), assume celular/whatsapp.
                        tipo = "whatsapp" if len(phone_num) >= 10 else "telefone fixo"
                        # O primeiro número encontrado será o principal se ainda não houver nenhum
                        is_principal = (i == 0)

                        new_phone = TelefonesPaciente(
                            cliente_codigo=existing_patient.id,
                            numero=phone_num,
                            tipo=tipo,
                            is_principal=is_principal
                        )
                        session.add(new_phone)
                        phones_added_count += 1

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
