import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select


from app.scraper.base import Browser


class PatientHistoryScraper(Browser):
    def __init__(self):
        super().__init__()

    def has_next_page(self):
        try:
            next_button = self.wait_for_element(By.XPATH, "//a[@aria-label='Next']")
            return next_button is not None
        except NoSuchElementException:
            return False

    def go_to_next_page(self):
        next_button = self.wait_for_element(By.XPATH, "//a[@aria-label='Next']")
        if next_button:
            try:
                next_button.click()
            except:
                self.execute_script("arguments[0].click();", next_button)
        time.sleep(2)

    def is_last_page(self):
        try:
            current_page = self.wait_for_element(
                By.XPATH, "//a[contains(@class,'paginaAtual')]"
            )
            last_page = self.wait_for_element(
                By.XPATH, "//a[starts-with(normalize-space(text()), 'Última')]"
            )

            if current_page and last_page:
                return current_page.get_attribute("href") == last_page.get_attribute(
                    "href"
                )

        except NoSuchElementException:
            pass

        return True

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

            time.sleep(3)

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

            time.sleep(3)

            # self.save_screenshot("patient_history_tables.png")
            tables = self.wait_for_element(
                By.XPATH, "//table[contains(@class,'table-bordered')]"
            )

            if not tables:
                print(
                    "No tables found with xpath //table[contains(@class,'table-bordered')]"
                )
                self.save_screenshot("no_tables_error.png")
                return {"status": "error", "message": "No tables found"}

            print(f"Found tables on page")
            appointments = []

            while True:
                tables = self.driver.find_elements(
                    By.XPATH, "//table[contains(@class,'table-bordered')]"
                )

                for table in tables:
                    profissional = "Desconhecido"
                    for xpath in [
                        ".//tr[td[contains(@class,'active')]]//strong",
                        ".//tr[contains(@class,'active')]//strong",
                        ".//td[@class='active']/ancestor::tr//strong",
                        ".//strong[contains(text(),'Profissional')]",
                    ]:
                        try:
                            profissional = (
                                table.find_element(By.XPATH, xpath)
                                .text.replace("Profissional / Agenda:", "")
                                .strip()
                            )
                            print(f"Found profissional: {profissional}")
                            break
                        except Exception:
                            continue

                    linhas = table.find_elements(By.XPATH, ".//tr[td and not(th)]")

                    for linha in linhas:
                        colunas = linha.find_elements(By.TAG_NAME, "td")

                        if len(colunas) < 8:
                            continue

                        dta_atend = colunas[0].text.strip()

                        if "EXCLUÍDO POR" in dta_atend:
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

                if self.is_last_page():
                    break

                if self.has_next_page():
                    self.go_to_next_page()
                else:
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
            print("Closing browser for patient history scraper.")
            self.quit()
