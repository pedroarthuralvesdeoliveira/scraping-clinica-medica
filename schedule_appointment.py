import time
import os 
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.keys import Keys

from webdriver_manager.chrome import ChromeDriverManager


def schedule_appointment(medico, data_desejada, horario_desejado, nome_paciente, convenio, tipo_atendimento):
    """
    Executa a automação de agendamento no SoftClyn.
    """
    
    debugger_address = 'localhost:9222' 

    options = Options()
    # options.add_argument("--headless=new")
    # options.add_argument("--window-size=1920,1080") 
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

        password  = wait.until(EC.presence_of_element_located((By.ID, "senha")))
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
        
        print("Iniciando fluxo de agendamento...")
        
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

        time.sleep(3)

        appointments_grid = wait.until(
            EC.element_to_be_clickable((By.ID, "abaAgenda"))
        )
        appointments_grid.click()

        time.sleep(3)

        dateAppointment.send_keys(Keys.TAB) 
        print(f"Data selecionada: {data_desejada}") 

        print(f"Validando se o horário {horario_desejado} está disponível...")
        
        try:
            horario_id = horario_desejado.replace(":", "") + "00"
        except Exception as e:
            print(f"Erro ao formatar o horário: {e}")
            raise ValueError("Formato de horário inválido. Esperado HH:MM")

        print(f"Horário formatado: {horario_id}")
        
        time.sleep(5) 

        try:
            horario_tr_xpath = f"//tr[@id='{horario_id}']"
            wait.until(EC.presence_of_element_located((By.XPATH, horario_tr_xpath)))
            
        except TimeoutException:
            print(f"Erro: A linha de horário {horario_desejado} (ID: {horario_id}) não foi encontrada.")
            return {"status": "error", "message": f"Horário {horario_desejado} não existe na grade."}

        time.sleep(5) 

        try:
            elementos_filhos_xpath = f"//tr[@id='{horario_id}']/td[2]/*"
            elementos_filhos = driver.find_elements(By.XPATH, elementos_filhos_xpath) 

            if len(elementos_filhos) > 0:
                print(f"Erro: O horário {horario_desejado} já está OCUPADO.")
                return {"status": "error", "message": f"Horário {horario_desejado} indisponível."}
            else:
                print(f"Horário {horario_desejado} está disponível. Continuando...")

        except Exception as e:
            print(f"Erro inesperado durante a validação do horário: {e}")
            driver.save_screenshot("error_screenshot_validacao.png")
            return {"status": "error", "message": str(e)}

        horario_xpath = f"//a[starts-with(@href, 'javascript:marcaHorarioAgenda') and normalize-space()='{horario_desejado}']"

        try:
            horario_slot = wait.until(
                EC.presence_of_element_located((By.XPATH, horario_xpath))
            )
       
            driver.execute_script("arguments[0].click();", horario_slot)
            
            print(f"Horário selecionado (via JS): {horario_desejado}")

        except TimeoutException:
            print(f"Erro: Não foi possível encontrar o horário {horario_desejado}.")
            print(f"Verifique se o horário está vago ou se o XPATH está correto: {horario_xpath}")
            raise 
        except Exception as e:
            print(f"Erro ao tentar clicar no horário: {e}")
            raise

        campo_pesquisa_paciente = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Digite o Nome do Paciente para Pesquisar']"))
        )
        campo_pesquisa_paciente.send_keys(nome_paciente)
        campo_pesquisa_paciente.send_keys(Keys.ENTER)
        print(f"Pesquisando paciente: {nome_paciente}")

        paciente_limpo = nome_paciente.strip()

        paciente_encontrado_xpath = (
            f"//td[contains(@onclick, 'selecionaPacienteAgenda') and "
            f"span[normalize-space()='{paciente_limpo}']]"
        )

        paciente_encontrado = wait.until(
            EC.element_to_be_clickable((By.XPATH, paciente_encontrado_xpath))
        )
        paciente_encontrado.click()
        print(f"Paciente selecionado: {nome_paciente}")

        time.sleep(2) 

        select_tipo_clickable = wait.until(
            EC.element_to_be_clickable((By.ID, "select2-tipoAtendimento-container"))
        )
        select_tipo_clickable.click()

        search_field_tipo = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='select2-search__field']"))
        )
        
        tipo_atendimento_limpo = tipo_atendimento.strip()
        search_field_tipo.send_keys(tipo_atendimento_limpo)

        tipo_option_xpath = f"//li[contains(@class, 'select2-results__option') and normalize-space()='{tipo_atendimento_limpo}']"
        
        tipo_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, tipo_option_xpath))
        )
        tipo_option.click()

        print(f"Tipo de Atendimento selecionado: {tipo_atendimento}")

        time.sleep(2) 

        botao_salvar = wait.until(
            EC.element_to_be_clickable((By.ID, "btSalvarAgenda"))
        )
        botao_salvar.click()
        print("Clicando em Salvar...")

        time.sleep(5) 
        
        print("Agendamento concluído com sucesso!")
        return {"status": "success", "message": "Agendamento realizado."}

    except TimeoutException as e:
        print(f"Erro: Timeout! O elemento não foi encontrado a tempo. {e}")
        driver.save_screenshot("error_screenshot.png")
        return {"status": "error", "message": f"A timeout occurred: {e}"}
    except Exception as e: 
        print(f"Erro inesperado: {e}")
        driver.save_screenshot("error_screenshot.png")
        return {"status": "error", "message": str(e)}
    finally: 
        print("Fechando o navegador.")
        driver.quit()

if __name__ == '__main__':    
    medico_para_agendar = "Danielle Braga - Médico endocrinologista e metabologista "
    data_do_agendamento = "24/10/2025"
    horario_do_agendamento = "13:00"
    paciente_para_agendar = "Denis Bechelli da Costa"
    convenio_do_paciente = "Particular"
    tipo_de_atendimento = "Consulta"
    
    resultado = schedule_appointment(
        medico_para_agendar,
        data_do_agendamento,
        horario_do_agendamento,
        paciente_para_agendar,
        convenio_do_paciente,
        tipo_de_atendimento
    )
    print(resultado)