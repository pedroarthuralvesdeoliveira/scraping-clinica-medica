import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoAlertPresentException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

def cancel_appointment(medico, data_desejada, horario_desejado, nome_paciente):
    """
    Cancels an appointment in SoftClyn.
    """
    debugger_address = 'localhost:9222'

    options = Options()
    options.add_experimental_option("debuggerAddress", debugger_address)
    
    prefs = {
         "profile.default_content_setting_values.notifications": 0
         }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()

    URL = os.environ.get("SOFTCLYN_URL")
    USER = os.environ.get("SOFTCLYN_USER")
    PASSWORD = os.environ.get("SOFTCLYN_PASS")
    
    try:
        wait = WebDriverWait(driver, 30)
        
        print(f"Navigating to: {URL}")
        driver.get(URL)

        print("Waiting for page to load...")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        user = wait.until(EC.element_to_be_clickable((By.ID, "usuario")))
        user.send_keys(USER)

        password = wait.until(EC.presence_of_element_located((By.ID, "senha")))
        password.send_keys(PASSWORD)
   
        login = wait.until(EC.element_to_be_clickable((By.ID, "btLogin")))
        login.click()

        time.sleep(5)

        try:
            print("Waiting for modal...")
            modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'bootbox')))
            print("Modal found, waiting for OK button...")
            ok_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-bb-handler="ok"]'))
            )
            try:
                ok_button.click()
            except ElementClickInterceptedException:
                print("OK button click intercepted, using JavaScript...")
                driver.execute_script("arguments[0].click();", ok_button)
            wait.until(
                EC.invisibility_of_element_located((By.CLASS_NAME, 'bootbox'))
            )
            print("Modal closed successfully.")
        except TimeoutException:
            print("No modal found or already closed, proceeding...")
        
        print("Iniciando fluxo de cancelamento...")
        
        select_doctor_clickable = wait.until(
            EC.element_to_be_clickable((By.ID, "select2-medico-container"))
        )
        select_doctor_clickable.click()
        
        search_field = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='select2-search__field']"))
        )
        medico_limpo = medico.strip()
        search_field.send_keys(medico_limpo)
        
        medico_option_xpath = f"//li[contains(@class, 'select2-results__option') and normalize-space()='{medico_limpo}']"
        
        medico_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, medico_option_xpath))
        )
        medico_option.click()

        print(f"Profissional selecionado: {medico}")

        time.sleep(2)

        dateAppointment = wait.until(EC.element_to_be_clickable((By.ID, "dataAgenda")))
        dateAppointment.clear()
        dateAppointment.send_keys(data_desejada)
        dateAppointment.send_keys(Keys.TAB)

        time.sleep(3)
        
        print(f"Data selecionada: {data_desejada}")

        horario_id = horario_desejado.replace(":", "") + "00"

        cancel_span_xpath = f"//tr[@id='{horario_id}']//span[contains(@onclick, '{nome_paciente}') and contains(@class, 'glyphicon-trash')]"

        try:
            cancel_span = wait.until(
                EC.presence_of_element_located((By.XPATH, cancel_span_xpath))
            )
            
            driver.execute_script("arguments[0].click();", cancel_span)
            print(f"Ícone de cancelamento para o paciente {nome_paciente} no horário {horario_desejado} clicado.")

            time.sleep(2)

            desmarcado_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-bb-handler='danger']"))
            )
            desmarcado_button.click()
            print("Botão 'Desmarcado' clicado.")

            time.sleep(2)

            reason_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.bootbox-input-text"))
            )
            reason_input.send_keys("não disse o motivo")
            print("Motivo do cancelamento preenchido.")

            time.sleep(1)

            confirm_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-bb-handler='confirm']"))
            )
            confirm_button.click()
            print("Botão de confirmação do motivo clicado.")

        except TimeoutException:
            print(f"Erro: Não foi possível encontrar o agendamento para o paciente {nome_paciente} no horário {horario_desejado}.")
            return {"status": "error", "message": "Agendamento não encontrado."}

        time.sleep(5)
        
        print("Cancelamento concluído com sucesso!")
        return {"status": "success", "message": "Agendamento cancelado."}

    except TimeoutException as e:
        print(f"Erro: Timeout! O elemento não foi encontrado a tempo. {e}")
        driver.save_screenshot("error_screenshot_cancel.png")
        return {"status": "error", "message": f"A timeout occurred: {e}"}
    except Exception as e:
        print(f"Erro inesperado: {e}")
        driver.save_screenshot("error_screenshot_cancel.png")
        return {"status": "error", "message": str(e)}
    finally:
        print("Fechando o navegador.")
        driver.quit()

if __name__ == '__main__':
    medico_para_cancelar = "Danielle Braga - Médico endocrinologista e metabologista "
    data_do_cancelamento = "24/10/2025"
    horario_do_cancelamento = "13:00"
    paciente_para_cancelar = "Denis Bechelli da Costa"
    
    resultado = cancel_appointment(
        medico_para_cancelar,
        data_do_cancelamento,
        horario_do_cancelamento,
        paciente_para_cancelar,
    )
    print(resultado)
