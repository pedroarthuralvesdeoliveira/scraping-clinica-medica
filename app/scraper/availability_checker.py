from .base import Browser
from ..core.dependencies import get_settings
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

settings = get_settings()


class AvailabilityChecker(Browser):
    """
    Classe responsável por verificar a disponibilidade de consultas no sistema softclyn.
    Herda de Browser para reutilizar a inicialização do self e o login.
    """

    def __init__(self):
        super().__init__()

    def _verify_availability(
        self,
        data_desejada: str | None = None,
        horario_desejado: str | None = None,
        horario_inicial: str | None = None,
        horario_final: str | None = None,
    ):
        if data_desejada and horario_desejado:
            try:
                data_obj = datetime.strptime(data_desejada, "%d/%m/%Y").date()
                data_formatada_iso = data_obj.strftime("%Y-%m-%d")
                print(
                    f"Convertendo data {data_desejada} para {data_formatada_iso} (ISO) para envio via JS."
                )
            except ValueError:
                print(
                    f"ERRO: Data desejada '{data_desejada}' não está no formato dd/mm/yyyy."
                )
                return {"status": "error", "message": "Data em formato inválido."}

            try:
                dateAppointment = self.wait_for_element(By.ID, "dataAgenda")
                self.execute_script(
                    "arguments[0].value = arguments[1];",
                    dateAppointment,
                    data_formatada_iso,
                )
                self.execute_script(
                    "arguments[0].dispatchEvent(new Event('blur'));", dateAppointment
                )
                print(f"Data {data_formatada_iso} injetada e 'onblur' disparado.")
            except Exception as e:
                print(f"Erro ao tentar injetar data com JavaScript: {e}")
                self.save_screenshot("debug_data_javascript_falhou_1.png")
                return {
                    "status": "error",
                    "message": "Falha ao definir data com JavaScript.",
                }

            try:
                aba_agenda = self.wait_for_element(By.ID, "abaAgenda")
                self.execute_script("arguments[0].click();", aba_agenda)
            except Exception as e:
                print(f"Erro ao tentar clicar em abaAgenda via JS: {e}")
                return {
                    "status": "error",
                    "message": "Falha ao clicar na aba de agenda.",
                }

            self._is_timetable()

            print(f"Data selecionada: {data_desejada}")

            try:
                no_expediente_element = self.wait_for_element(
                    By.XPATH,
                    "//div[contains(@class, 'alert-info') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'não há expediente')]",
                    timeout=5,
                )
                if no_expediente_element:
                    print(f"A data {data_desejada} é um fim de semana ou feriado.")
                    return {
                        "status": "unavailable",
                        "message": f"A data {data_desejada} não tem expediente.",
                    }
            except TimeoutException:
                pass

            horario_id = horario_desejado.replace(":", "") + "00"

            try:
                horario_tr_xpath = f"//tr[@id='{horario_id}']"
                self.wait_for_element(By.XPATH, horario_tr_xpath)
                print(
                    f"Linha de horário {horario_desejado} (ID: {horario_id}) encontrada na grade."
                )
            except NoSuchElementException:
                print(
                    f"ERRO: A linha de horário {horario_desejado} (ID: {horario_id}) não existe na grade para este dia."
                )
                return {
                    "status": "unavailable",
                    "message": f"Horário {horario_desejado} não existe na grade para {data_desejada}.",
                }

            horario_link_xpath = f"//tr[@id='{horario_id}']//a[starts-with(@href, 'javascript:marcaHorarioAgenda') and normalize-space()='{horario_desejado}']"
            horario_link = self.wait_for_element(By.XPATH, horario_link_xpath)

            if horario_link:
                print(
                    f"O horário {horario_desejado}, formatado como {horario_id}, do dia {data_desejada} está DISPONÍVEL para o profissional selecionado."
                )
                return {
                    "status": "success",
                    "message": f"Horário {horario_desejado} em {data_desejada} disponível.",
                }
            else:
                print(
                    f"O horário {horario_desejado}, formatado como {horario_id}, do dia {data_desejada} NÃO está disponível ou não existe como opção de agendamento."
                )
                return {
                    "status": "unavailable",
                    "message": f"Horário {horario_desejado} em {data_desejada} indisponível.",
                }

        elif data_desejada:
            try:
                data_obj = datetime.strptime(data_desejada, "%d/%m/%Y").date()
                data_formatada_iso = data_obj.strftime("%Y-%m-%d")
                print(
                    f"Convertendo data {data_desejada} para {data_formatada_iso} (ISO) para envio via JS."
                )
            except ValueError:
                print(
                    f"ERRO: Data desejada '{data_desejada}' não está no formato dd/mm/yyyy."
                )
                return {"status": "error", "message": "Data em formato inválido."}

            try:
                dateAppointment = self.wait_for_element(By.ID, "dataAgenda")
                self.execute_script(
                    "arguments[0].value = arguments[1];",
                    dateAppointment,
                    data_formatada_iso,
                )
                self.execute_script(
                    "arguments[0].dispatchEvent(new Event('blur'));", dateAppointment
                )
                print(f"Data {data_formatada_iso} injetada e 'onblur' disparado.")
            except Exception as e:
                print(f"Erro ao tentar injetar data com JavaScript: {e}")
                self.save_screenshot("debug_data_javascript_falhou_2.png")
                return {
                    "status": "error",
                    "message": "Falha ao definir data com JavaScript.",
                }

            print(f"Data selecionada: {data_desejada}")

            try:
                aba_agenda = self.wait_for_element(By.ID, "abaAgenda")
                self.execute_script("arguments[0].click();", aba_agenda)
            except Exception as e:
                print(f"Erro ao tentar clicar em abaAgenda via JS: {e}")
                return {
                    "status": "error",
                    "message": "Falha ao clicar na aba de agenda.",
                }

            self._is_timetable()

            print(
                f"Data selecionada: {data_desejada}. Verificando horários entre {horario_inicial} e {horario_final}."
            )

            try:
                no_expediente_element = self.wait_for_element(
                    By.XPATH,
                    "//div[contains(@class, 'alert-info') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'não há expediente')]",
                    timeout=5,
                )
                if no_expediente_element:
                    return {
                        "status": "unavailable",
                        "message": f"A data {data_desejada} não tem expediente.",
                    }
            except TimeoutException:
                pass

            horario_inicial_id = int(
                (horario_inicial or "07:00").replace(":", "") + "00"
            )
            horario_final_id = int((horario_final or "19:30").replace(":", "") + "00")

            elementos_filhos_xpath = "//tr[@class='ui-droppable' and normalize-space(td[2]) = '' and not(td[2]/*)]"
            elementos_filhos = self.find_elements(By.XPATH, elementos_filhos_xpath)

            available_times = []

            if elementos_filhos:
                for slot_tr in elementos_filhos:
                    slot_id = slot_tr.get_attribute("id")
                    print(
                        f"Id do slot: {slot_id}, inicial: {horario_inicial_id}, final: {horario_final_id}"
                    )
                    if (
                        slot_id
                        and (int(slot_id) >= horario_inicial_id)
                        and (int(slot_id) <= horario_final_id)
                    ):
                        available_times.append(
                            slot_tr.find_element(By.TAG_NAME, "a").text
                        )

            return {
                "status": "success",
                "date": data_desejada,
                "slots": available_times,
            }
        else:
            current_date = datetime.now()
            for i in range(365):
                check_date_str_display = current_date.strftime("%d/%m/%Y")
                check_date_iso = current_date.strftime("%Y-%m-%d")

                try:
                    dateAppointment = self.wait_for_element(By.ID, "dataAgenda")
                    self.execute_script(
                        "arguments[0].value = arguments[1];",
                        dateAppointment,
                        check_date_iso,
                    )
                    self.execute_script(
                        "arguments[0].dispatchEvent(new Event('blur'));",
                        dateAppointment,
                    )
                except Exception as e:
                    print(
                        f"Erro ao injetar data {check_date_iso} via JS: {e}. Pulando dia."
                    )
                    self.save_screenshot(f"debug_js_loop_fail_{check_date_iso}.png")
                    current_date += timedelta(days=1)
                    continue

                try:
                    aba_agenda = self.wait_for_element(By.ID, "abaAgenda")
                    self.execute_script("arguments[0].click();", aba_agenda)
                except Exception as e:
                    print(f"Erro ao tentar clicar em abaAgenda via JS: {e}")
                    current_date += timedelta(days=1)
                    continue

                try:
                    self.wait_for_element(By.XPATH, "//tr[@id='070000']")
                    self.wait_for_element(
                        By.XPATH,
                        "//div[contains(@class, 'alert-info') and contains(text(), 'expediente')]",
                    )
                except TimeoutException:
                    print(
                        f"A grade de horários para {check_date_str_display} não carregou (Timeout). Pulando."
                    )
                    current_date += timedelta(days=1)
                    continue

                print(f"Verificando data: {check_date_str_display}")

                is_working_day = True

            try:
                self.wait_for_element(
                    By.XPATH,
                    "//div[contains(@class, 'alert-info') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'não há expediente')]",
                    timeout=5,
                )
                is_working_day = False
            except TimeoutException:
                pass

                if is_working_day:
                    print(
                        f"Data {check_date_str_display} é um dia de trabalho. Verificando horários..."
                    )
                    try:
                        available_slot_xpath = (
                            "//a[starts-with(@href, 'javascript:marcaHorarioAgenda')]"
                        )

                        available_slots = self.find_elements(
                            By.XPATH, available_slot_xpath
                        )

                        if available_slots:
                            next_time = available_slots[0].text
                            print(
                                f"Próximo horário disponível encontrado: {next_time} em {check_date_str_display}"
                            )
                            return {
                                "status": "success",
                                "date": check_date_str_display,
                                "time": next_time,
                            }
                        else:
                            print(
                                f"Nenhum horário vago encontrado em {check_date_str_display}."
                            )
                    except TimeoutException:
                        print(
                            f"Nenhum horário vago encontrado em {check_date_str_display}."
                        )
                    except NoSuchElementException:
                        pass
                else:
                    print(
                        f"Data {check_date_str_display} é um fim de semana ou feriado."
                    )

            current_date += timedelta(days=1)

            return {
                "status": "not_found",
                "message": "Nenhum horário disponível encontrado no próximo ano.",
            }

    def verify_doctors_calendar(
        self,
        medico: str,
        data_desejada: str | None = None,
        horario_desejado: str | None = None,
        horario_inicial: str | None = None,
        horario_final: str | None = None,
    ):
        """
        Verifica a disponibilidade da agenda de um médico.
        """

        try:
            self._login(medico)

            self._close_modal()

            print("Iniciando fluxo de verificação de agenda...")

            if self.is_softclyn_of:
                self._click_on_appointment_menu()

            self._search_doctor(medico)

            result = self._verify_availability(
                data_desejada, horario_desejado, horario_inicial, horario_final
            )

            return result
        except TimeoutException as e:
            print(f"Erro: Timeout! O elemento não foi encontrado a tempo. {e}")
            self.save_screenshot("error_screenshot_verify.png")
            return {"status": "error", "message": f"A timeout occurred: {e}"}
        except Exception as e:
            print(f"Erro inesperado: {e}")
            self.save_screenshot("error_screenshot_verify.png")
            return {"status": "error", "message": str(e)}
        finally:
            print("Fechando o navegador.")
            if "self" in locals():
                self.quit()
            else:
                print("self não encontrado.")
