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
    
    # Estados da nossa máquina de processamento
    STATE_LOOKING_FOR_DOCTOR = 1
    STATE_LOOKING_FOR_HEADER = 2
    STATE_READING_DATA = 3

    try:
        # Abrir o workbook com xlrd
        workbook = xlrd.open_workbook(file_path, ignore_workbook_corruption=True)
        
        # Ler a primeira planilha para um DataFrame, sem cabeçalho
        df = pd.read_excel(workbook, header=None)

        all_doctors_data = {}
        current_doctor_name = None
        current_headers = None
        current_data_rows = []
        
        # Inicia no estado "procurando médico"
        state = STATE_LOOKING_FOR_DOCTOR

        # Itera por cada linha do DataFrame
        for index, row in df.iterrows():
            
            # --- ESTADO 1: PROCURANDO MÉDICO ---
            if state == STATE_LOOKING_FOR_DOCTOR:
                # Um médico é identificado por ter um nome na Coluna A (índice 0)
                # e NADA na Coluna B (índice 1) - Veja imagem (Linha 1, 10, 30)
                if pd.notna(row.iloc[0]) and pd.isna(row.iloc[1]):
                    current_doctor_name = str(row.iloc[0]).strip()
                    state = STATE_LOOKING_FOR_HEADER # Achamos, agora procure o cabeçalho
                    # print(f"DEBUG: Achei Médico: {current_doctor_name} (Linha {index})") # Debug
                    continue # Pula para a próxima linha

            # --- ESTADO 2: PROCURANDO CABEÇALHO ---
            elif state == STATE_LOOKING_FOR_HEADER:
                # O cabeçalho é identificado por ter "DATA/HORA" na Coluna A
                if pd.notna(row.iloc[0]) and "DATA/HORA" in str(row.iloc[0]).upper():
                    # Pega as 11 colunas (A-K) como cabeçalho
                    current_headers = [str(col).strip() for col in row.iloc[0:11]]
                    state = STATE_READING_DATA # Achamos, agora leia os dados
                    current_data_rows = [] # Limpa dados antigos
                    # print(f"DEBUG: Achei Cabeçalho para {current_doctor_name} (Linha {index})") # Debug
                    continue # Pula para a próxima linha

            # --- ESTADO 3: LENDO DADOS ---
            elif state == STATE_READING_DATA:
                # Enquanto lemos dados, precisamos verificar 3 coisas:
                
                # 1. É uma linha de DADOS? (Tem algo na Coluna A)
                is_data_row = pd.notna(row.iloc[0])
                
                # 2. É uma linha de NOVO MÉDICO? (Começa um novo bloco)
                is_new_doctor = pd.notna(row.iloc[0]) and pd.isna(row.iloc[1])
                
                # 3. É uma linha de TOTAL ou VAZIA? (Termina o bloco atual)
                #    (Coluna A está vazia)
                is_end_of_block = pd.isna(row.iloc[0])

                if is_new_doctor:
                    # --- Encontramos um NOVO médico ---
                    # 1. Salvar os dados do médico anterior
                    if current_data_rows:
                        doc_df = pd.DataFrame(current_data_rows, columns=current_headers)
                        all_doctors_data[current_doctor_name] = doc_df
                        # print(f"DEBUG: Salvei dados de {current_doctor_name} ({len(doc_df)} linhas)") # Debug
                    
                    # 2. Iniciar o processamento do novo médico
                    current_doctor_name = str(row.iloc[0]).strip()
                    state = STATE_LOOKING_FOR_HEADER # Procurar cabeçalho dele
                    # print(f"DEBUG: Achei Médico: {current_doctor_name} (Linha {index})") # Debug
                    continue
                
                elif is_end_of_block:
                    # --- Encontramos uma linha VAZIA ou de TOTAL ---
                    # 1. Salvar os dados do médico anterior
                    if current_data_rows:
                        doc_df = pd.DataFrame(current_data_rows, columns=current_headers)
                        all_doctors_data[current_doctor_name] = doc_df
                        # print(f"DEBUG: Salvei dados de {current_doctor_name} ({len(doc_df)} linhas)") # Debug
                    
                    # 2. Voltar a procurar um médico
                    state = STATE_LOOKING_FOR_DOCTOR
                    current_doctor_name = None
                    current_headers = None
                    current_data_rows = []
                    # print(f"DEBUG: Fim do bloco. Procurando novo médico (Linha {index})") # Debug
                    continue

                elif is_data_row:
                    # --- É uma linha de dados comum ---
                    # Adiciona os dados das colunas A-K na lista
                    current_data_rows.append(row.iloc[0:11].tolist())

        # --- FIM DO LOOP ---
        # Após o loop, pode ter sobrado dados do ÚLTIMO médico. Salva eles.
        if current_doctor_name and current_data_rows:
            doc_df = pd.DataFrame(current_data_rows, columns=current_headers)
            all_doctors_data[current_doctor_name] = doc_df
            # print(f"DEBUG: Salvei dados do ÚLTIMO médico: {current_doctor_name} ({len(doc_df)} linhas)") # Debug

        # --- Processamento Final ---
        # Converter os DataFrames em dicionários (JSON), que é mais fácil de usar
        final_output = {}
        for doctor, data_df in all_doctors_data.items():
            # Converte colunas de data/hora para string para evitar problemas com JSON
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
