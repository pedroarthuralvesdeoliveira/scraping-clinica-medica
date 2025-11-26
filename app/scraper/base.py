from selenium.webdriver.common.by import By
from ..core.dependencies import get_settings
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class Browser:
    def __init__(self, prefs=None):
        options = webdriver.ChromeOptions()

        prefs = {
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox") # Necessário para rodar como root/em containers
        options.add_argument("--disable-dev-shm-usage") # Necessário para alguns ambientes Linux
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")

        self.driver = webdriver.Chrome(options=options)
        self.settings = get_settings()

    def get(self, url):
        self.driver.get(url)

    def find_element(self, by, value):
        return self.driver.find_element(by, value)

    def find_elements(self, by, value):
        return self.driver.find_elements(by, value)
    
    def wait_for_element(self, by, value, timeout=10):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None
        
    def execute_script(self, script, *args):
        return self.driver.execute_script(script, *args)
    
    def refresh(self):
        self.driver.refresh()
    
    def quit(self):
        self.driver.quit()
    
    def _login(self):
        """
        Realiza o login no sistema Softclyn. 
        """
        try:
            self.get(self.settings.softclyn_url)
            self.wait_for_element(By.TAG_NAME, 'body')
            
            self.find_element('ID', 'usuario').send_keys(self.settings.softclyn_user)
            self.find_element('ID', 'senha').send_keys(self.settings.softclyn_pass)
            
            self.wait_for_element(By.ID, 'btLogin')
            
            self.execute_script("arguments[0].click();", self.find_element(By.ID, 'btLogin'))
        except Exception as e:
            print(f"Erro ao realizar login: {e}")
            
    def _close_modal(self):
        try:
            self.wait_for_element(By.CLASS_NAME, 'modal')
            self.execute_script("arguments[0].click();", self.find_element(By.CSS_SELECTOR, 'button[data-dismiss="modal"]'))
        except Exception as e:
            print(f"Erro ao fechar modal: {e}")
