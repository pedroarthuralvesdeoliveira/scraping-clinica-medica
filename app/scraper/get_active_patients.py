from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.support.select import Select
from .base import Browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import glob
from datetime import datetime
import pandas as pd


class GetActivePatients(Browser):
    def __init__(self):
        super().__init__()

    def capture_data(self, data_type: str, header_value: str):
        """
        Captures data from the first row of a table based on column header.
        
        Args:
            data_type (str): The type of data being captured (e.g., 'telefone', 'cpf', 'celular')
            header_value (str): The header text to search for (e.g., 'Telefone', 'CPF', 'Celular')
        
        Returns:
            str or None: The captured data from the table or None if not found
        """
        try:
            # Wait for table to update
            time.sleep(1.5)
            tabela = self.wait_for_element(By.CSS_SELECTOR, "table.tableFiltro", timeout=5)
            if not tabela:
                print(f"  Tabela de resultados não encontrada.")
                return None

            # Find the column index based on header text
            cabecalhos = tabela.find_elements(By.XPATH, ".//thead/tr/th")
            indice_coluna = None
            for i, th in enumerate(cabecalhos, start=1):
                if header_value.upper() in th.text.strip().upper():
                    indice_coluna = i
                    break

            if indice_coluna is None:
                print(f"  Coluna '{header_value}' não encontrada.")
                return None

            try:
                # Get the first row
                linha = tabela.find_element(By.XPATH, ".//tbody/tr[1]")
                data_td = linha.find_element(By.XPATH, f"./td[{indice_coluna}]")
                valor_capturado = data_td.text.strip()
                print(f"  {data_type.capitalize()} encontrado na tabela: {valor_capturado}")
                return valor_capturado
            except Exception as e:
                print(f"  Erro ao extrair dados da célula: {e}")
                return None
        except Exception as e:
            print(f"  Erro ao capturar {data_type}: {e}")
            return None

    def capture_phone(self, cell_phone: bool = False):
        """Captura o telefone da primeira linha da tabela de resultados."""
        if cell_phone:
            return self.capture_data("celular", "Celular")
        return self.capture_data("telefone", "Telefone")

    def capture_cpf(self):
        """Captura o CPF da primeira linha da tabela de resultados."""
        return self.capture_data("cpf", "CPF")

    def prepare_patient_registration_search(self):
        """
        Navigates to the patient registration screen and opens the search modal.
        """
        try:
            print("Navegando para Cadastros -> Paciente...")
            menu_cadastros = self.wait_for_element(
                By.XPATH, 
                "//a[.//span[contains(text(), 'Cadastros')]]",
                timeout=5
            )
            if not menu_cadastros:
                menu_cadastros = self.wait_for_element(By.ID, "menuCadastrosLi", timeout=5)
            
            try:
                menu_cadastros.click()
            except:
                self.execute_script("arguments[0].click();", menu_cadastros)

            submenu_pacientes = self.wait_for_element(By.ID, "M7", timeout=5)
            if not submenu_pacientes:
                submenu_pacientes = self.wait_for_element(By.XPATH, "//a[contains(text(), 'Paciente')]", timeout=5)
            
            try:
                submenu_pacientes.click()
            except:
                self.execute_script("arguments[0].click();", submenu_pacientes)

            time.sleep(2)

            # self.save_screenshot("patient_registration_screen.png")

            print("Abrindo modal de pesquisa...")
            # Try to find the search button by icon or ID
            input_pesquisa = self.wait_for_element(By.ID, "pesquisa", timeout=10)
            if input_pesquisa:
                try:
                    input_pesquisa.click()
                    time.sleep(0.5)
                    input_pesquisa.send_keys(Keys.ENTER)
                except:
                    self.execute_script("arguments[0].click();", input_pesquisa)
                    self.execute_script(
                        "arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));", 
                        input_pesquisa
                    )

            time.sleep(2)
            
            
            # Verify if modal opened
            if self.wait_for_element(By.ID, "pesquisa2", timeout=10):
                print("Modal de pesquisa aberto com sucesso.")
                self.save_screenshot("patient_search_screen.png")
                return True
            
            print("Falha ao abrir o modal de pesquisa (pesquisa2 não encontrado).")
            self.save_screenshot("erro_abrir_modal.png")
            return False
        except Exception as e:
            print(f"Erro ao preparar busca: {e}")
            return False

    def get_phone_by_code(self, patient_code: str):
        """
        Searches for a patient by code and returns their CPF.
        """
        try:
            input_pesquisa2 = self.wait_for_element(
                By.ID, 
                "pesquisa2"
            )
            if not input_pesquisa2:
                print("  Modal parece estar fechado. Tentando reabrir...")
                if not self.prepare_patient_registration_search():
                    return None
                input_pesquisa2 = self.wait_for_element(By.ID, "pesquisa2", timeout=5)

            if not input_pesquisa2:
                print("  Não foi possível encontrar o campo 'pesquisa2'.")
                return None

            try:
                input_pesquisa2.clear()
            except:
                self.execute_script("arguments[0].value = '';", input_pesquisa2)

            time.sleep(1)

            try:
                input_pesquisa2.send_keys(patient_code)
            except:
                self.execute_script("arguments[0].value = arguments[1];", input_pesquisa2, patient_code)
            
            time.sleep(1)

            try:
                input_pesquisa2.send_keys(Keys.ENTER)
            except:
                self.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));", input_pesquisa2)
            
            time.sleep(1)
            
            # Tenta capturar telefone, se vazio tenta celular
            phone_raw = self.capture_phone()
            if not phone_raw:  # Captura strings vazias e None
                phone_raw = self.capture_phone(cell_phone=True)
            
            print(f"  Telefone bruto capturado: {phone_raw}")
            if phone_raw:
                phone_clean = "".join(filter(str.isdigit, phone_raw))
                print(f"  Telefone limpo: {phone_clean}")
                return phone_clean if len(phone_clean) >= 10 else None
                
            return None

        except Exception as e:
            print(f"Erro na busca por código {patient_code}: {e}")
            self.save_screenshot(f"erro_busca_{patient_code}.png")
            return None
    
    
    def get_cpf_by_code(self, patient_code: str):
        """
        Searches for a patient by code and returns their CPF.
        """
        try:
            input_pesquisa2 = self.wait_for_element(
                By.ID, 
                "pesquisa2"
            )
            if not input_pesquisa2:
                print("  Modal parece estar fechado. Tentando reabrir...")
                if not self.prepare_patient_registration_search():
                    return None
                input_pesquisa2 = self.wait_for_element(By.ID, "pesquisa2", timeout=5)

            if not input_pesquisa2:
                print("  Não foi possível encontrar o campo 'pesquisa2'.")
                return None

            # Use JS to clear and type to be more reliable
            try:
                input_pesquisa2.clear()
            except:
                self.execute_script("arguments[0].value = '';", input_pesquisa2)
            
            try:
                input_pesquisa2.send_keys(patient_code)
            except:
                self.execute_script("arguments[0].value = arguments[1];", input_pesquisa2, patient_code)
            
            time.sleep(1)

            try:
                input_pesquisa2.send_keys(Keys.ENTER)
            except:
                self.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));", input_pesquisa2)
            
            cpf_raw = self.capture_cpf()
            if cpf_raw:
                cpf_clean = "".join(filter(str.isdigit, cpf_raw))
                # Softclyn sometimes shows "0" or masks if empty
                return cpf_clean if len(cpf_clean) >= 11 else None
            return None

        except Exception as e:
            print(f"Erro na busca por código {patient_code}: {e}")
            self.save_screenshot(f"erro_busca_{patient_code}.png")
            return None

    def click_on_patients_menu(self):
        menu_relatorios = self.wait_for_element(
            By.ID, "menuRelatoriosLi", expectation=EC.element_to_be_clickable
        )

        submenu_agendamento = self.find_element(By.ID, "menuRelatorioPacientesLi")

        item_final = self.find_element(
            By.CSS_SELECTOR, "#menuRelatorioPacientes #Pacientes a[href*='relPacientesInativos.php']"
        )

        actions = ActionChains(self.driver)
        actions.move_to_element(menu_relatorios)  # Move para Relatórios
        actions.move_to_element(submenu_agendamento)  # Move para Paciente
        try:
            actions.click(item_final)
            actions.perform()
        except:
            self.execute_script(
                "abrePagina('centro','../view/relatorios/pacientes/relPacientesInativos.php');"
            )

        time.sleep(2)

    def click_on_active_patients(self):
        search_patient = self.wait_for_element(
                By.ID,
                "tipoRelatorio",
                expectation=EC.element_to_be_clickable,
            )

        if search_patient:
            select = Select(search_patient)
            try:
                select.select_by_visible_text("Pacientes Ativos")
            except:
                select.select_by_value("ativo")
            time.sleep(2)

        time.sleep(2)

        print("Selecionou os pacientes ativos.")

    def export_excel(self):
        try:
            botao = self.wait_for_element(
                By.XPATH,
                "//button[contains(@onclick, \"exportarExcel\")]",
                expectation=EC.element_to_be_clickable
            )
            try:
                botao.click()
            except:
                self.execute_script("arguments[0].click();", botao)

            # Aguarda o arquivo aparecer (até 30s)
            folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            for i in range(30):
                if glob.glob(os.path.join(folder_path, "*.xls")):
                    print(f"Arquivo baixado após {i+1}s.")
                    break
                time.sleep(1)
            else:
                print("AVISO: Nenhum .xls apareceu em 30s, continuando mesmo assim...")

            print("Exportou os dados do Excel.")

        except Exception as e:
            print(f"Erro ao exportar dados do Excel: {e}")
            return {
                "status": "error",
                "message": "Falha ao exportar dados do Excel.",
            }

    def get_excel_data(self):
        try:
            folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            xls_files = glob.glob(os.path.join(folder_path, "*.xls"))
            if not xls_files:
                return {
                    "status": "error",
                    "message": "No .xls file found in the folder.",
                }
            # Use the first .xls file found
            full_path = xls_files[0]
            print(f"Using Excel file: {os.path.basename(full_path)}")
            df = pd.read_excel(full_path, engine="calamine")

            df.columns = [str(c).strip() for c in df.columns]
            df_limpo = df.dropna(axis=1, how="all")
            df_limpo = df_limpo[
                ["CÓDIGO", "PACIENTE", "TELEFONE"]
            ]
            df_limpo["TELEFONE"] = df_limpo["TELEFONE"].str.split("/", expand=True)[0] # Traz somente o primeiro telefone 
            # TODO: modelagem de banco para considerar mais que um número de telefone

            patients = []
            for _, row in df_limpo.iterrows():
                try:
                    patient = {
                        "codigo": str(row["CÓDIGO"]).strip()
                        if not pd.isna(row["CÓDIGO"])
                        else "",
                        "cad_telefone": str(row["TELEFONE"]).strip()
                        if not pd.isna(row["TELEFONE"])
                        else "",
                        "nomewpp": str(row["PACIENTE"]).strip()
                        if not pd.isna(row["PACIENTE"])
                        else "",
                        "data_nascimento": "",
                        "atendimento_ia": "",
                        "setor": "",
                        "cpf": ""
                    }
                    patients.append(patient)

                except Exception as e:
                    print(f"Erro ao processar linha {_}: {e}")
                    continue

            return {
                "status": "success",
                "patients": patients,
                "total_count": len(patients),
                "file_path": full_path,
            }

        except Exception as e:
            print(f"Erro ao obter dados do Excel: {e}")
            return {
                "status": "error",
                "message": "Falha ao obter dados do Excel.",
            }

    def remove_excel_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Arquivo {os.path.basename(file_path)} removido com sucesso.")
            else:
                print(f"Arquivo {os.path.basename(file_path)} não encontrado.")
        except Exception as e:
            print(f"Erro ao remover arquivo: {e}")

    def get_all_active_patients(self):
        """
        Scrapes all the active patients from the website. 
        """
        try:
            self._login()
            print("Login realizado com sucesso.")
            self._close_modal()
            print("Modal fechado com sucesso.")
            # self.prepare_patient_registration_search()
            # print("Busca de registro de pacientes preparada com sucesso.")
            self.click_on_patients_menu()
            print("Menu de pacientes clicado com sucesso.")
            self.click_on_active_patients()
            print("Pacientes ativos selecionados com sucesso.")
            self.export_excel()
            print("Excel exportado com sucesso.")
            result = self.get_excel_data()
            print("Dados do Excel obtidos com sucesso.")

            if result.get("status") != "success":
                return result

            self.remove_excel_file(result.get("file_path"))

            return {
                "status": "success",
                "message": "All active patients scraped successfully.",
                "patients": result.get("patients", []),
                "total_count": result.get("total_count", 0),
            }
        except Exception as e:
            print(f"Erro ao obter dados: {e}")
            print(f"Erro ao obter dados do Excel: {e}")
            return {
                "status": "error",
                "message": "Falha ao obter dados do Excel.",
            }

    
if __name__ == "__main__":
    scraper = GetActivePatients()
    result = scraper.get_all_active_patients()
    print(result)