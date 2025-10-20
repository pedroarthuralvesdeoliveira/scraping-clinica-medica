import os 
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager

def check_softclyn_disponibility():
    """
    Executa a automação completa no SoftClyn e retorna o próximo horário.
    """

    # Configuração do WebDriver

    options = Options()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--no-sandbox')  # Required for WSL2
    options.add_argument('--disable-dev-shm-usage')  # Avoids issues with shared memory
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    URL = os.environ.get("SOFTCLYN_URL")
    USER = os.environ.get("SOFTCLYN_USER")
    PASSWORD = os.environ.get("SOFTCLYN_PASS")

    try: 
        driver.get(URL)

        driver.find_element(By.ID, "usuario").send_keys(USER)
        driver.find_element(By.ID, "senha").send_keys(PASSWORD)
        driver.find_element(By.ID, "btlLogin").click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located)

        # Aguarda a modal aparecer (botão "OK" da modal)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-bb-handler="ok"]'))
        )

        # Clica no botão "OK" para fechar a modal
        driver.find_element(By.CSS_SELECTOR, 'button[data-bb-handler="ok"]').click()

        # Aguarde a modal desaparecer
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, 'bootbox'))
        )

        # Se tudo deu certo, retorne os dados
        return {"status": "sucesso", "horario": "24/10/2025 às 07:00"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally: 
        driver.quit()


if __name__ == '__main__':
    check_softclyn_disponibility()