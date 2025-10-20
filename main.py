import json 
import os 
from dotenv import load_dotenv
from scraper import check_softclyn_disponibility


def main():
    """
    Ponto de entrada principal para a execução do n8n.
    """
    load_dotenv()

    result = check_softclyn_disponibility()

    print(json.dumps(result))

if __name__ == "__main__":
    main()
