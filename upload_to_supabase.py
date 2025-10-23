import os
import pandas as pd
from supabase import create_client, Client
import json
import xlrd  
import datetime  
import traceback

from parse_clinic_report import parse_clinic_report 

def nan_to_none(value):
    if pd.isna(value):
        return None
    return value

def send_data_to_supabase(file_path):
    print(f"Iniciando processo de parse e upload para {file_path}...")
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    SUPABASE_TABLE = "appointments"

    if not all([SUPABASE_URL, SUPABASE_KEY]):
        print("Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não definidas.")
        return {"status": "error", "message": "Supabase credentials missing."}

    try:
        parsed_result = parse_clinic_report(file_path)
        
        if parsed_result["status"] == "error":
            print(f"Erro ao processar o arquivo Excel: {parsed_result['message']}")
            return parsed_result
            
        data_by_doctor = parsed_result["data"]
        
        all_appointments_to_insert = []
        
        for doctor_name, appointments_list in data_by_doctor.items():
            for appt in appointments_list:

                raw_datetime_str = appt.get("DATA/HORA")
                iso_timestamp = None
                if raw_datetime_str and pd.notna(raw_datetime_str):
                    dt_str = str(raw_datetime_str).strip()
                    dt_str_corrigida = dt_str.replace(" - ", " ")

                    formats_to_try = [
                        '%d/%m/%Y %H:%M:%S',  
                        '%d/%m/%Y %H:%M'    
                    ]

                    dt_obj = None

                    for fmt in formats_to_try:
                        try:
                            dt_obj = datetime.datetime.strptime(dt_str_corrigida, fmt)
                            iso_timestamp = dt_obj.isoformat()
                            break  
                        except ValueError:
                            continue

                    if dt_obj is None:
                        print(f"Aviso: Ignorando data/hora mal formatada (nenhum formato bateu): {dt_str}")
                        continue

                options_data = {
                    "convenio": appt.get("CONVÊNIO"),
                    "carteirinha": appt.get("CARTEIRINHA"),
                    "agendado_por": appt.get("AGEN. POR"),
                    "responsavel": appt.get("RESPONSÁVEL"),
                    "tags": appt.get("TAGS"),
                }
                options_json = json.dumps({k: v for k, v in options_data.items() if pd.notna(v)})

                record_to_insert = {
                    "timestamp": iso_timestamp, 
                    "patient_name": nan_to_none(appt.get("PACIENTE")), 
                    "type": nan_to_none(appt.get("TIPO")), 
                    "options": options_json, 
                    "status": nan_to_none(appt.get("STATUS")), 
                    "phone_number": nan_to_none(appt.get("TELEFONE")), 
                    "responsible_physician": doctor_name, 
                    "observation": nan_to_none(appt.get("OBSERVAÇÕES")) 
                }
                
                if iso_timestamp:
                    all_appointments_to_insert.append(record_to_insert)

        if not all_appointments_to_insert:
            print("Nenhum agendamento válido encontrado no arquivo.")
            return {"status": "warning", "message": "No valid appointments found."}

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        print(f"Preparando para inserir {len(all_appointments_to_insert)} registros no Supabase...")

        response = supabase.table(SUPABASE_TABLE).insert(all_appointments_to_insert).execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"Sucesso! Inseridos {len(response.data)} registros.")
            return {"status": "success", "message": f"Uploaded {len(response.data)} rows."}
        elif hasattr(response, 'error') and response.error:
            print(f"Erro do Supabase: {response.error}")
            return {"status": "error", "message": str(response.error)}
        else:
             print(f"Resposta inesperada do Supabase: {response}")
             return {"status": "error", "message": "Unknown Supabase response."}

    except Exception as e:
        print(f"Erro fatal na função send_data_to_supabase: {e}")
        print(traceback.format_exc())
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    os.environ["SUPABASE_URL"] = "https://izuzdfuemhrmgaboskux.supabase.co"
    os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6dXpkZnVlbWhybWdhYm9za3V4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEwOTAwOTQsImV4cCI6MjA3NjY2NjA5NH0.eh0TI0s7zw59Wb0bLr6qQedJCeIAOSnTlqVXMZexR2s"
    
    arquivo_exemplo = "download/26relatorio.xls" 
    
    if os.path.exists(arquivo_exemplo):
        send_data_to_supabase(arquivo_exemplo)
    else:
        print(f"Arquivo de exemplo não encontrado em: {arquivo_exemplo}")
        print("Por favor, baixe o arquivo ou ajuste o caminho em 'arquivo_exemplo'.")