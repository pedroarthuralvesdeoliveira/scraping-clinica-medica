from .base import Browser

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os
from datetime import datetime, timedelta


class NextAppointmentsScraper(Browser):
    def __init__(self):
        super().__init__()

    def click_on_reports_menu(self):
        menu_relatorios = self.wait_for_element(
            By.ID, "menuRelatoriosLi", expectation=EC.element_to_be_clickable
        )

        submenu_agendamento = self.find_element(By.ID, "menuRelatorioAgendaLi")

        item_final = self.find_element(
            By.CSS_SELECTOR, "#menuRelatorioAgenda #Agendamento a"
        )

        actions = ActionChains(self.driver)
        actions.move_to_element(menu_relatorios)  # Move para Relatórios
        actions.move_to_element(submenu_agendamento)  # Move para Agendamento
        try:
            actions.click(item_final)
            actions.perform()
        except:
            self.execute_script(
                "abrePagina('centro','../view/relatorios/agendamentos/relAgendamentos.php');"
            )

        time.sleep(2)

        print("Entrou na tela de relatórios de agendamentos.")

    def set_date_range(self):
        dataInicial = self.wait_for_element(By.ID, "dataInicial")

        try:
            data_obj = datetime.strptime(
                datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y"
            )

            data_formatada_para_input = data_obj.strftime("%Y-%m-%d")

            print(
                f"Convertendo data {datetime.now().strftime('%d/%m/%Y')} para {data_formatada_para_input} (ISO) para envio via JS."
            )

        except ValueError:
            print(f"ERRO: Não foi possível converter a data '{data_obj}'.")
            return {"status": "error", "message": "Data em formato inválido."}

        try:
            self.execute_script(
                "arguments[0].value = arguments[1];",
                dataInicial,
                data_formatada_para_input,
            )
            print("Valor da data injetado via JavaScript.")

            print("Disparando 'onblur' via JavaScript para carregar a grade...")
            self.execute_script(
                "arguments[0].dispatchEvent(new Event('blur'));", dataInicial
            )

        except Exception as e:
            print(f"Erro ao tentar injetar data com JavaScript: {e}")
            return {
                "status": "error",
                "message": "Falha ao definir data com JavaScript.",
            }

        if dataInicial:
            valor_final_campo = dataInicial.get_attribute("value")
            print(
                f"Valor final no campo de data (value property): '{valor_final_campo}' (Esperado: '{data_formatada_para_input}')"
            )

            if valor_final_campo != data_formatada_para_input:
                print(
                    "ALERTA: O valor final no campo não corresponde ao esperado após injeção de JS!"
                )

        dataFinal = self.wait_for_element(By.ID, "dataFinal")
        next_month = datetime.now() + timedelta(days=30)

        try:
            data_obj = None
            data_obj = datetime.strptime(next_month.strftime("%d/%m/%Y"), "%d/%m/%Y")

            data_formatada_para_input = None
            data_formatada_para_input = data_obj.strftime("%Y-%m-%d")

            print(
                f"Convertendo data {next_month.strftime('%d/%m/%Y')} para {data_formatada_para_input} (ISO) para envio via JS."
            )

        except ValueError:
            print(f"ERRO: Não foi possível converter a data '{data_obj}'.")
            return {"status": "error", "message": "Data em formato inválido."}

        try:
            self.execute_script(
                "arguments[0].value = arguments[1];",
                dataFinal,
                data_formatada_para_input,
            )
            print("Valor da data injetado via JavaScript.")

            print("Disparando 'onblur' via JavaScript para carregar a grade...")
            self.execute_script(
                "arguments[0].dispatchEvent(new Event('blur'));", dataFinal
            )

        except Exception as e:
            print(f"Erro ao tentar injetar data com JavaScript: {e}")
            return {
                "status": "error",
                "message": "Falha ao definir data com JavaScript.",
            }

        if dataFinal:
            valor_final_campo = dataFinal.get_attribute("value")
            print(
                f"Valor final no campo de data (value property): '{valor_final_campo}' (Esperado: '{data_formatada_para_input}')"
            )

            if valor_final_campo != data_formatada_para_input:
                print(
                    "ALERTA: O valor final no campo não corresponde ao esperado após injeção de JS!"
                )


        time.sleep(2)

    def select_all_doctors(self):
        try:
            botao = self.wait_for_element(
                By.CSS_SELECTOR,
                "button.multiselect.dropdown-toggle",
                expectation=EC.element_to_be_clickable,
            )
            try:
                botao.click()
            except:
                self.execute_script("arguments[0].click();", botao)

            checkbox_todos = self.wait_for_element(
                By.CSS_SELECTOR,
                "li.multiselect-all input[type='checkbox']",
                expectation=EC.element_to_be_clickable,
            )
            try:
                checkbox_todos.click()
            except:
                self.execute_script("arguments[0].click();", checkbox_todos)

            menu_opcoes = self.wait_for_element(
                By.ID, "menuConfiguracoesLi", expectation=EC.element_to_be_clickable
            )
            try:
                menu_opcoes.click()
            except:
                self.execute_script("arguments[0].click();", menu_opcoes)

        except Exception as e:
            print(f"Erro ao selecionar todos os médicos: {e}")
            return {
                "status": "error",
                "message": "Falha ao selecionar todos os médicos.",
            }


        time.sleep(2)

    def export_excel(self):
        try:
            botao_exportar = self.wait_for_element(
                By.ID, "exportaExcel", expectation=EC.element_to_be_clickable
            )
            try:
                botao_exportar.click()
            except:
                self.execute_script("arguments[0].click();", botao_exportar)

        except Exception as e:
            print(f"Erro ao exportar relatório: {e}")
            return {
                "status": "error",
                "message": "Falha ao exportar relatório.",
            }

        time.sleep(5)

    def get_excel_data(self):
        try:
            folder_path = (
                "/home/pedro/freelas/backend/scraping-clinica-medica/app/scraper/data"
            )
            file_name = "26relatorio.xls"
            full_path = os.path.join(folder_path, file_name)
            df = pd.read_excel(full_path, engine="calamine", skiprows=1)

            df.columns = [str(c).strip() for c in df.columns]
            df_limpo = df[
                df["DATA/HORA"].astype(str).str.contains(r"\d{2}/\d{2}/\d{4}", na=False)
            ].copy()
            df_limpo = df_limpo.dropna(axis=1, how="all")

            df_limpo = df_limpo[
                ["DATA/HORA", "PACIENTE", "TIPO", "STATUS", "RESPONSÁVEL", "TELEFONE"]
            ]
            df_limpo[["DATA", "HORA"]] = df_limpo["DATA/HORA"].str.split(
                " - ", expand=True
            )
            df_limpo["DATA"] = df_limpo["DATA"].str.strip()
            df_limpo["HORA"] = df_limpo["HORA"].str.strip()
            df_limpo = df_limpo.drop(columns=["DATA/HORA"])


            df_limpo[["CODIGO", "NOME_PACIENTE"]] = df_limpo["PACIENTE"].str.split(
                " - ", expand=True
            )
            df_limpo["CODIGO"] = df_limpo["CODIGO"].str.strip()
            df_limpo["NOME_PACIENTE"] = df_limpo["NOME_PACIENTE"].str.strip()
            df_limpo = df_limpo.drop(columns=["PACIENTE"])


            appointments = []
            for _, row in df_limpo.iterrows():
                try:
                    data_str = row["DATA"]
                    if pd.isna(data_str) or not isinstance(data_str, str):
                        continue

                    data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()

                    hora_str = row["HORA"]
                    hora_obj = None
                    if not pd.isna(hora_str) and isinstance(hora_str, str):
                        try:
                            hora_obj = datetime.strptime(hora_str, "%H:%M:%S").time()
                        except ValueError:
                            pass

                    appointment = {
                        "data_consulta": data_obj,
                        "hora_consulta": hora_obj,
                        "codigo": str(row["CODIGO"]).strip()
                        if not pd.isna(row["CODIGO"])
                        else "",
                        "telefone": str(row["TELEFONE"]).strip()
                        if not pd.isna(row["TELEFONE"])
                        else "",
                        "nome_paciente": str(row["NOME_PACIENTE"]).strip()
                        if not pd.isna(row["NOME_PACIENTE"])
                        else "",
                        "profissional": str(row["RESPONSÁVEL"]).strip()
                        if not pd.isna(row["RESPONSÁVEL"])
                        else "",
                        "procedimento": str(row["TIPO"]).strip()
                        if not pd.isna(row["TIPO"])
                        else "",
                        "status": str(row["STATUS"]).strip()
                        if not pd.isna(row["STATUS"])
                        else "",
                        "primeira_consulta": "primeira" in str(row["TIPO"]).lower()
                        if not pd.isna(row["TIPO"])
                        else False,
                        "especialidade": "",
                        "observacoes": "",
                    }
                    appointments.append(appointment)

                except Exception as e:
                    print(f"Erro ao processar linha {_}: {e}")
                    continue

            return {
                "status": "success",
                "appointments": appointments,
                "total_count": len(appointments),
            }

        except Exception as e:
            print(f"Erro ao obter dados do Excel: {e}")
            return {
                "status": "error",
                "message": "Falha ao obter dados do Excel.",
            }

    def remove_excel_file(self):
        try:
            folder_path = (
                "/home/pedro/freelas/backend/scraping-clinica-medica/app/scraper/data"
            )
            file_name = "26relatorio.xls"
            full_path = os.path.join(folder_path, file_name)
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"Arquivo {file_name} removido com sucesso.")
            else:
                print(f"Arquivo {file_name} não encontrado.")
        except Exception as e:
            print(f"Erro ao remover arquivo: {e}")

    def get_next_appointments(self):
        """
        Scrapes the next appointments from the website.
        """
        try:
            self._login()
            self._close_modal()
            self.click_on_reports_menu()
            self.set_date_range()
            self.select_all_doctors()
            self.export_excel()
            result = self.get_excel_data()

            if result.get("status") != "success":
                return result

            self.remove_excel_file()

            return {
                "status": "success",
                "message": "Next appointments scraped successfully.",
                "appointments": result.get("appointments", []),
                "total_count": result.get("total_count", 0),
            }


        except Exception as e:
            print(f"Error in get_next_appointments: {e}")
            self.remove_excel_file()
            return {
                "status": "error",
                "message": f"Error in get_next_appointments: {e}",
            }


if __name__ == "__main__":
    scraper = NextAppointmentsScraper()
    scraper.get_next_appointments()
