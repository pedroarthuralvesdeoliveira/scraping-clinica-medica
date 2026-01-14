import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC

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
            By.ID, "select2-convenio-container", expectation=EC.element_to_be_clickable
        )
        if select_convenio_clickable:
            try:
                select_convenio_clickable.click()
            except:
                self.execute_script("arguments[0].click();", select_convenio_clickable)

        search_field_xpath = "//span[contains(@class,'select2-container--open')]//input[@class='select2-search__field']"
        search_field = self.wait_for_element(
            By.XPATH, search_field_xpath, expectation=EC.element_to_be_clickable
        )
        if search_field:
            search_field.clear()
            search_field.send_keys(convenio_nome.strip())
            time.sleep(1)

        option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{convenio_nome.upper()}')]"
        option = self.wait_for_element(
            By.XPATH, option_xpath, expectation=EC.element_to_be_clickable
        )
        if option:
            try:
                option.click()
            except:
                self.execute_script("arguments[0].click();", option)

        print(f"Convênio '{convenio_nome}' selecionado com sucesso.")

    def _select_tipo_atendimento(self, tipo_atendimento: str | None = "Primeira vez"):
        print(f"Selecionando tipo de atendimento: {tipo_atendimento}")

        select_tipo_clickable = self.wait_for_element(
            By.ID,
            "select2-tipoAtendimento-container",
            expectation=EC.element_to_be_clickable,
            timeout=15,
        )

        if not select_tipo_clickable:
            print(
                "ERRO: O container do Select2 para tipo de atendimento não foi encontrado a tempo."
            )
            return
        try:
            select_tipo_clickable.click()
        except:
            self.execute_script("arguments[0].click();", select_tipo_clickable)

        search_field_xpath = "//span[contains(@class,'select2-container--open')]//input[@class='select2-search__field']"
        search_field = self.wait_for_element(
            By.XPATH,
            search_field_xpath,
            expectation=EC.element_to_be_clickable,
            timeout=20,
        )

        if not search_field:
            print(
                "ERRO: O campo de busca do Select2 para tipo de atendimento não foi encontrado a tempo."
            )
            return
        print("Campo de busca do Select2 para tipo de atendimento encontrado.")

        if search_field:
            search_field.clear()
            search_field.send_keys(tipo_atendimento.strip())  # pyright: ignore[reportOptionalMemberAccess]
            time.sleep(1)

        option_xpath = f"//li[contains(@class, 'select2-results__option') and contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{(tipo_atendimento or '').upper()}')]"
        option = self.wait_for_element(
            By.XPATH, option_xpath, expectation=EC.element_to_be_clickable
        )

        if option:
            try:
                option.click()
            except:
                self.execute_script("arguments[0].click();", option)
            print(f"Tipo de Atendimento '{tipo_atendimento}' selecionado com clique.")
        else:
            print(
                f"ERRO: Opção para o tipo de atendimento '{tipo_atendimento}' não encontrada para clique."
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

            horario_link_xpath = f"//tr[@id='{horario_id}']//a[starts-with(@href, 'javascript:marcaHorarioAgenda') and normalize-space()='{horario_desejado}']"
            horario_link = self.wait_for_element(By.XPATH, horario_link_xpath)

            if horario_link:
                print(
                    f"O horário {horario_desejado}, formatado como {horario_id}, do dia {data_desejada} está DISPONÍVEL para o profissional selecionado."
                )
                try:
                    horario_link.click()
                except Exception as e:
                    print(f"Erro ao clicar no horário {horario_desejado}: {e}")
                    self.execute_script("arguments[0].click();", horario_link)
            else:
                print(
                    f"O horário {horario_desejado}, formatado como {horario_id}, do dia {data_desejada} NÃO está disponível ou não existe como opção de agendamento."
                )
                return {
                    "status": "unavailable",
                    "message": f"Horário {horario_desejado} em {data_desejada} indisponível.",
                }


            select_type_of_search = self.wait_for_element(By.ID, "tipoPesquisaPaciente")
            if select_type_of_search:
                try:
                    select_type_of_search.click()
                except:
                    self.execute_script("arguments[0].click();", select_type_of_search)
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

            paciente_encontrado = self.wait_for_element(
                By.XPATH, 
                "//td[contains(@onclick, 'selecionaPacienteAgenda')]", 
                timeout=15, 
                expectation=EC.visibility_of_element_located
            )

            if paciente_encontrado:
                print(f"Paciente encontrado na base (ID/Nome: {paciente_encontrado.text}). Selecionando existente...")
                self.execute_script("arguments[0].click();", paciente_encontrado)
                
                print(f"Paciente com CPF {cpf_paciente} selecionado com sucesso.")

                time.sleep(2)

                data_nascimento_input = self.wait_for_element(
                    By.ID, "dataNascimentoAgenda"
                )
                
                if data_nascimento_input:
                    valor_atual = data_nascimento_input.get_attribute("value")
        
                    if not valor_atual or valor_atual.strip() == "" or "/" not in valor_atual:
                        print(f"Campo data de nascimento vazio. Preenchendo com: {paciente_info['data_nascimento']}")
                        data_nascimento_input.send_keys(paciente_info["data_nascimento"])
                    else:
                        print(f"Data de nascimento já preenchida no sistema: {valor_atual}")

                print(
                    f"Data de nascimento preenchida: {paciente_info['data_nascimento']}"
                )

                time.sleep(2)

            else:
                print(
                    f"Paciente com CPF {cpf_paciente} não apareceu na tabela. Verificando botão de novo cadastro..."
                )

                self.save_screenshot("debug_paciente_nao_encontrado.png")

                time.sleep(2)

                criar_paciente_xpath = (
                    "//td[contains(@onclick, 'adicionaPacienteNovoAgenda')]" 
                )
                criar_paciente_button = self.wait_for_element(
                    By.XPATH,
                    criar_paciente_xpath,
                    expectation=EC.element_to_be_clickable,
                    timeout=20,
                )

                if not criar_paciente_button:
                    print(
                        "ERRO: O botão de 'Cadastrar Novo' não apareceu após a pesquisa."
                    )
                    self.save_screenshot("erro_botao_cadastrar_novo.png")
                    return {
                        "status": "error",
                        "message": "Falha na pesquisa do paciente.",
                    }

                try:
                    criar_paciente_button.click()
                except:
                    self.execute_script("arguments[0].click();", criar_paciente_button)

                data_nascimento_input = self.wait_for_element(
                    By.ID, "dataNascimentoAgenda"
                )
                if data_nascimento_input:
                    data_nascimento_input.send_keys(paciente_info["data_nascimento"])

                print(
                    f"Data de nascimento preenchida: {paciente_info['data_nascimento']}"
                )

                telefone_input = self.wait_for_element(By.ID, "numeroTelefone")
                telefone_val = paciente_info["telefone"]
                self.execute_script(
                    "arguments[0].value = arguments[1];", telefone_input, telefone_val
                )
                self.execute_script(
                    "arguments[0].dispatchEvent(new Event('change'));", telefone_input
                )

                print(f"Telefone preenchido: {paciente_info['telefone']}")

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

                self.wait_for_staleness_element(botao_salvar, timeout=15)

                time.sleep(5)
                return {
                    "status": "success",
                    "message": "Agendamento de novo paciente realizado.",
                }

            if paciente_info["convenio"]:
                self._select_convenio_digitando(paciente_info["convenio"])

            self._select_tipo_atendimento(tipo_atendimento)

            botao_salvar = self.wait_for_element(
                By.ID,
                "btSalvarAgenda",
                expectation=EC.element_to_be_clickable,
                timeout=20,
            )

            if not botao_salvar:
                print(
                    "Botão 'Salvar' por ID não encontrado. Tentando estratégia reforçada..."
                )

                try:
                    botao_salvar = self.wait_for_element(
                        By.CSS_SELECTOR,
                        "button#btSalvarAgenda.btn.btn-success",
                        timeout=15,
                    )
                    if botao_salvar:
                        print("Botão 'Salvar' encontrado via CSS Selector.")
                except Exception:
                    pass

            if not botao_salvar:
                print("Tentando encontrar pelo texto 'Salvar'...")
                botao_salvar = self.wait_for_element(
                    By.XPATH,
                    "//button[@id='btSalvarAgenda']//span[contains(text(), 'Salvar')]",
                    timeout=15,
                )

            if botao_salvar:
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", botao_salvar)
                    time.sleep(1)
                    botao_salvar.click()
                    print("Botão 'Salvar' clicado nativamente.")
                except Exception as e:
                    print(f"Clique nativo falhou, tentando via JS: {e}")
                    self.execute_script("arguments[0].click();", botao_salvar)

                try:
                    erro_feedback = self.wait_for_element(By.CLASS_NAME, "alert-danger", timeout=3)
                    if erro_feedback and erro_feedback.is_displayed():
                        print(f"ERRO DE VALIDAÇÃO NO SISTEMA: {erro_feedback.text}")
                        self.save_screenshot("erro_validacao_sistema.png")
                        return {"status": "error", "message": f"Sistema recusou: {erro_feedback.text}"}
                except:
                    pass

                foi_fechado = self.wait_for_staleness_element(botao_salvar, timeout=15)

                if foi_fechado:
                    print("Agendamento concluído com sucesso (modal fechado)!")
                    return {"status": "success", "message": "Agendamento realizado."}
                else:
                    print("ALERTA: O modal de agendamento não fechou após o clique em Salvar.")
                    self.save_screenshot("erro_modal_preso.png")
                    return {"status": "error", "message": "O modal de agendamento não fechou."}

            else:
                print(
                    "ERRO: Botão 'Salvar' não encontrado para agendamento de paciente existente."
                )
                self.save_screenshot("erro_botao_salvar_paciente_existente.png")
                return {"status": "error", "message": "O modal de agendamento não fechou."}


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
