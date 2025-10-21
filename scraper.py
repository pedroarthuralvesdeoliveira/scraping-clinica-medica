import time
import os 
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


from webdriver_manager.chrome import ChromeDriverManager

def check_softclyn_disponibility():
    """
    Executa a automação completa no SoftClyn e retorna o próximo horário.
    """

    # Configuração do WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()

    URL = os.environ.get("SOFTCLYN_URL")
    USER = os.environ.get("SOFTCLYN_USER")
    PASSWORD = os.environ.get("SOFTCLYN_PASS")
    
    try: 
        driver.get(URL)
        wait = WebDriverWait(driver, 10)

        time.sleep(5)

        campo_usuario = wait.until(EC.presence_of_element_located((By.ID, "usuario")))
        campo_usuario.send_keys(USER)

        campo_senha = wait.until(EC.presence_of_element_located((By.ID, "senha")))
        campo_senha.send_keys(PASSWORD)
   
        botao_login = wait.until(EC.element_to_be_clickable((By.ID, "btLogin")))
        botao_login.click()

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

        time.sleep(5)

        menu_relatorios = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Relatórios")))

        actions = ActionChains(driver)
        actions.move_to_element(menu_relatorios).click().perform()

        submenu_hover = wait.until(EC.visibility_of_element_located((By.ID, "menuRelatorioAgendaLi")))
        actions.move_to_element(submenu_hover).perform()

        link_final_agendamentos = wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//a[contains(@href, 'relAgendamentos.php')]")
        ))

        actions.click(link_final_agendamentos)
        actions.perform()

        seletor_botao_dropdown = "//select[@id='medico']/following-sibling::div/button"
        
        botao_dropdown = wait.until(
            EC.element_to_be_clickable((By.XPATH, seletor_botao_dropdown))
        )
        botao_dropdown.click()

        seletor_opcao_todos = "//li[contains(@class, 'multiselect-all')]//label[contains(text(), 'Todos')]"
        opcao_todos = wait.until(
            EC.element_to_be_clickable((By.XPATH, seletor_opcao_todos))
        )
        opcao_todos.click()

        time.sleep(3)

        initialDate = wait.until(
            EC.element_to_be_clickable((By.ID, "dataInicial"))
        )
        initialDate.click()

        time.sleep(3)

        botao_exportar = wait.until(
            EC.element_to_be_clickable((By.ID, "exportaExcel"))
        )
    
        botao_exportar.click()

        time.sleep(10)

        # Se tudo deu certo, retorne os dados
        return {"status": "sucesso", "horario": "24/10/2025 às 07:00"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally: 
        driver.quit()


if __name__ == '__main__':
    check_softclyn_disponibility() 