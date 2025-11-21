import os 
import time
from datetime import datetime
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

from selenium.webdriver.common.keys import Keys

load_dotenv()


def _select_convenio_digitando(driver, wait, convenio_nome):
    """
    Seleciona um convênio digitando o nome no campo select2 de 'convênio'.
    """
    print(f"Selecionando convênio: {convenio_nome}")

    select_convenio_clickable = wait.until(
        EC.element_to_be_clickable((By.ID, "select2-convenio-container"))
    )
    select_convenio_clickable.click()

    search_field_xpath = "//span[contains(@class,'select2-container--open')]//input[@class='select2-search__field']"
    search_field = wait.until(
        EC.element_to_be_clickable((By.XPATH, search_field_xpath))
    )

    search_field.clear()
    search_field.send_keys(convenio_nome.strip())
    time.sleep(1)  

    option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{convenio_nome.upper()}')]"
    option = wait.until(
        EC.element_to_be_clickable((By.XPATH, option_xpath))
    )

    option.click()
    print(f"Convênio '{convenio_nome}' selecionado com sucesso.")


def _select_tipo_atendimento(driver, wait, tipo_atendimento):
    print(f"Selecionando tipo de atendimento: {tipo_atendimento}")
    select_tipo_clickable = wait.until(
        EC.element_to_be_clickable((By.ID, "select2-tipoAtendimento-container"))
    )
    select_tipo_clickable.click()

    search_field_xpath = "//span[contains(@class,'select2-container--open')]//input[@class='select2-search__field']"
    search_field = wait.until(
        EC.element_to_be_clickable((By.XPATH, search_field_xpath))
    )

    search_field.clear()
    search_field.send_keys(tipo_atendimento.strip())
    time.sleep(1)  

    option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{tipo_atendimento.upper()}')]"
    option = wait.until(
        EC.element_to_be_clickable((By.XPATH, option_xpath))
    )

    option.click()
    print(f"Tipo de Atendimento '{tipo_atendimento}' selecionado com Enter.")

