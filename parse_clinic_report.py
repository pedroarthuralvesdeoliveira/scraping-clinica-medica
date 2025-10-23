import pandas as pd
import json
import xlrd

def parse_clinic_report(file_path: str) -> dict:
    """
    Processa o arquivo .xls da clínica, separando os dados por profissional.
    
    O arquivo tem uma estrutura repetitiva:
    1. Linha do Médico (Nome na Coluna A, restante vazio/mergeado)
    2. Linha de Cabeçalho (DATA/HORA, PACIENTE, etc. nas colunas A-K)
    3. Linhas de Dados
    4. Linha de Total (Fora das colunas A-K, ex: começa na L) ou Linha em Branco
    5. Repete...
    """
    
    STATE_LOOKING_FOR_DOCTOR = 1
    STATE_LOOKING_FOR_HEADER = 2
    STATE_READING_DATA = 3

    try:
        workbook = xlrd.open_workbook(file_path, ignore_workbook_corruption=True)
        
        df = pd.read_excel(workbook, header=None)

        all_doctors_data = {}
        current_doctor_name = None
        current_headers = None
        current_data_rows = []
        
        state = STATE_LOOKING_FOR_DOCTOR

        for index, row in df.iterrows():
            if state == STATE_LOOKING_FOR_DOCTOR:
                if pd.notna(row.iloc[0]) and pd.isna(row.iloc[1]):
                    current_doctor_name = str(row.iloc[0]).strip()
                    state = STATE_LOOKING_FOR_HEADER 
                    continue 

            elif state == STATE_LOOKING_FOR_HEADER:
                if pd.notna(row.iloc[0]) and "DATA/HORA" in str(row.iloc[0]).upper():
                    current_headers = [str(col).strip() for col in row.iloc[0:11]]
                    state = STATE_READING_DATA 
                    current_data_rows = [] 
                    continue

            elif state == STATE_READING_DATA:
                is_data_row = pd.notna(row.iloc[0])
                is_new_doctor = pd.notna(row.iloc[0]) and pd.isna(row.iloc[1])  
                is_end_of_block = pd.isna(row.iloc[0])

                if is_new_doctor:
                    if current_data_rows:
                        doc_df = pd.DataFrame(current_data_rows, columns=current_headers)
                        all_doctors_data[current_doctor_name] = doc_df
                    
                    current_doctor_name = str(row.iloc[0]).strip()
                    state = STATE_LOOKING_FOR_HEADER 
                    continue
                
                elif is_end_of_block:
                    if current_data_rows:
                        doc_df = pd.DataFrame(current_data_rows, columns=current_headers)
                        all_doctors_data[current_doctor_name] = doc_df
                    
                    state = STATE_LOOKING_FOR_DOCTOR
                    current_doctor_name = None
                    current_headers = None
                    current_data_rows = []
                    continue

                elif is_data_row:
                    current_data_rows.append(row.iloc[0:11].tolist())

        if current_doctor_name and current_data_rows:
            doc_df = pd.DataFrame(current_data_rows, columns=current_headers)
            all_doctors_data[current_doctor_name] = doc_df

        final_output = {}
        for doctor, data_df in all_doctors_data.items():
            if "DATA/HORA" in data_df.columns:
                 data_df["DATA/HORA"] = data_df["DATA/HORA"].astype(str)
            final_output[doctor] = data_df.to_dict(orient='records')

        return {"status": "success", "data": final_output}

    except Exception as e:
        import traceback
        print(f"Erro detalhado: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    arquivo_exemplo = "download/26relatorio.xls" 
    
    print(f"Processando arquivo: {arquivo_exemplo}\n")
    
    resultado = parse_clinic_report(arquivo_exemplo)
    
    if resultado["status"] == "success":
        print("--- SUCESSO! ---")
        print(f"Dados processados para {len(resultado['data'])} profissionais.")
        
        print(json.dumps(resultado['data'], indent=2, ensure_ascii=False))
        
    else:
        print(f"--- ERRO ---")
        print(resultado["message"])
