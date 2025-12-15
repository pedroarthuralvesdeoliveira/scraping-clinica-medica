import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

from app.scraper.base import Browser


class AppointmentScheduler(Browser):
    def __init__(self):
        super().__init__()

    def _select_convenio_digitando(self, convenio_nome: str):
        """
        Seleciona um convênio digitando o nome no campo select2 de 'convênio'.
        """
        print(f"Selecionando convênio: {convenio_nome}")

        select_convenio_clickable = self.wait_for_element(
            By.ID, "select2-convenio-container"
        )
        if select_convenio_clickable:
            select_convenio_clickable.click()

        search_field_xpath = "//span[contains(@class,'select2-container--open')]//input[@class='select2-search__field']"
        search_field = self.wait_for_element(By.XPATH, search_field_xpath)
        if search_field:
            search_field.clear()
            search_field.send_keys(convenio_nome.strip())

        time.sleep(2)

        option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{convenio_nome.upper()}')]"
        option = self.wait_for_element(By.XPATH, option_xpath)
        if option:
            option.click()

        print(f"Convênio '{convenio_nome}' selecionado com sucesso.")

    def _select_tipo_atendimento(self, tipo_atendimento: str | None = "Primeira vez"):
        print(f"Selecionando tipo de atendimento: {tipo_atendimento}")
        select_tipo_clickable = self.wait_for_element(
            By.ID, "select2-tipoAtendimento-container", timeout=20
        )
        if not select_tipo_clickable:
            print(
                "ERRO: O container do Select2 para tipo de atendimento não foi encontrado a tempo."
            )
            return

        self.execute_script("arguments[0].click();", select_tipo_clickable)

        search_field_xpath = "//span[contains(@class,'select2-selection__rendered')]//input[@class='select2-search__field']"
        search_field = self.wait_for_element(By.XPATH, search_field_xpath, timeout=20)
        if not search_field:
            print(
                "ERRO: O campo de busca do Select2 para tipo de atendimento não foi encontrado a tempo."
            )
            return
        print("Campo de busca do Select2 para tipo de atendimento encontrado.")

        if search_field:
            search_field.clear()
            search_field.send_keys(tipo_atendimento.strip())  # pyright: ignore[reportOptionalMemberAccess]

            time.sleep(2)

            print(f"Tipo de Atendimento '{tipo_atendimento}' selecionado com Enter.")
            search_field.send_keys(Keys.ENTER)
            print("Enviado ENTER para selecionar o tipo de atendimento.")

        if not self.wait_for_staleness_element(search_field):
            print(
                "Campo de busca do Select2 para tipo de atendimento ainda visível após ENTER. Tentando clicar na opção."
            )
        else:
            print(
                "Campo de busca do Select2 para tipo de atendimento desapareceu, indicando seleção por ENTER."
            )
            return

        option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{tipo_atendimento}')]"
        option = self.wait_for_element(By.XPATH, option_xpath)
        if option:
            self.execute_script("arguments[0].click();", option)
            print(f"Clicado na opção de Tipo de Atendimento: {tipo_atendimento}")
            time.sleep(2)
        else:
            print(
                f"ERRO: Opção para o tipo de atendimento '{tipo_atendimento}' não encontrada para clique após tentar ENTER."
            )
            raise TimeoutException(
                f"Service type option '{tipo_atendimento}' not found."
            )

    def schedule_appointment(
        self,
        medico: str,
        data_desejada: str,
        paciente_info: dict,
        horario_desejado: str | None = None,
        tipo_atendimento: str | None = "Primeira vez",
    ):
        """
        Executa a automação de agendamento.
        """

        try:
            self._login(medico)
            self._close_modal()

            print("Iniciando fluxo de agendamento...")

            if self.is_softclyn_of:
                self._click_on_appointment_menu()

            self._search_doctor(medico)

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
                self.execute_script(
                    "arguments[0].value = arguments[1];",
                    dateAppointment,
                    data_formatada_para_input,
                )
                print("Valor da data injetado via JavaScript.")

                print("Disparando 'onblur' via JavaScript para carregar a grade...")
                self.execute_script(
                    "arguments[0].dispatchEvent(new Event('blur'));", dateAppointment
                )

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

            self._is_timetable()

            try:
                horario_id = horario_desejado.replace(":", "") + "00"  # pyright: ignore[reportOptionalMemberAccess]
            except Exception as e:
                print(f"Erro ao formatar o horário: {e}")
                raise ValueError("Formato de horário inválido. Esperado HH:MM")

            try:
                horario_tr_xpath = f"//tr[@id='{horario_id}']"
                self.wait_for_element(By.XPATH, horario_tr_xpath)

            except TimeoutException:
                print(
                    f"Erro: A linha de horário {horario_desejado} (ID: {horario_id}) não foi encontrada."
                )
                return {
                    "status": "error",
                    "message": f"Horário {horario_desejado} não existe na grade.",
                }
            except NoSuchElementException:
                return {
                    "status": "error",
                    "message": f"Horário {horario_desejado} não existe na grade.",
                }

            try:
                elementos_filhos_xpath = f"//tr[@id='{horario_id}']/td[2]/*"
                elementos_filhos = self.wait_for_element(
                    By.XPATH, elementos_filhos_xpath
                )

                if elementos_filhos:
                    print(f"Erro: O horário {horario_desejado} já está OCUPADO.")
                    return {
                        "status": "error",
                        "message": f"Horário {horario_desejado} indisponível.",
                    }
                else:
                    print(f"Horário {horario_desejado} está disponível. Continuando...")

            except Exception as e:
                print(f"Erro inesperado durante a validação do horário: {e}")
                self.save_screenshot("error_screenshot_validacao.png")
                return {"status": "error", "message": str(e)}

            horario_xpath = f"//a[starts-with(@href, 'javascript:marcaHorarioAgenda') and normalize-space()='{horario_desejado}']"

            try:
                horario_slot = self.wait_for_element(By.XPATH, horario_xpath)
                self.execute_script("arguments[0].click();", horario_slot)

                print(f"Horário selecionado (via JS): {horario_desejado}")

            except TimeoutException:
                print(f"Erro: Não foi possível encontrar o horário {horario_desejado}.")
                print(
                    f"Verifique se o horário está vago ou se o XPATH está correto: {horario_xpath}"
                )
                raise
            except Exception as e:
                print(f"Erro ao tentar clicar no horário: {e}")
                raise

            select_type_of_search = self.wait_for_element(By.ID, "tipoPesquisaPaciente")
            if select_type_of_search:
                select_type_of_search.click()
                select = Select(select_type_of_search)
                select.select_by_value("cpf")

            cpf_paciente = paciente_info["cpf"]
            campo_pesquisa_paciente = self.wait_for_element(
                By.XPATH,
                "//input[@placeholder='Digite o Nome do Paciente para Pesquisar']",
            )
            if campo_pesquisa_paciente:
                campo_pesquisa_paciente.send_keys(cpf_paciente)
                campo_pesquisa_paciente.send_keys(Keys.ENTER)

            print(f"Pesquisando paciente: {cpf_paciente}")

            try:
                paciente_encontrado_xpath = (
                    "//td[contains(@onclick, 'selecionaPacienteAgenda')]"
                )
                paciente_encontrado = self.wait_for_element(
                    By.XPATH, paciente_encontrado_xpath
                )
                if paciente_encontrado:
                    self.execute_script("arguments[0].click();", paciente_encontrado)

                print(f"Paciente com CPF {cpf_paciente} encontrado e selecionado.")

            except TimeoutException:
                print(
                    f"Paciente com CPF {cpf_paciente} não encontrado. Iniciando criação de novo paciente."
                )

                criar_paciente_xpath = (
                    "//td[contains(@onclick, 'adicionaPacienteNovoAgenda')]"
                )
                criar_paciente_button = self.wait_for_element(
                    By.XPATH, criar_paciente_xpath
                )
                if criar_paciente_button:
                    criar_paciente_button.click()

                # Data de Nascimento
                data_nascimento_input = self.wait_for_element(
                    By.ID, "dataNascimentoAgenda"
                )
                if data_nascimento_input:
                    data_nascimento_input.send_keys(paciente_info["data_nascimento"])

                print(
                    f"Data de nascimento preenchida: {paciente_info['data_nascimento']}"
                )

                # Telefone
                telefone_input = self.wait_for_element(By.ID, "numeroTelefone")
                telefone_val = paciente_info["telefone"]
                self.execute_script(
                    "arguments[0].value = arguments[1];", telefone_input, telefone_val
                )
                self.execute_script(
                    "arguments[0].dispatchEvent(new Event('change'));", telefone_input
                )

                print(f"Telefone preenchido: {paciente_info['telefone']}")

                # CPF
                cpf_selector = "input[id='cpfPaciente'][type='text']"
                cpf_input = self.wait_for_element(By.CSS_SELECTOR, cpf_selector)
                self.execute_script(
                    "arguments[0].value = arguments[1];",
                    cpf_input,
                    paciente_info["cpf"],
                )
                self.execute_script(
                    "arguments[0].dispatchEvent(new Event('change'));", cpf_input
                )

                print(f"CPF preenchido: {paciente_info['cpf']}")

                self._select_convenio_digitando(paciente_info["convenio"])

                self._select_tipo_atendimento(tipo_atendimento)

                print("Corrigindo o campo 'Nome' como última ação antes de salvar...")

                nome_paciente_input = self.wait_for_element(By.ID, "nomePaciente")
                nome_val = paciente_info["nome"]
                self.execute_script(
                    "arguments[0].value = arguments[1];", nome_paciente_input, nome_val
                )
                self.execute_script(
                    "arguments[0].dispatchEvent(new Event('change'));",
                    nome_paciente_input,
                )

                print(f"Nome final definido como: {nome_val}")

                time.sleep(5)

                botao_salvar = self.wait_for_element(By.ID, "btSalvarAgenda")
                self.execute_script("arguments[0].click();", botao_salvar)
                print("Clicando em 'Salvar' via JS...")

                time.sleep(2)
                return {
                    "status": "success",
                    "message": "Agendamento de novo paciente realizado.",
                }

            if paciente_info["convenio"]:
                self._select_convenio_digitando(paciente_info["convenio"])

            self._select_tipo_atendimento(tipo_atendimento)

            botao_salvar = self.wait_for_element(By.ID, "btSalvarAgenda", timeout=20)

            if not botao_salvar:
                print(
                    "Botão 'Salvar' por ID não encontrado. Tentando estratégia reforçada..."
                )

                # Tentativa 2: CSS Selector específico com classes
                try:
                    botao_salvar = self.wait_for_element(
                        By.CSS_SELECTOR,
                        "button#btSalvarAgenda.btn.btn-success",
                        timeout=5,
                    )
                    if botao_salvar:
                        print("Botão 'Salvar' encontrado via CSS Selector.")
                except Exception as e:
                    pass

            if not botao_salvar:
                print("Tentando encontrar pelo texto 'Salvar'...")
                botao_salvar = self.wait_for_element(
                    By.XPATH,
                    "//button[@id='btSalvarAgenda']//span[contains(text(), 'Salvar')]",
                    timeout=5,
                )

            if botao_salvar:
                self.execute_script("arguments[0].click();", botao_salvar)

            else:
                print(
                    "ERRO: Botão 'Salvar' não encontrado para agendamento de paciente existente."
                )
                self.save_screenshot("erro_botao_salvar_paciente_existente.png")

                try:
                    with open("debug_page_source.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    print("Source da página salvo em 'debug_page_source.html'")
                except Exception as e:
                    print(f"Erro ao salvar source da página: {e}")

                return {"status": "error", "message": "Botão Salvar não encontrado."}

            print("Clicando em 'Salvar' via JS...")
            time.sleep(5)

            print("Agendamento concluído com sucesso!")
            return {"status": "success", "message": "Agendamento realizado."}

        except TimeoutException as e:
            print(f"Erro: Timeout! O elemento não foi encontrado a tempo. {e}")
            self.save_screenshot("error_screenshot.png")
            return {"status": "error", "message": f"A timeout occurred: {e}"}
        except Exception as e:
            print(f"Erro inesperado: {e}")
            self.save_screenshot("error_screenshot.png")
            return {"status": "error", "message": str(e)}
        finally:
            print("Fechando o navegador.")
            if "self" in locals():
                self.quit()
            else:
                print("self não encontrado.")
