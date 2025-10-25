# Automação e Scraping para SoftClyn

Este projeto consiste em um conjunto de scripts de automação e scraping para o sistema de agendamento SoftClyn. Utilizando Selenium, os scripts interagem com a interface web para realizar tarefas como agendamento e cancelamento de consultas, verificação de disponibilidade de médicos e a extração de relatórios de agendamentos.

Os dados extraídos dos relatórios são processados com `pandas` e preparados para serem enviados a um banco de dados Supabase.

## Funcionalidades Principais

* **Agendar Consulta (`schedule_appointment.py`):** Agenda uma nova consulta para um paciente com um profissional específico em uma data e horário determinados.
* **Cancelar Consulta (`cancel_appointment.py`):** Cancela um agendamento existente com base no profissional, data, hora e nome do paciente.
* **Verificar Disponibilidade (`verify_doctors_calendar.py`):** Verifica a agenda de um profissional. Pode ser usado para encontrar o próximo horário livre ou para checar a disponibilidade de um dia e hora específicos.
* **Extração de Relatórios (`scraper.py`):** Realiza o login, navega até a seção de relatórios, aplica filtros (como "Todos" os profissionais e data atual) e baixa o relatório de agendamentos em formato `.xls` para a pasta `download/`.
* **Processamento de Relatório (`parse_clinic_report.py`):** Lê o arquivo `.xls` baixado, que possui uma estrutura de blocos por médico, e o transforma em um dicionário Python estruturado.
* **Upload para Supabase (`upload_to_supabase.py`):** Utiliza o script de parsing para processar o relatório e, em seguida, formata e envia os dados de agendamento para a tabela configurada no Supabase.

## Requisitos

* Python 3.13+
* Google Chrome
* Dependências Python (veja `pyproject.toml`):
    * `pandas`
    * `python-dotenv`
    * `selenium`
    * `webdriver-manager`

## Configuração

### 1. Dependências

Clone este repositório e instale as dependências. Se você estiver usando `uv`, basta executar:

```bash
uv sync
```

### 2. Variáveis de Ambiente

Copie o arquivo .env.example para um novo arquivo chamado .env e preencha com suas credenciais:
Ini, TOML

#Credenciais de acesso ao SoftClyn
```bash
SOFTCLYN_URL="[https://app.softclyn.com/endoclin_ouro/view/principal.php](https://app.softclyn.com/endoclin_ouro/view/principal.php)"
SOFTCLYN_USER="seu_usuario_aqui"
SOFTCLYN_PASS="sua_senha_aqui"

#Credenciais do Supabase
SUPABASE_URL="url_do_seu_projeto_supabase"
SUPABASE_KEY="sua_chave_anon_supabase"
SUPABASE_TABLE="nome_da_tabela_destino"
```

### 3. Instância do Chrome (Importante!)

Os scripts Python são projetados para se conectar a uma instância existente do Google Chrome que esteja rodando em modo de depuração remota (--remote-debugging-port=9222). Isso é feito para reutilizar a sessão, facilitar o login e evitar detecções de automação.

Antes de rodar qualquer script Python, você DEVE primeiro iniciar o Chrome usando o arquivo de lote fornecido:
Bash

```bash
.\instantiate_chrome.bat
```

Isso abrirá uma nova janela do Chrome (ou usará seu perfil padrão) escutando na porta 9222. Mantenha esta janela aberta enquanto os scripts estiverem em execução.

Como Usar

Certifique-se de que a instância do Chrome (passo 3 da configuração) esteja em execução.

### 1. Para Baixar Relatórios e Enviar ao Supabase

O script main.py aciona o scraper.py para baixar o relatório.
```bash
python main.py
```

### 2. Processa o relatório baixado e envia ao Supabase
##### (O script 'upload_to_supabase.py' procura o arquivo em 'download/')
```bash
python upload_to_supabase.py
```



------


Para Agendar uma Consulta

Modifique os parâmetros de exemplo no bloco if __name__ == '__main__': do arquivo schedule_appointment.py e execute:
```bash
python schedule_appointment.py
```

Para Cancelar uma Consulta

Modifique os parâmetros de exemplo no bloco if __name__ == '__main__': do arquivo cancel_appointment.py e execute:
```bash
python cancel_appointment.py
```

Para Verificar Disponibilidade

Modifique os parâmetros de exemplo no bloco if __name__ == '__main__': do arquivo verify_doctors_calendar.py e execute:
```bash
python verify_doctors_calendar.py
```

Estrutura de Pastas

    /download: Pasta de destino dos relatórios .xls baixados. Está incluída no .gitignore.

    /__pycache__: Cache de bytecode do Python.

    main.py: Ponto de entrada para acionar o scraper de relatórios.

    scraper.py: Contém a lógica de login e download do relatório.

    parse_clinic_report.py: Contém a lógica para processar o .xls baixado.

    upload_to_supabase.py: Envia os dados processados para o banco de dados.

    schedule_appointment.py: Script para criar novos agendamentos.

    cancel_appointment.py: Script para remover agendamentos.

    verify_doctors_calendar.py: Script para checar horários livres.

    instantiate_chrome.bat: Script auxiliar para iniciar o Chrome em modo de depuração.