from selenium.common import StaleElementReferenceException
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait


from app.scraper.base import Browser


class PatientHistoryScraper(Browser):
    def __init__(self):
        super().__init__()

    def go_to_next_page(self):
        try:
            # Selector específico para a paginação do histórico
            pagination_xpath = "//ul[@class='pagination'][.//a[contains(@href, 'scriptTrilhaAuditoriaAgenda')]]"
            
            # 1. Verifica se já está na última página
            if self.is_last_page():
                print("Já estamos na última página do histórico. Encerrando.")
                return False

            # 2. Busca o elemento atual DENTRO da paginação correta
            current_page_elem = self.wait_for_element(
                By.XPATH, 
                f"{pagination_xpath}//a[@class='paginaAtual']"
            )
            if not current_page_elem:
                return False
            
            current_val = int(current_page_elem.get_attribute("data-value"))
            next_val = current_val + 1
            
            print(f"Navegando: da página {current_val + 1} para {next_val + 1}")

            # 3. Dispara o script (AJAX)
            self.execute_script(f"scriptTrilhaAuditoriaAgenda.pesquisaPorPagina({next_val});")

            # 4. Aguarda a página atualizar (o data-value do elemento paginaAtual deve mudar)
            def wait_for_page_change(driver):
                try:
                    elem = driver.find_element(By.XPATH, f"{pagination_xpath}//a[@class='paginaAtual']")
                    return int(elem.get_attribute("data-value")) == next_val
                except:
                    return False

            WebDriverWait(self.driver, 10).until(wait_for_page_change)
            print(f"Página {next_val + 1} carregada com sucesso.")
            
            return True

        except Exception as e:
            print(f"Erro na navegação do histórico: {e}")
            self.save_screenshot("patient_history_navigate_error.png")
            return False

    def is_last_page(self):
        import re
        try:
            pagination_xpath = "//ul[@class='pagination'][.//a[contains(@href, 'scriptTrilhaAuditoriaAgenda')]]"
            
            # Encontrar a página atual no componente correto
            current_page_elements = self.find_elements(By.XPATH, f"{pagination_xpath}//a[@class='paginaAtual']")
            if not current_page_elements:
                return True
            
            current_page_elem = current_page_elements[0]
            
            # Encontrar o botão "Última" no componente correto
            last_page_elements = self.find_elements(By.XPATH, f"{pagination_xpath}//a[contains(text(), 'Última')]")
            if not last_page_elements:
                return True
            
            last_page_elem = last_page_elements[0]
            current_href = current_page_elem.get_attribute("href")
            last_href = last_page_elem.get_attribute("href")
            
            # Regra 1: Comparação de href
            if current_href and last_href and current_href == last_href:
                print(f"Fim da paginação (href): {current_href}")
                return True

            # Regra 2: Extrair total de "Última (N)"
            match = re.search(r'\((\d+)\)', last_page_elem.text)
            if match:
                total_pages = int(match.group(1))
                current_text = current_page_elem.text.strip()
                if current_text.isdigit() and int(current_text) >= total_pages:
                    print(f"Fim da paginação (texto): {current_text} de {total_pages}")
                    return True
                
            # Regra 3: Botão "Next" aponta para a mesma página atual (ou não existe)
            next_page_elements = self.find_elements(By.XPATH, f"{pagination_xpath}//a[@aria-label='Next']")
            if not next_page_elements:
                return True
            
            next_href = next_page_elements[0].get_attribute("href")
            if next_href == current_href:
                print("Fim da paginação (Next button mesmo href)")
                return True
                
            return False
        except Exception as e:
            print(f"Erro is_last_page: {e}")
            return True

    def prepare_patient_search(self, force_login=False, patient_type: str ="cpf"):
        """
        Navigates to the patient search screen.
        If force_login is True, it will perform login even if already logged in.
        """
        try:
            current_url = self.driver.current_url or ""
            if force_login or "softclyn.com" not in current_url or "login" in current_url:
                print(f"Login required (current URL: {current_url}). Logging in...")
                self._login(medico=None)
                self._close_modal()
                self._click_on_appointment_menu()

                print("Navigating to patient history search screen...")
                pesquisa_paciente_xpath = "//a[@href='#divPesquisaPaciente' and contains(text(),'Pesquisa Paciente')]"
                prontuario_menu = self.wait_for_element(By.XPATH, pesquisa_paciente_xpath)
                if prontuario_menu:
                    try:
                        prontuario_menu.click()
                    except:
                        self.execute_script("arguments[0].click();", prontuario_menu)

            search_patient_elem = self.wait_for_element(
                By.ID,
                "tipoPesquisaPacienteGrade",
                expectation=EC.element_to_be_clickable,
                timeout=20
            )

            if search_patient_elem:
                select = Select(search_patient_elem)
                # Normalize type (e.g., "cpf" -> "Cpf", "nome" -> "Nome")
                type_normalized = patient_type.capitalize() if patient_type.lower() in ["cpf", "nome"] else patient_type
                
                try:
                    select.select_by_visible_text(type_normalized)
                except:
                    select.select_by_value(patient_type.lower())
                
                time.sleep(1)
                print(f"Patient search screen ready (type: {type_normalized}).")
                return True
            
            print("Failed to find patient search field 'tipoPesquisaPacienteGrade'.")
            return False

        except Exception as e:
            print(f"Error preparing patient search: {e}")
            return False

    def get_patient_by_type(self, type: str, value: str):
        try:
            # Ensure we are on the search screen
            if not self.prepare_patient_search(patient_type=type):
                print("Failed to prepare patient search screen.")
                return None

            print(f"Searching for patient code for type: {type}")

            type_field = self.wait_for_element(By.ID, "pesquisaPacienteGrade")

            if type_field:
                type_field.clear()
                try:
                    type_field.send_keys(value)
                except:
                    self.execute_script(
                        "arguments[0].value = arguments[1];", type_field, value
                    )

                print(f"Type {type} entered in search field.")

                search_button = self.wait_for_element(
                    By.ID,
                    "btPesquisaPacienteGrade1",
                )

                time.sleep(2)

                if search_button:
                    try:
                        search_button.click()
                    except:
                        self.execute_script("arguments[0].click();", search_button)
                    print("Search button clicked.")
                else:
                    type_field.send_keys(Keys.ENTER)
                    print("ENTER sent to search.")
            else:
                print("Could not find type search field.")

            # Specific XPath for the results table cell containing the code
            # Usually the first column of the first row in the results table
            codigo_elem = self.find_element(
                By.XPATH,
                "//div[@id='divGradePesquisaPaciente']//table//tr[td and not(th)][1]/td[1]"
            )

            if codigo_elem:
                text = codigo_elem.text.strip()
                # Verify if it's actually a number to avoid "Caso não encontre..." messages
                if text.isdigit():
                    return text
                else:
                    print(f"  Found non-numeric text in code field: '{text}'")
                    return None
            else:
                return None
        except Exception as e:
            print(f"Error in get_patient_by_type: {e}")
            return None


    def get_patient_history(self, cpf: str):
        """
        Scrapes the patient's appointment history from the website.
        Returns a list of appointment dictionaries.
        """
        try:
            self._login(medico=None)

            self._close_modal()

            self._click_on_appointment_menu()

            print(f"Navigating to patient history search for CPF: {cpf}")

            pesquisa_paciente_xpath = "//a[@href='#divPesquisaPaciente' and contains(text(),'Pesquisa Paciente')]"
            prontuario_menu = self.wait_for_element(By.XPATH, pesquisa_paciente_xpath)
            if prontuario_menu:
                try:
                    prontuario_menu.click()
                except:
                    self.execute_script("arguments[0].click();", prontuario_menu)

            search_patient = self.wait_for_element(
                By.ID,
                "tipoPesquisaPacienteGrade",
                expectation=EC.element_to_be_clickable,
            )

            if search_patient:
                select = Select(search_patient)
                try:
                    select.select_by_visible_text("Cpf")
                except:
                    select.select_by_value("cpf")
                time.sleep(2)

            print("Entered patient history screen.")

            cpf_field = self.wait_for_element(By.ID, "pesquisaPacienteGrade")

            if cpf_field:
                cpf_field.clear()
                try:
                    cpf_field.send_keys(cpf)
                except:
                    self.execute_script(
                        "arguments[0].value = arguments[1];", cpf_field, cpf
                    )

                print(f"CPF {cpf} entered in search field.")
                # self.save_screenshot("patient_history_cpf_entered.png")

                search_button = self.wait_for_element(
                    By.ID,
                    "btPesquisaPacienteGrade1",
                )

                time.sleep(2)

                if search_button:
                    try:
                        search_button.click()
                    except:
                        self.execute_script("arguments[0].click();", search_button)
                    print("Search button clicked.")
                else:
                    cpf_field.send_keys(Keys.ENTER)
                    print("ENTER sent to search.")
            else:
                print("Could not find CPF search field.")

            time.sleep(2)

            botao_historico = self.wait_for_element(
                By.XPATH, "//button[@title='Visualizar Histórico do Paciente.']"
            )

            if botao_historico:
                try:
                    botao_historico.click()
                except:
                    self.execute_script("arguments[0].click();", botao_historico)
                print("Historical button clicked.")
            else:
                print("Could not find historical button.")

            time.sleep(0.5)

            appointments = []
            today_string = datetime.now().strftime("%d/%m/%Y")
            today = datetime.strptime(today_string, "%d/%m/%Y")
            max_pages = 100
            page_count = 0

            while True:
                page_count += 1
                print(f"Processing page {page_count}/{max_pages}")
                time.sleep(1)  

                self.wait_for_element(By.XPATH, "//table[contains(@class,'table-bordered')][.//td[contains(@class,'active')]]")

                tables = self.find_elements(
                    By.XPATH, 
                    # "//table[contains(@class,'table-bordered')]"
                    "//table[contains(@class,'table-bordered')][.//td[contains(@class,'active') and contains(., 'Profissional')]]"
                )

                for table in tables:
                    # profissional = "Desconhecido"

                    # profissional = (
                    #     self.wait_for_element(
                    #         By.XPATH, ".//td[contains(@class,'active')]//strong"
                    #     )
                    #     .text.replace("Profissional / Agenda:", "")
                    #     .strip()
                    # )
                    prof_elem = table.find_elements(By.XPATH, ".//td[contains(@class,'active')]//strong")
                    profissional = prof_elem[0].text.replace("Profissional / Agenda:", "").strip() if prof_elem else "Desconhecido"
                    print(f"Found profissional: {profissional}")

                    # linhas = table.find_elements(By.XPATH, ".//tr[td and not(td[@colspan]) and not(th)]")
                    linhas = table.find_elements(
                        By.XPATH, ".//tbody/tr[td and not(th) and not(td[@colspan])]"
                    )

                    for linha in linhas:
                        colunas = linha.find_elements(By.TAG_NAME, "td")

                        if len(colunas) < 9:
                            continue

                        dta_atend = colunas[0].text.strip()

                        if "EXCLUÍDO POR" in dta_atend:  # cancelado
                            continue

                        dta_atend_date = datetime.strptime(dta_atend, "%d/%m/%Y")

                        if (
                            linha.get_attribute("class") == "bg-danger"
                            and dta_atend_date < today
                        ):  # não compareceu
                        # TODO: implementar também por última data no banco de dados 
                            continue

                        appointments.append(
                            {
                                "profissional": profissional,
                                "data_atendimento": dta_atend,
                                "hora": colunas[1].text.strip(),
                                "tipo": colunas[5].text.strip(),
                                "retorno_ate": colunas[7].text.strip(),
                            }
                        )

                # if self.is_last_page():
                #     break
                
                if not self.go_to_next_page():
                    # print("Falha na navegação. Encerrando loop.")
                    break
                

            if len(appointments) == 0:
                print(f"No appointments found for CPF {cpf}.")
                self.save_screenshot("patient_history_no_appointments.png")
                return {"status": "success", "appointments": []}

            print(f"Found {len(appointments)} appointments for CPF {cpf}.")
            return {"status": "success", "appointments": appointments}

        except TimeoutException as e:
            print(f"Timeout while fetching patient history: {e}")
            self.save_screenshot("patient_history_timeout.png")
            return {"status": "error", "message": f"Timeout: {e}"}
        except Exception as e:
            print(f"Error fetching patient history: {e}")
            self.save_screenshot("patient_history_error.png")
            return {"status": "error", "message": str(e)}
        finally:
            print("History fetch cycle ended.")

if __name__ == "__main__":
    scraper = PatientHistoryScraper()
    codigo = scraper.get_patient_by_type("nome", "Pedro Oliveira")
    print(codigo)