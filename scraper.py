import time
import os 
import shutil
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.chrome.options import Options


from webdriver_manager.chrome import ChromeDriverManager

from parse_clinic_report import parse_clinic_report

def check_softclyn_disponibility():
    """
    Executa a automação completa no SoftClyn e retorna o próximo horário.
    """

    # WebDriver configuration
    debugger_address = 'localhost:9222'

    base_dir = os.path.abspath(os.path.dirname(__file__))  
    download_dir = os.path.join(base_dir, "download")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080") 
    options.add_experimental_option("debuggerAddress", debugger_address)
    prefs = {"download.default_directory": download_dir,
         "download.prompt_for_download": False,
         "download.directory_upgrade": True,
         "safebrowsing.enabled": True,
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
            modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'bootbox')))  # Ensure modal is present
            print("Modal found, waiting for OK button...")
            ok_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-bb-handler="ok"]'))
            )   

            try:
                ok_button.click()
            except ElementClickInterceptedException:
                # Fallback to JavaScript click
                print("OK button click intercepted, using JavaScript...")
                driver.execute_script("arguments[0].click();", ok_button)
            wait.until(
                EC.invisibility_of_element_located((By.CLASS_NAME, 'bootbox'))
            )
            print("Modal closed successfully.")
        except TimeoutException:
            print("No modal found or already closed, proceeding...")        
        
        reports = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Relatórios")))

        actions = ActionChains(driver)
        actions.move_to_element(reports).click().perform()

        submenu_hover = wait.until(EC.visibility_of_element_located((By.ID, "menuRelatorioAgendaLi")))
        actions.move_to_element(submenu_hover).perform()

        appointments = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@href, 'relAgendamentos.php')]")
        ))

        actions.click(appointments)
        actions.perform()

        select_doctor = "//select[@id='medico']/following-sibling::div/button"
        
        dropdown_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, select_doctor))
        )
        dropdown_button.click()

        select_option_all = "//li[contains(@class, 'multiselect-all')]//label[contains(text(), 'Todos')]"
        all = wait.until(
            EC.element_to_be_clickable((By.XPATH, select_option_all))
        )
        all.click()

        initialDate = wait.until(EC.element_to_be_clickable((By.ID, "dataInicial")))
        initialDate.click()

        time.sleep(5)

        print("Exporting to Excel...")
        export_button = wait.until(EC.element_to_be_clickable((By.ID, "exportaExcel")))
        export_button.click()

        # Wait for download to complete
        time.sleep(7)
        
        downloaded_files = [f for f in os.listdir(download_dir) if f.endswith('.xls')]
        default_download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not downloaded_files:
            # Check default Downloads folder if not found in custom directory
            downloaded_files = [f for f in os.listdir(default_download_dir) if f.endswith('.xls')]
            if downloaded_files:
                latest_file = max([os.path.join(default_download_dir, f) for f in downloaded_files], key=os.path.getctime)
                # Move the file to the desired directory
                destination = os.path.join(download_dir, os.path.basename(latest_file))
                shutil.move(latest_file, destination)
                print(f"Moved file from Downloads to: {destination}")
                latest_file = destination
            else:
                print("No file downloaded in either directory.")
                return None
        else:
            latest_file = max([os.path.join(download_dir, f) for f in downloaded_files], key=os.path.getctime)
            print(f"Downloaded file: {latest_file}")

        parse_clinic_report(latest_file)
    except TimeoutException as e:
        return {"status": "error", "message": f"A timeout occurred: {e}"}
    except Exception as e: # Catch other exceptions
        return {"status": "error", "message": str(e)}
    finally: 
        driver.quit()

if __name__ == '__main__':
    check_softclyn_disponibility() 