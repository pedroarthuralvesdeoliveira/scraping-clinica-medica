import os
import pandas as pd
from supabase import create_client, Client
import xlrd

# def send_data_to_supabase(file_path):
    # print(f"Attempting to send data from {file_path} to Supabase...")
    
    # SUPABASE_URL = os.environ.get("SUPABASE_URL")
    # SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    # SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE")

    # if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE]):
    #     print("Error: Supabase environment variables (URL, KEY, TABLE) are not set.")
    #     return {"status": "error", "message": "Supabase credentials missing."}

    # try:
        # supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # df = pd.read_excel(file_path, engine='xlrd', header=None)
        # print(f"Successfully read {len(df)} rows from {file_path}.")

        # data_to_insert = df.to_dict(orient='records')

        # response = supabase.table(SUPABASE_TABLE).insert(data_to_insert).execute()
        # print(f"Data sent to Supabase. Response: {response.data}")
        # return {"status": "success", "message": f"Uploaded {len(df)} rows."}
    # except Exception as e:
        # print(f"Error sending data to Supabase: {e}")
        # return {"status": "error", "message": str(e)}

# def send_data_to_supabase(file_path):
#     try:
#         # Try reading with openpyxl for .xlsx files
#         df = pd.read_excel(file_path, engine='openpyxl', header=None)
#         print(f"Successfully read {len(df)} rows from {file_path}.")
#         data_to_insert = df.to_dict(orient='records')
#         return {"status": "success", "message": f"Read {len(df)} rows."}
#     except Exception as e:
#         print(f"Error reading with openpyxl: {e}")
#         # Fallback to xlrd for .xls files
#         try:
#             workbook = xlrd.open_workbook(file_path, ignore_workbook_corruption=True)
#             df = pd.read_excel(workbook)
#             # df = pd.read_excel(file_path, engine='xlrd', header=None)
#             print(f"Successfully read {len(df)} rows from {file_path}.")
#             print(df.head())            
#             data_to_insert = df.to_dict(orient='records')
#             return {"status": "success", "message": f"Read {len(df)} rows."}
#         except Exception as e:
#             return {"status": "error", "message": str(e)}

def send_data_to_supabase(file_path):
    try:
        # Read the workbook with xlrd, ignoring corruption
        workbook = xlrd.open_workbook(file_path, ignore_workbook_corruption=True)
        # Read the first sheet into a DataFrame
        df = pd.read_excel(workbook)

        # Initialize variables to store results
        doctors_data = {}
        current_doctor = None
        header_row = None
        header_row_index = None

        # Iterate through the DataFrame
        for index, row in df.iterrows():
            # Check if this is a doctor name (value in first column, rest may be merged)
            if pd.notna(row.iloc[0]) and (all(pd.isna(row.iloc[i]) for i in range(1, len(row))) or row.iloc[1] == row.iloc[0]):
                if current_doctor and header_row is not None:
                    # Process the previous doctor's data, stopping before the summary row
                    start_idx = header_row_index + 1
                    # Look ahead to find the summary row
                    end_idx = index
                    for j in range(index - 1, start_idx - 1, -1):
                        if pd.notna(df.iloc[j, 0]) and "Total de Registros" in str(df.iloc[j, 0]):
                            end_idx = j
                            break
                    doctor_df = df.iloc[start_idx:end_idx].dropna(how='all')
                    if not doctor_df.empty:
                        # Ensure header matches the number of columns (should be 11)
                        expected_cols = len(doctor_df.columns)
                        header_row = [col for col in header_row if col in ["DATA/HORA", "PACIENTE", "CARTEIRINHA", "TELEFONE", "CONVÊNIO", "TIPO", "AGEN. POR", "RESPONSÁVEL", "OBSERVAÇÕES", "TAGS", "STATUS"]]
                        if len(header_row) > expected_cols:
                            header_row = header_row[:expected_cols]
                        elif len(header_row) < expected_cols:
                            header_row.extend([""] * (expected_cols - len(header_row)))
                        doctor_df.columns = header_row
                        doctors_data[current_doctor] = doctor_df
                current_doctor = row.iloc[0]
                header_row_index = index
                header_row = None
            # Check if this is the header row (after doctor name, before data)
            elif current_doctor and header_row is None and pd.notna(row.iloc[0]):
                header_row = row.dropna().tolist()
                # Filter to expected headers and adjust length
                header_row = [col for col in header_row if col in ["DATA/HORA", "PACIENTE", "CARTEIRINHA", "TELEFONE", "CONVÊNIO", "TIPO", "AGEN. POR", "RESPONSÁVEL", "OBSERVAÇÕES", "TAGS", "STATUS"]]
                if len(header_row) == 0:
                    header_row = ["DATA/HORA", "PACIENTE", "CARTEIRINHA", "TELEFONE", "CONVÊNIO", "TIPO", "AGEN. POR", "RESPONSÁVEL", "OBSERVAÇÕES", "TAGS", "STATUS"]

        # Process the last doctor's data
        if current_doctor and header_row is not None:
            start_idx = header_row_index + 1
            # Look ahead to find the summary row for the last doctor
            end_idx = len(df)
            for j in range(len(df) - 1, start_idx - 1, -1):
                if pd.notna(df.iloc[j, 0]) and "Total de Registros" in str(df.iloc[j, 0]):
                    end_idx = j
                    break
            doctor_df = df.iloc[start_idx:end_idx].dropna(how='all')
            if not doctor_df.empty:
                expected_cols = len(doctor_df.columns)
                header_row = [col for col in header_row if col in ["DATA/HORA", "PACIENTE", "CARTEIRINHA", "TELEFONE", "CONVÊNIO", "TIPO", "AGEN. POR", "RESPONSÁVEL", "OBSERVAÇÕES", "TAGS", "STATUS"]]
                if len(header_row) > expected_cols:
                    header_row = header_row[:expected_cols]
                elif len(header_row) < expected_cols:
                    header_row.extend([""] * (expected_cols - len(header_row)))
                doctor_df.columns = header_row
                doctors_data[current_doctor] = doctor_df

        # Print or process the results
        for doctor, data in doctors_data.items():
            print(f"Doctor: {doctor}")
            print(data)
            # Add Supabase upload logic here if needed
            # data_to_insert = data.to_dict(orient='records')
            # supabase.table(SUPABASE_TABLE).insert(data_to_insert).execute()

        return {"status": "success", "message": f"Processed data for {len(doctors_data)} doctors."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# TODO Pular linha que tem somente uma coluna com o nome do doutor responsavel, e pular linha de total
# Acessar dados somente de colunas de A a K

# Run directly
if __name__ == "__main__":
    test_file = "download/26relatorio.xls"  # Replace with real path
    result = send_data_to_supabase(test_file)
    print(result)
