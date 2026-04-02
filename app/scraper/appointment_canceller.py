import time
from datetime import datetime

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from app.scraper.base import Browser

from ..core.dependencies import get_settings

settings = get_settings()


class AppointmentCanceller(Browser):
    def __init__(self):
        super().__init__()

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        return " ".join((value or "").split()).casefold()

    def _find_cancel_click_target(self, horario_id: str, nome_paciente: str):
        row_xpath = f"//tr[@id='{horario_id}']"
        row = self.wait_for_element(By.XPATH, row_xpath)

        if not row:
            print(f"ERRO: Linha da grade para o horário {horario_id} não encontrada.")
            return None

        row_text = self._normalize_text(row.text)
        patient_name = self._normalize_text(nome_paciente)
        print(f"Conteúdo encontrado na linha {horario_id}: {row.text!r}")

        if patient_name and patient_name not in row_text:
            print(
                f"Paciente '{nome_paciente}' não encontrado no texto da linha {horario_id}."
            )
            return None

        trash_icons = row.find_elements(By.XPATH, ".//*[contains(@class, 'glyphicon-trash')]")
        if not trash_icons:
            print(f"Nenhum ícone de cancelamento encontrado na linha {horario_id}.")
            return None

        for trash_icon in trash_icons:
            onclick = self._normalize_text(trash_icon.get_attribute("onclick"))
            ancestor_onclick = None

            try:
                ancestor_onclick = trash_icon.find_element(By.XPATH, "./ancestor::*[@onclick][1]")
            except Exception:
                ancestor_onclick = None

            ancestor_onclick_attr = self._normalize_text(
                ancestor_onclick.get_attribute("onclick") if ancestor_onclick else ""
            )

            if patient_name and (
                patient_name in onclick or patient_name in ancestor_onclick_attr
            ):
                return ancestor_onclick or trash_icon

        if len(trash_icons) == 1:
            print(
                "Usando o único ícone de cancelamento disponível na linha do horário."
            )
            try:
                return trash_icons[0].find_element(By.XPATH, "./ancestor::*[@onclick][1]")
            except Exception:
                return trash_icons[0]

        print(
            f"Foram encontrados {len(trash_icons)} ícones de cancelamento na linha {horario_id}, sem correspondência inequívoca para '{nome_paciente}'."
        )
        return None
        
    def _check_scheduled_time(self, data_desejada: str):
        dateAppointment = self.wait_for_element(By.ID, "dataAgenda")

        try:
            data_obj = datetime.strptime(data_desejada, "%d/%m/%Y")

            data_formatada_para_input = data_obj.strftime("%Y-%m-%d")

            print(
                f"Convertendo data {data_desejada} para {data_formatada_para_input} (ISO) para envio via JS."
            )

        except ValueError:
            print(f"ERRO: Não foi possível converter a data '{data_desejada}'.")
            return {"status": "error", "message": "Data em formato inválido."}

        try:
            self._set_date(dateAppointment, data_formatada_para_input)
            print("Data injetada e eventos disparados.")

        except Exception as e:
            print(f"Erro ao tentar injetar data com JavaScript: {e}")
            self.save_screenshot("debug_data_javascript_falhou.png")
            return {
                "status": "error",
                "message": "Falha ao definir data com JavaScript.",
            }
            
        if dateAppointment: 
            valor_final_campo = dateAppointment.get_attribute("value")
            print(
                f"Valor final no campo de data (value property): '{valor_final_campo}' (Esperado: '{data_formatada_para_input}')"
            )
    
            if valor_final_campo != data_formatada_para_input:
                print(
                    "ALERTA: O valor final no campo não corresponde ao esperado após injeção de JS!"
                )

        print(f"Data selecionada (original): {data_desejada}")

    def cancel_appointment(
        self, medico, data_desejada, horario_desejado, nome_paciente
    ):
        """
        Cancels an appointment in softclyn.
        """

        try:
            self._login(medico)
            self._close_modal()

            print("Iniciando fluxo de cancelamento...")

            if self.is_softclyn_of:
                self._click_on_appointment_menu()

            self._search_doctor(medico)
            
            self._check_scheduled_time(data_desejada)

            self._is_timetable()

            horario_id = horario_desejado.replace(":", "") + "00"

            try:
                cancel_click_target = self._find_cancel_click_target(
                    horario_id, nome_paciente
                )

                if not cancel_click_target:
                    print(
                        f"Erro: Não foi possível localizar um acionador de cancelamento para o paciente {nome_paciente} no horário {horario_desejado}."
                    )
                    self.save_screenshot("cancel_trigger_not_found.png")
                    return {"status": "error", "message": "Agendamento não encontrado."}

                try:
                    cancel_click_target.click()
                except Exception:
                    self.execute_script("arguments[0].click();", cancel_click_target)
                print(
                    f"Ícone de cancelamento para o paciente {nome_paciente} no horário {horario_desejado} clicado."
                )

                
                desmarcado_button = self.wait_for_element(By.CSS_SELECTOR, "button[data-bb-handler='danger']")
                
                if not desmarcado_button:
                    print("ERRO: Botão 'Desmarcado' do modal não encontrado.")
                    raise TimeoutException("Botão 'Desmarcado' não encontrado.")
    
                try:
                    self.execute_script("arguments[0].click();", desmarcado_button)
                    print("Botão 'Desmarcado' clicado via JavaScript.")
                    time.sleep(2)
                except Exception: 
                    print("Falha ao clicar no botão 'Desmarcado' via JavaScript. Tentando método padrão.")
                    desmarcado_button = self.wait_for_element(By.CSS_SELECTOR, "button[data-bb-handler='danger']")
                    if desmarcado_button:
                        try: 
                            desmarcado_button.click()
                        except Exception:
                            print("Falha ao clicar no botão 'Desmarcado' via método padrão.")
                            self.execute_script("arguments[0].click();", desmarcado_button)
                        print("Botão 'Desmarcado' clicado via método padrão.")
                    else:
                        print("ERRO: Botão 'Desmarcado' não encontrado após falha do JS.")
                        raise TimeoutException("Botão 'Desmarcado' não encontrado após tentativa de clique JS.")
                                        
                time.sleep(2)
    
                reason_input = self.wait_for_element(By.CSS_SELECTOR, "input.bootbox-input-text")
                if not reason_input:
                    print("ERRO: Campo de motivo não encontrado.")
                    raise TimeoutException("Campo de motivo não encontrado.")
    
                reason_input.send_keys("não disse o motivo")
                print("Motivo do cancelamento preenchido.")
                
                confirm_button = self.wait_for_element(By.CSS_SELECTOR, "button[data-bb-handler='confirm']")
                if not confirm_button:
                    print("ERRO: Botão de confirmação de motivo não encontrado.")
                    raise TimeoutException("Botão de confirmação de motivo não encontrado.")
    
                self.execute_script("arguments[0].click();", confirm_button)
                print("Botão de confirmação do motivo clicado.")
                time.sleep(2)
    
                print("Cancelamento concluído com sucesso!")
                return {"status": "success", "message": "Agendamento cancelado."}

            except TimeoutException:
                print(
                    f"Erro: Não foi possível encontrar o agendamento para o paciente {nome_paciente} no horário {horario_desejado}."
                )
                return {"status": "error", "message": "Agendamento não encontrado."}

        except TimeoutException as e:
            print(f"Erro: Timeout! O elemento não foi encontrado a tempo. {e}")
            self.save_screenshot("error_screenshot_cancel.png")
            return {"status": "error", "message": f"A timeout occurred: {e}"}
        except Exception as e:
            print(f"Erro inesperado: {e}")
            self.save_screenshot("error_screenshot_cancel.png")
            return {"status": "error", "message": str(e)}
        finally:
            print("Fechando o navegador.")
            if "self" in locals():
                self.quit()
            else:
                print("self não encontrado.")