def schedule_appointment(medico: str, data_desejada: str, paciente_info: dict, horario_desejado: str | None = None, tipo_atendimento: str | None = "Primeira vez"):
    """
    Executa a automação de agendamento no SoftClyn.
    """
    
    options = Options()
    options.add_argument("--lang=pt-BR")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox") # Necessário para rodar como root/em containers
    options.add_argument("--disable-dev-shm-usage") # Necessário para alguns ambientes Linux
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    prefs = {
        "profile.default_content_setting_values.notifications": 0
    }
    options.add_experimental_option("prefs", prefs)
    
    print("Iniciando driver com logging verbose...")
    try:
        driver = webdriver.Chrome(options=options)
        print("Driver iniciado com sucesso.")
    except Exception as e:
        print(f"ERRO IMEDIATO AO INICIAR O DRIVER: {e}")
        raise e

    is_endoclin_of = False

    URL = os.environ.get("SOFTCLYN_URL")
    LOGIN = os.environ.get("SOFTCLYN_LOGIN_PAGE")

    medicos_endoclin_of = ["ANDRÉ A. S. BAGANHA", "JOAO R.C.MATOS"]

    URL_BASE = f"{URL}/endoclin_ouro/{LOGIN}"

    for dr in medicos_endoclin_of:
        if medico.upper() in dr.upper():
            URL_BASE = f"{URL}/endoclin_of/{LOGIN}"
            is_endoclin_of = True   
            break
    
    USER = os.environ.get("SOFTCLYN_USER")
    PASSWORD = os.environ.get("SOFTCLYN_PASS")
    
    try: 
        driver.set_page_load_timeout(30)
        
        wait = WebDriverWait(driver, 30) 
        
        print(f"Navigating to: {URL_BASE}")
        driver.get(URL_BASE)

        print("Aguardando o campo 'usuario' (ID: usuario)...")
        try:
            user = wait.until(
                EC.presence_of_element_located((By.ID, "usuario"))
            )
            print("Campo 'usuario' encontrado. Preenchendo...")
            user.send_keys(USER)
        
        except TimeoutException:
            print("ERRO: Timeout! O campo 'usuario' não apareceu na página de login.")
            raise 

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
            modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'modal')))
            print("Modal found, waiting for OK button...")
            ok_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-dismiss="modal"]'))
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

        if is_endoclin_of:
            menu = wait.until(EC.element_to_be_clickable((By.ID, "menuAtendimentoLi")))
            menu.click()

            print("Clicando em 'Agendamento' no menu...")

            agendamento = wait.until(
                EC.element_to_be_clickable((By.ID, "M1"))
            )
            agendamento.click()

            print("Entrou na tela de agendamento.")

            time.sleep(2)  
       
        select_doctor_clickable = wait.until(
            EC.element_to_be_clickable((By.ID, "select2-medico-container"))
        )
        select_doctor_clickable.click()
        
        search_field = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='select2-search__field']"))
        )

        medico_limpo = medico.replace("Dr.", "").replace("Dra.", "").strip()
        search_field.send_keys(medico_limpo)
        
        medico_option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{medico_limpo.upper()}')]"
        
        medico_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, medico_option_xpath))
        )
        medico_option.click()

        print(f"Profissional selecionado: {medico}")

        dateAppointment = wait.until(EC.element_to_be_clickable((By.ID, "dataAgenda")))

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

            # Data de Nascimento
            data_nascimento_input = wait.until(EC.element_to_be_clickable((By.ID, "dataNascimentoAgenda")))
            data_nascimento_input.send_keys(paciente_info['data_nascimento'])
            print(f"Data de nascimento preenchida: {paciente_info['data_nascimento']}")
            
            # Telefone
            telefone_input = wait.until(EC.presence_of_element_located((By.ID, "numeroTelefone")))
            telefone_val = paciente_info["telefone"]
            driver.execute_script("arguments[0].value = arguments[1];", telefone_input, telefone_val)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", telefone_input)
            print(f"Telefone preenchido: {paciente_info['telefone']}")

            # CPF
            cpf_selector = "input[id='cpfPaciente'][type='text']"
            cpf_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, cpf_selector)))
            driver.execute_script("arguments[0].value = arguments[1];", cpf_input, paciente_info["cpf"])
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", cpf_input)
            print(f"CPF preenchido: {paciente_info['cpf']}")

            _select_convenio_digitando(driver, wait, paciente_info['convenio'])

            _select_tipo_atendimento(driver, wait, tipo_atendimento)

            print("Corrigindo o campo 'Nome' como última ação antes de salvar...")
            nome_paciente_input = wait.until(EC.presence_of_element_located((By.ID, "nomePaciente")))
            nome_val = paciente_info["nome"]
            driver.execute_script("arguments[0].value = arguments[1];", nome_paciente_input, nome_val)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", nome_paciente_input)
            print(f"Nome final definido como: {nome_val}")

            time.sleep(5)
            
            botao_salvar = wait.until(
                EC.element_to_be_clickable((By.ID, "btSalvarAgenda"))
            )
            driver.execute_script("arguments[0].click();", botao_salvar)
            print("Clicando em 'Salvar' via JS...")

            time.sleep(2)  # Espera para garantir que o paciente foi salvo
            return {"status": "success", "message": "Agendamento de novo paciente realizado."}

        
        if paciente_info['convenio']:
            _select_convenio_digitando(driver, wait, paciente_info['convenio'])

        _select_tipo_atendimento(driver, wait, tipo_atendimento)

        botao_salvar = wait.until(
            EC.element_to_be_clickable((By.ID, "btSalvarAgenda"))
        )
        driver.execute_script("arguments[0].click();", botao_salvar)
        print("Clicando em 'Salvar' via JS...")
        time.sleep(2)  # Espera para garantir que o paciente foi salvo
        
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
        paciente_info,
        horario_do_agendamento,
        tipo_de_atendimento,
    )
    print(resultado)