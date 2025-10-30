import os
import time
from datetime import datetime
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

    options = Options()
    options.add_argument("--lang=pt-BR")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox") # Necessário para rodar como root/em containers
    options.add_argument("--disable-dev-shm-usage") # Necessário para alguns ambientes Linux
    options.add_argument("--window-size=1920,1080")

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

        print("Logging in...")
   
        try:
            login_button = wait.until(
                EC.presence_of_element_located((By.ID, "btLogin"))
            )
            print("Botão 'btLogin' encontrado. Forçando clique via JavaScript...")
            
            driver.execute_script("arguments[0].click();", login_button)

        except TimeoutException:
            print("ERRO: Timeout! Não foi possível encontrar 'btLogin' (nem pela presença).")
            raise 

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

        dateAppointment = wait.until(EC.presence_of_element_located((By.ID, "dataAgenda")))

        try:
            data_obj = datetime.strptime(data_desejada, '%d/%m/%Y')
            
            data_formatada_para_input = data_obj.strftime('%Y-%m-%d')
            
            print(f"Convertendo data {data_desejada} para {data_formatada_para_input} (ISO) para envio via JS.")
            
        except ValueError:
            print(f"ERRO: Não foi possível converter a data '{data_desejada}'.")
            return {"status": "error", "message": "Data em formato inválido."}

        try:
            driver.execute_script("arguments[0].value = arguments[1];", dateAppointment, data_formatada_para_input)
            print("Valor da data injetado via JavaScript.")

            print("Disparando 'onblur' via JavaScript para carregar a grade...")
            driver.execute_script("arguments[0].dispatchEvent(new Event('blur'));", dateAppointment)

        except Exception as e:
            print(f"Erro ao tentar injetar data com JavaScript: {e}")
            driver.save_screenshot("debug_data_javascript_falhou.png")
            return {"status": "error", "message": "Falha ao definir data com JavaScript."}

        valor_final_campo = dateAppointment.get_attribute("value")
        print(f"Valor final no campo de data (value property): '{valor_final_campo}' (Esperado: '{data_formatada_para_input}')")
        
        if valor_final_campo != data_formatada_para_input:
             print("ALERTA: O valor final no campo não corresponde ao esperado após injeção de JS!")
        
        print(f"Data selecionada (original): {data_desejada}")

        try:
              wait.until(
                  EC.any_of(
                      EC.presence_of_element_located((By.XPATH, "//tr[@id='070000']")),
                      EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'alert-info') and contains(text(), 'expediente')]"))
                  )
              )
              print("Grade de horários ou mensagem de expediente (re)carregada após JS.")
        except TimeoutException:
              print("ERRO: A grade não recarregou após a injeção de JS. Verifique o screenshot.")
              driver.save_screenshot("debug_data_nao_recarregou_js.png")
              return {"status": "error", "message": "Falha ao definir a data e recarregar a grade."}

        horario_id = horario_desejado.replace(":", "") + "00"

        cancel_span_xpath = f"//tr[@id='{horario_id}']//span[contains(@onclick, '{nome_paciente}') and contains(@class, 'glyphicon-trash')]"

        try:
            cancel_span = wait.until(
                EC.presence_of_element_located((By.XPATH, cancel_span_xpath))
            )
            
            driver.execute_script("arguments[0].click();", cancel_span)
            print(f"Ícone de cancelamento para o paciente {nome_paciente} no horário {horario_desejado} clicado.")

            desmarcado_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-bb-handler='danger']"))
            )
            desmarcado_button.click()
            print("Botão 'Desmarcado' clicado.")

            time.sleep(1)

            reason_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.bootbox-input-text"))
            )
            reason_input.click()
            reason_input.send_keys("não disse o motivo")
            print("Motivo do cancelamento preenchido.")

            confirm_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-bb-handler='confirm']"))
            )
            confirm_button.click()
            print("Botão de confirmação do motivo clicado.")

        except TimeoutException:
            print(f"Erro: Não foi possível encontrar o agendamento para o paciente {nome_paciente} no horário {horario_desejado}.")
            return {"status": "error", "message": "Agendamento não encontrado."}
        
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
        if 'driver' in locals():
            driver.quit()
        else:
            print("Driver não encontrado.")
        

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
