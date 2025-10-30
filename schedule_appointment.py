import os 
from datetime import datetime
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.keys import Keys

from webdriver_manager.chrome import ChromeDriverManager


def schedule_appointment(medico: str, data_desejada: str, paciente_info: dict, horario_desejado: str | None = None, tipo_atendimento: str | None = "Primeira vez"):
    """
    Executa a automação de agendamento no SoftClyn.
    """
    
    options = Options()
    options.add_argument("--lang=pt-BR")
    # options.add_argument("--headless=new")
    # options.add_argument("--no-sandbox") # Necessário para rodar como root/em containers
    # options.add_argument("--disable-dev-shm-usage") # Necessário para alguns ambientes Linux
    # options.add_argument("--window-size=1920,1080")
    
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

        dateAppointment = wait.until(EC.element_to_be_clickable((By.ID, "dataAgenda")))
        # dateAppointment.clear()
        # dateAppointment.send_keys(data_desejada)

        # appointments_grid = wait.until(
        #     EC.element_to_be_clickable((By.ID, "abaAgenda"))
        # )
        # appointments_grid.click()

        # dateAppointment.send_keys(Keys.TAB) 
        # print(f"Data selecionada: {data_desejada}") 

        # print(f"Validando se o horário {horario_desejado} está disponível...")

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
        
        try:
            horario_id = horario_desejado.replace(":", "") + "00"
        except Exception as e:
            print(f"Erro ao formatar o horário: {e}")
            raise ValueError("Formato de horário inválido. Esperado HH:MM")

        try:
            horario_tr_xpath = f"//tr[@id='{horario_id}']"
            wait.until(EC.presence_of_element_located((By.XPATH, horario_tr_xpath)))
            
        except TimeoutException:
            print(f"Erro: A linha de horário {horario_desejado} (ID: {horario_id}) não foi encontrada.")
            return {"status": "error", "message": f"Horário {horario_desejado} não existe na grade."}

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

        select_type_of_search = wait.until(
            EC.element_to_be_clickable((By.ID, "tipoPesquisaPaciente"))
        )
        select_type_of_search.click()

        select = Select(select_type_of_search)
        select.select_by_value("cpf")

        cpf_paciente = paciente_info['cpf']
        campo_pesquisa_paciente = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Digite o Nome do Paciente para Pesquisar']"))
        )
        campo_pesquisa_paciente.send_keys(cpf_paciente)
        campo_pesquisa_paciente.send_keys(Keys.ENTER)
        print(f"Pesquisando paciente: {cpf_paciente}")

        try:
            paciente_encontrado_xpath = "//td[contains(@onclick, 'selecionaPacienteAgenda')]"
            paciente_encontrado = wait.until(
                EC.element_to_be_clickable((By.XPATH, paciente_encontrado_xpath))
            )
            paciente_encontrado.click()
            print(f"Paciente com CPF {cpf_paciente} encontrado e selecionado.")

        except TimeoutException:
            print(f"Paciente com CPF {cpf_paciente} não encontrado. Iniciando criação de novo paciente.")
            
            criar_paciente_xpath = "//td[contains(@onclick, 'adicionaPacienteNovoAgenda')]"
            criar_paciente_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, criar_paciente_xpath))
            )
            criar_paciente_button.click()

            # Nome
            nome_paciente_input = wait.until(EC.element_to_be_clickable((By.ID, "nomePaciente")))
            nome_paciente_input.clear()
            nome_paciente_input.send_keys(paciente_info['nome'])
            print(f"Nome preenchido: {paciente_info['nome']}")

            # Data de Nascimento
            data_nascimento_input = wait.until(EC.element_to_be_clickable((By.ID, "dataNascimentoAgenda")))
            data_nascimento_input.send_keys(paciente_info['data_nascimento'])
            print(f"Data de nascimento preenchida: {paciente_info['data_nascimento']}")
            
            # Telefone
            telefone_paciente_input = wait.until(EC.element_to_be_clickable((By.ID, "numeroTelefone")))
            telefone_paciente_input.click()  
            telefone_paciente_input.clear()  
            telefone_paciente_input.send_keys(paciente_info["telefone"])
            if telefone_paciente_input.text == "":
                telefone_paciente_input = wait.until(EC.presence_of_element_located((By.ID, "numeroTelefone")))
                telefone_val = paciente_info["telefone"]
                driver.execute_script("arguments[0].value = arguments[1];", telefone_paciente_input, telefone_val)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", telefone_paciente_input)
            print(f"Telefone preenchido: {paciente_info["telefone"]}")

            # CPF
            cpf_selector = "input[id='cpfPaciente'][type='text']"
            
            cpf_paciente_input = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, cpf_selector))
            )
            
            cpf_paciente_input.click()
            cpf_paciente_input.clear() 
            cpf_paciente_input.send_keys(paciente_info["cpf"])
            print(f"CPF preenchido: {paciente_info['cpf']}")

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

            botao_salvar = wait.until(
                EC.element_to_be_clickable((By.ID, "btSalvarAgenda"))
            )
            botao_salvar.click()
            print("Clicando em Salvar...")
            
            print("Agendamento concluído com sucesso!")
            return {"status": "success", "message": "Agendamento realizado."}

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

        botao_salvar = wait.until(
            EC.element_to_be_clickable((By.ID, "btSalvarAgenda"))
        )
        botao_salvar.click()
        print("Clicando em Salvar...")
        
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
        if 'driver' in locals():
            driver.quit()
        else: 
            print("Driver não encontrado.")
        

if __name__ == '__main__':
    medico_para_agendar = "Danielle Braga - Médico endocrinologista e metabologista"
    data_do_agendamento = "24/10/2025"
    horario_do_agendamento = "13:30"
    
    paciente_info = {
        "nome": "Paciente Teste",
        "data_nascimento": "10/10/1990",
        "cpf": "123.456.789-00",
        "telefone": "11999999999",
        "tipo_atendimento": "Consulta"
    }
    
    tipo_de_atendimento = "Consulta"
    
    resultado = schedule_appointment(
        medico_para_agendar,
        data_do_agendamento,
        horario_do_agendamento,
        paciente_info,
        tipo_de_atendimento
    )
    print(resultado)