import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from datetime import timedelta

def verify_doctors_calendar(
        medico: str, 
        data_desejada: str | None = None,
        horario_desejado: str | None = None,
        horario_inicial: str | None = None,
        horario_final: str | None = None
):
    """
    Verifica a disponibilidade da agenda de um médico.
    """

    service = Service(
        executable_path="/usr/bin/chromedriver",
        log_output="/code/chromedriver.log",  # Salva o log na pasta /code
        service_args=["--verbose"]            # Ativa o modo verbose
    )
    

    options = Options()
    options.binary_location = "/usr/bin/google-chrome"
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
    
    WAIT_TIME_SHORT = 5
    WAIT_TIME_LONG = 30 

    print("Iniciando driver com logging verbose...")    
    try:
        driver = webdriver.Chrome(service=service, options=options)
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

        wait = WebDriverWait(driver, WAIT_TIME_LONG) 
        
        print(f"Navigating to: {URL_BASE}")
        driver.get(URL_BASE)

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

        print("Waiting for modal...")

        try:
            modal_wait = WebDriverWait(driver, 5)
            print("Waiting for modal...")
            modal = modal_wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'bootbox')))
            print("Modal found, waiting for OK button...")
            ok_button = modal_wait.until(
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
        
        print("Iniciando fluxo de verificação de agenda...")

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
        medico_limpo = medico.strip()
        search_field.send_keys(medico_limpo)
        
        medico_option_xpath = f"//li[contains(@class, 'select2-results__option')]"
        medico_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, medico_option_xpath))
        )
        medico_option.click()

        print(f"Profissional selecionado: {medico}")

        if data_desejada and horario_desejado: 
            try:
                data_obj = datetime.strptime(data_desejada, '%d/%m/%Y').date()
                data_formatada_iso = data_obj.strftime('%Y-%m-%d')
                print(f"Convertendo data {data_desejada} para {data_formatada_iso} (ISO) para envio via JS.")
            except ValueError:
                print(f"ERRO: Data desejada '{data_desejada}' não está no formato dd/mm/yyyy.")
                return {"status": "error", "message": "Data em formato inválido."}

            try:
                dateAppointment = wait.until(EC.presence_of_element_located((By.ID, "dataAgenda")))
                driver.execute_script("arguments[0].value = arguments[1];", dateAppointment, data_formatada_iso)
                driver.execute_script("arguments[0].dispatchEvent(new Event('blur'));", dateAppointment)
                print(f"Data {data_formatada_iso} injetada e 'onblur' disparado.")
            except Exception as e:
                print(f"Erro ao tentar injetar data com JavaScript: {e}")
                driver.save_screenshot("debug_data_javascript_falhou_1.png")
                return {"status": "error", "message": "Falha ao definir data com JavaScript."}

            try:
                aba_agenda = wait.until(EC.presence_of_element_located((By.ID, "abaAgenda")))
                driver.execute_script("arguments[0].click();", aba_agenda)
            except Exception as e:
                print(f"Erro ao tentar clicar em abaAgenda via JS: {e}")
                return {"status": "error", "message": "Falha ao clicar na aba de agenda."}

            try:
                wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//tr[@id='070000']")),
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'alert-info') and contains(text(), 'expediente')]"))
                    )
                )
                print(f"Grade de horários para {data_desejada} (re)carregada.")
            except TimeoutException:
                print(f"A grade de horários para {data_desejada} não carregou.")
                return {"status": "error", "message": "Falha ao carregar a grade de horários."}

            print(f"Data selecionada: {data_desejada}")

            try:
                no_expediente_div = driver.find_element(By.XPATH, "//div[@class='alert alert-info' and contains(text(), 'Não há expediente neste dia!')]")
                if no_expediente_div:
                    print(f"A data {data_desejada} é um fim de semana ou feriado.")
                    return {"status": "unavailable", "message": f"A data {data_desejada} não tem expediente."}
            except NoSuchElementException:
                pass 

            horario_id = horario_desejado.replace(":", "") + "00" 

            try:
                horario_tr_xpath = f"//tr[@id='{horario_id}']"
                driver.find_element(By.XPATH, horario_tr_xpath)
                print(f"Linha de horário {horario_desejado} (ID: {horario_id}) encontrada na grade.")
            except NoSuchElementException:
                print(f"ERRO: A linha de horário {horario_desejado} (ID: {horario_id}) não existe na grade para este dia.")
                return {"status": "unavailable", "message": f"Horário {horario_desejado} não existe na grade para {data_desejada}."}

            elementos_filhos_xpath = f"//tr[@id='{horario_id}']/td[2]/*"
            elementos_filhos = driver.find_elements(By.XPATH, elementos_filhos_xpath)

            if len(elementos_filhos) > 0:
                print(f"O horário {horario_desejado}, formatado como {horario_id}, do dia {data_desejada} está OCUPADO.")
                return {"status": "unavailable", "message": f"Horário {horario_desejado} em {data_desejada} indisponível."}
            else:
                print(f"O horário {horario_desejado}, formatado como {horario_id}, do dia {data_desejada} está DISPONÍVEL para o profissional {medico}.")
                return {"status": "success", "message": f"Horário {horario_desejado} em {data_desejada} disponível."}

        elif data_desejada:
            try:
                data_obj = datetime.strptime(data_desejada, '%d/%m/%Y').date()
                data_formatada_iso = data_obj.strftime('%Y-%m-%d')
                print(f"Convertendo data {data_desejada} para {data_formatada_iso} (ISO) para envio via JS.")
            except ValueError:
                print(f"ERRO: Data desejada '{data_desejada}' não está no formato dd/mm/yyyy.")
                return {"status": "error", "message": "Data em formato inválido."}

            try:
                dateAppointment = wait.until(EC.presence_of_element_located((By.ID, "dataAgenda")))
                driver.execute_script("arguments[0].value = arguments[1];", dateAppointment, data_formatada_iso)
                driver.execute_script("arguments[0].dispatchEvent(new Event('blur'));", dateAppointment)
                print(f"Data {data_formatada_iso} injetada e 'onblur' disparado.")
            except Exception as e:
                print(f"Erro ao tentar injetar data com JavaScript: {e}")
                driver.save_screenshot("debug_data_javascript_falhou_2.png")
                return {"status": "error", "message": "Falha ao definir data com JavaScript."}

            print(f"Data selecionada: {data_desejada}")

            try:
                aba_agenda = wait.until(EC.presence_of_element_located((By.ID, "abaAgenda")))
                driver.execute_script("arguments[0].click();", aba_agenda)
            except Exception as e:
                print(f"Erro ao tentar clicar em abaAgenda via JS: {e}")
                return {"status": "error", "message": "Falha ao clicar na aba de agenda."}

            try:
                wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//tr[@id='070000']")),
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'alert-info') and contains(text(), 'expediente')]"))
                    )
                )
                print(f"Grade de horários para {data_desejada} (re)carregada.")
            except TimeoutException:
                print(f"A grade de horários para {data_desejada} não carregou.")
                return {"status": "error", "message": "Falha ao carregar a grade de horários."}

            print(f"Data selecionada: {data_desejada}. Verificando horários entre {horario_inicial} e {horario_final}.")

            try:
                driver.find_element(By.XPATH, "//div[@class='alert alert-info' and contains(text(), 'Não há expediente neste dia!')]")
                return {"status": "unavailable", "message": f"A data {data_desejada} não tem expediente."}
            except NoSuchElementException:
                pass

            horario_inicial_id = int((horario_inicial or "07:00").replace(":", "") + "00")
            horario_final_id = int((horario_final or "19:30").replace(":", "") + "00")

            elementos_filhos_xpath = f"//tr[@class='ui-droppable' and normalize-space(td[2]) = '' and not(td[2]/*)]"
            elementos_filhos = driver.find_elements(By.XPATH, elementos_filhos_xpath)   

            available_times = []

            for slot_tr in elementos_filhos:
                slot_id = slot_tr.get_attribute("id")
                print(f"Id do slot: {slot_id}, inicial: {horario_inicial_id}, final: {horario_final_id}")
                if slot_id and (int(slot_id) >= horario_inicial_id) and (int(slot_id) <= horario_final_id):
                    available_times.append(slot_tr.find_element(By.TAG_NAME, "a").text)
            
            return {"status": "success", "date": data_desejada, "slots": available_times}
        else: 
            for i in range(365): 
                check_date_str_display = current_date.strftime("%d/%m/%Y")
                check_date_iso = current_date.strftime("%Y-%m-%d")
                
                try:
                    dateAppointment = wait.until(EC.presence_of_element_located((By.ID, "dataAgenda")))
                    driver.execute_script("arguments[0].value = arguments[1];", dateAppointment, check_date_iso)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('blur'));", dateAppointment)
                except Exception as e:
                    print(f"Erro ao injetar data {check_date_iso} via JS: {e}. Pulando dia.")
                    driver.save_screenshot(f"debug_js_loop_fail_{check_date_iso}.png")
                    current_date += timedelta(days=1)
                    continue 
                
                try:
                    aba_agenda = wait.until(EC.presence_of_element_located((By.ID, "abaAgenda")))
                    driver.execute_script("arguments[0].click();", aba_agenda)
                except Exception as e:
                    print(f"Erro ao tentar clicar em abaAgenda via JS: {e}")
                    current_date += timedelta(days=1)
                    continue

                try:
                    wait.until(
                        EC.any_of(
                            EC.presence_of_element_located((By.XPATH, "//tr[@id='070000']")),
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'alert-info') and contains(text(), 'expediente')]"))
                        )
                    )
                except TimeoutException:
                    print(f"A grade de horários para {check_date_str_display} não carregou (Timeout). Pulando.")
                    current_date += timedelta(days=1)
                    continue
                
                print(f"Verificando data: {check_date_str_display}")
                
                is_working_day = True
                try:
                    driver.find_element(By.XPATH, "//div[@class='alert alert-info' and contains(text(), 'Não há expediente neste dia!')]")
                    is_working_day = False
                except NoSuchElementException:
                    pass 

                if is_working_day:
                    print(f"Data {check_date_str_display} é um dia de trabalho. Verificando horários...")
                    try:
                        available_slot_xpath = "//a[starts-with(@href, 'javascript:marcaHorarioAgenda')]"
                        
                        short_wait = WebDriverWait(driver, WAIT_TIME_SHORT)
                        
                        available_slots = short_wait.until(
                            EC.presence_of_all_elements_located((By.XPATH, available_slot_xpath))
                        )
                        
                        if available_slots:
                            next_time = available_slots[0].text
                            print(f"Próximo horário disponível encontrado: {next_time} em {check_date_str_display}")
                            return {"status": "success", "date": check_date_str_display, "time": next_time}
                        else:
                            print(f"Nenhum horário vago encontrado em {check_date_str_display}.")
                    except TimeoutException:
                         print(f"Nenhum horário vago encontrado em {check_date_str_display}.")
                    except NoSuchElementException:
                        pass 
                else:
                    print(f"Data {check_date_str_display} é um fim de semana ou feriado.")

            current_date += timedelta(days=1)
                
            return {"status": "not_found", "message": "Nenhum horário disponível encontrado no próximo ano."}

    except TimeoutException as e:
        print(f"Erro: Timeout! O elemento não foi encontrado a tempo. {e}")
        driver.save_screenshot("error_screenshot_verify.png")
        return {"status": "error", "message": f"A timeout occurred: {e}"}
    except Exception as e:
        print(f"Erro inesperado: {e}")
        driver.save_screenshot("error_screenshot_verify.png")
        return {"status": "error", "message": str(e)}
    finally:
        print("Fechando o navegador.")
        if 'driver' in locals():
            driver.quit()
        else:
            print("Driver não encontrado.")
    

if __name__ == '__main__':
    medico_para_verificar = "Danielle Braga - Médico endocrinologista e metabologista "
    
    # Exemplo 1: Verificar um horário específico
    # resultado = verify_doctors_calendar(medico_para_verificar, data_desejada="24/10/2025", horario_desejado="14:00")
    # print(resultado)

    # Exemplo 2: Verificar todos os horários disponíveis em um dia (e intervalo)
    # resultado = verify_doctors_calendar(medico_para_verificar, data_desejada="24/10/2025", horario_inicial="10:00", horario_final="18:00")
    #print(resultado)

    # Exemplo 3: Procurar o próximo horário livre (sem data)
    # resultado = verify_doctors_calendar(medico_para_verificar)
    # print(resultado)