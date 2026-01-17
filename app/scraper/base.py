import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from ..core.dependencies import get_settings
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException


class Browser:
    def __init__(self, prefs=None):
        options = webdriver.ChromeOptions()

        prefs = {"safebrowsing.enabled": True}
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--headless=new")
        options.add_argument(
            "--no-sandbox"
        )  # Necessário para rodar como root/em containers
        options.add_argument(
            "--disable-dev-shm-usage"
        )  # Necessário para alguns ambientes Linux
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")

        self.driver = webdriver.Chrome(options=options)
        self.settings = get_settings()
        self.is_softclyn_of = False

    def get(self, url):
        self.driver.get(url)

    def find_element(self, by, value):
        return self.driver.find_element(by, value)

    def find_elements(self, by, value):
        return self.driver.find_elements(by, value)

    def wait_for_staleness_element(self, element, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(EC.staleness_of(element))
            return True
        except TimeoutException:
            return False

    def wait_for_element(
        self, by, value, expectation=EC.presence_of_element_located, timeout=10
    ):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                expectation((by, value))
            )
            return element
        except TimeoutException:
            return None

    def execute_script(self, script, *args):
        return self.driver.execute_script(script, *args)

    def refresh(self):
        self.driver.refresh()

    def save_screenshot(self, filename):
        self.driver.save_screenshot(filename)

    def quit(self):
        if self.driver:
            self.driver.quit()

    def _click_on_appointment_menu(self):
        menu = self.wait_for_element(By.ID, "menuAtendimentoLi")
        try:
            menu.click()
        except:
            self.execute_script("arguments[0].click();", menu)

        print("Clicando em 'Agendamento' no menu...")

        agendamento = self.wait_for_element(By.ID, "M1")
        try:
            agendamento.click()
        except:
            self.execute_script("arguments[0].click();", agendamento)

        print("Entrou na tela de agendamento.")

        time.sleep(2)

    def _search_doctor(self, medico: str):
        try:
            select_doctor_clickable = self.wait_for_element(
                By.ID, "select2-medico-container"
            )
            if select_doctor_clickable:
                select_doctor_clickable.click()

            search_field = self.wait_for_element(
                By.XPATH, "//input[@class='select2-search__field']"
            )
            print("Campo de busca do Select2 encontrado.")

            medico_limpo = medico.replace("Dr.", "").replace("Dra.", "").strip()

            print(f"Digitando '{medico_limpo}'...")
            if search_field:
                search_field.send_keys(medico_limpo)

            time.sleep(2)

            print(f"Nome '{medico_limpo}' digitado no campo de busca.")

            try:
                if search_field:
                    search_field.send_keys(Keys.ENTER)
                print("Enviado ENTER para selecionar.")
            except Exception:
                pass

            try:
                medico_option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(text(), '{medico_limpo}')]"

                medico_option = self.wait_for_element(By.XPATH, medico_option_xpath)
                if medico_option:
                    medico_option.click()
                print(f"Clicado na opção: {medico_limpo}")
            except TimeoutException:
                print("Opção não encontrada ou já selecionada pelo ENTER.")
            except StaleElementReferenceException:
                medico_option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(text(), '{medico_limpo}')]"
                medico_option = self.find_element(By.XPATH, medico_option_xpath)
                medico_option.click()

        except TimeoutException:
            print("ERRO: O medico não foi encontrado a tempo.")
        except Exception as e:
            print(f"Ocorreu outro erro: {e}")
            raise

    def _login(self, medico: str | None = None):
        """
        Realiza o login no sistema Softclyn.
        """
        try:
            URL = self.settings.softclyn_url
            LOGIN = self.settings.softclyn_login_page

            medicos_softclyn_of = ["ANDRÉ A. S. BAGANHA", "JOAO R.C.MATOS"]

            URL_BASE = f"{URL}/{self.settings.softclyn_empresa}_ouro/{LOGIN}"

            if medico:
                medico_limpo = medico.replace("Dr.", "").replace("Dra.", "").strip()

                for dr in medicos_softclyn_of:
                    if medico_limpo.upper() in dr.upper():
                        URL_BASE = f"{URL}/{self.settings.softclyn_empresa}_of/{LOGIN}"
                        self.is_softclyn_of = True
                        break

            self.get(URL_BASE)

            self.wait_for_element(By.TAG_NAME, "body")

            user = self.find_element(By.ID, "usuario")
            user.send_keys(self.settings.softclyn_user)
            password = self.find_element(By.ID, "senha")
            password.send_keys(self.settings.softclyn_pass)

            self.wait_for_element(By.ID, "btLogin")

            self.execute_script(
                "arguments[0].click();", self.find_element(By.ID, "btLogin")
            )
        except Exception as e:
            print(f"Erro ao realizar login: {e}")
            self.quit()
            raise

    def _close_modal(self):
        try:
            self.wait_for_element(By.CLASS_NAME, "modal")
            close_button = self.wait_for_element(
                By.CSS_SELECTOR, 'button[data-dismiss="modal"]'
            )
            if close_button:
                self.execute_script("arguments[0].click();", close_button)
                print("Modal fechado com sucesso.")
            else:
                print(
                    "Botão para fechar modal não encontrado, ou modal não está presente."
                )
        except TimeoutException:
            print("Modal não apareceu dentro do tempo")
        except Exception as e:
            print(f"Erro ao fechar modal: {e}")

    def _is_timetable(self):
        try:
            self.wait_for_element(By.XPATH, "//tr[@id='070000']")
            self.wait_for_element(
                By.XPATH,
                "//div[contains(@class, 'alert-info') and contains(text(), 'expediente')]",
            )
            print("Grade de horários ou mensagem de expediente (re)carregada após JS.")
        except TimeoutException:
            print(
                "ERRO: A grade não recarregou após a injeção de JS. Verifique o screenshot."
            )
            self.save_screenshot("debug_data_nao_recarregou_js.png")
