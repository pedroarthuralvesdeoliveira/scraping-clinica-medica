# upload_to_supabase.py

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

def send_data_to_supabase(file_path):
    try:
        # Try reading with openpyxl for .xlsx files
        df = pd.read_excel(file_path, engine='openpyxl', header=None)
        print(f"Successfully read {len(df)} rows from {file_path}.")
        data_to_insert = df.to_dict(orient='records')
        return {"status": "success", "message": f"Read {len(df)} rows."}
    except Exception as e:
        print(f"Error reading with openpyxl: {e}")
        # Fallback to xlrd for .xls files
        try:
            workbook = xlrd.open_workbook(file_path, ignore_workbook_corruption=True)
            df = pd.read_excel(workbook)
            # df = pd.read_excel(file_path, engine='xlrd', header=None)
            print(f"Successfully read {len(df)} rows from {file_path}.")
            print(df.head())            
            data_to_insert = df.to_dict(orient='records')
            return {"status": "success", "message": f"Read {len(df)} rows."}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Run directly
if __name__ == "__main__":
    test_file = "download/26relatorio.xls"  # Replace with real path
    result = send_data_to_supabase(test_file)
    print(result)
