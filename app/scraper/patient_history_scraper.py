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
            return len(next_button) > 0
        except NoSuchElementException:
            return False

    def go_to_next_page(self):
        next_button = self.wait_for_element(
            By.XPATH, "//a[@aria-label='Next']"
        )
        try:
            next_button.click()
        except:
            self.execute_script("arguments[0].click();", next_button)
        finally:
            time.sleep(2)

    def is_last_page(self):
        try:
            current_page = self.wait_for_element(
                By.XPATH, "//a[contains(@class,'paginaAtual')]"
            )
            last_page = self.wait_for_element(
                By.XPATH, "//a[starts-with(normalize-space(text()), 'Última')]"
        )

            return current_page.get_attribute("href") == last_page.get_attribute("href")

        except NoSuchElementException:
            # Se não existe "Última", não há paginação
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

            try:
                try:
                    pesquisa_paciente_xpath = "//a[@href='#divPesquisaPaciente' and contains(text(),'Pesquisa Paciente')]" 
                    prontuario_menu = self.wait_for_element(By.XPATH, pesquisa_paciente_xpath)
                    prontuario_menu.click()
                except:
                    self.execute_script("arguments[0].click();", prontuario_menu)

                search_patient = self.wait_for_element(By.ID, "tipoPesquisaPacienteGrade")
                select = Select(search_patient)
                select.select_by_visible_text("Cpf")

                print("Entered patient history screen.")
                time.sleep(2)

            except TimeoutException:
                print("Could not find patient history menu. Using direct search...")


            cpf_field = self.wait_for_element(By.ID, "pesquisaPacienteGrade")

            if cpf_field:
                cpf_field.clear()
                cpf_field.send_keys(cpf)

                print(f"CPF {cpf} entered in search field.")

                search_button = self.wait_for_element(
                    By.ID,
                    "btPesquisaPacienteGrade1",
                )

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

            botao_historico = self.wait_for_element(By.XPATH, "//button[@title='Visualizar Histórico do Paciente.']")

            if botao_historico:
                try:
                    botao_historico.click()
                except:
                    self.execute_script("arguments[0].click();", botao_historico)
                print("Historical button clicked.")
            else:
                print("Could not find historical button.")

            time.sleep(2)

            tables = self.wait_for_element(
                By.XPATH, "//table[contains(@class,'table-bordered')]"
            )

            appointments = []
            

            # for table in tables: 
            #     profissional = table.wait_for_element(
            #         By.XPATH, ".//tr[td[contains(@class,'active')]]//strong"
            #     ).text.replace("Profissional / Agenda:", "").strip()

            #     print(f"Profissional: {profissional}")

            #     linhas = table.find_elements(By.XPATH, ".//tr[td and not(th)]")


            #     for linha in linhas:
            #         colunas = linha.find_elements(By.TAG_NAME, "td")

            #         if len(colunas) < 8:
            #             continue

            #         dta_atend = colunas[0].text.strip()

            #         if "EXCLUÍDO POR" in dta_atend:
            #             continue

            #         hora = colunas[1].text.strip()
            #         tipo = colunas[5].text.strip()
            #         retorno_ate = colunas[7].text.strip()

            #         appointments.append({
            #             "profissional": profissional,
            #             "data_atendimento": dta_atend,
            #             "hora": hora,
            #             "tipo": tipo,
            #             "retorno_ate": retorno_ate
            #         })

            while True:
                tables = self.driver.find_elements(
                    By.XPATH, "//table[contains(@class,'table-bordered')]"
                )

                for table in tables:
                    profissional = table.find_element(
                        By.XPATH, ".//tr[td[contains(@class,'active')]]//strong"
                    ).text.replace("Profissional / Agenda:", "").strip()

                    linhas = table.find_elements(By.XPATH, ".//tr[td and not(th)]")

                    for linha in linhas:
                        colunas = linha.find_elements(By.TAG_NAME, "td")

                        if len(colunas) < 8:
                            continue

                        dta_atend = colunas[0].text.strip()

                        if "EXCLUÍDO POR" in dta_atend:
                            continue

                        appointments.append({
                            "profissional": profissional,
                            "data_atendimento": dta_atend,
                            "hora": colunas[1].text.strip(),
                            "tipo": colunas[5].text.strip(),
                            "retorno_ate": colunas[7].text.strip()
                        })

                if self.is_last_page():
                    break

                if self.has_next_page():
                    self.go_to_next_page()
                else:
                    break

            

            # print(appointments)

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
            if "self" in locals():
                self.quit()
