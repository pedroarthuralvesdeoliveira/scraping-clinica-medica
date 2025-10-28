# Automação e Scraping para SoftClyn

Este projeto consiste em um conjunto de scripts de automação e scraping para o sistema de agendamento SoftClyn. Utilizando Selenium, os scripts interagem com a interface web para realizar tarefas como agendamento e cancelamento de consultas e verificação de disponibilidade de médicos.


## Funcionalidades Principais

* **Agendar Consulta (`schedule_appointment.py`):** Agenda uma nova consulta para um paciente com um profissional específico em uma data e horário determinados.
* **Cancelar Consulta (`cancel_appointment.py`):** Cancela um agendamento existente com base no profissional, data, hora e nome do paciente.
* **Verificar Disponibilidade (`verify_doctors_calendar.py`):** Verifica a agenda de um profissional. Pode ser usado para encontrar o próximo horário livre ou para checar a disponibilidade de um dia e hora específicos.

## Requisitos

* Python 3.13+
* Google Chrome
* Dependências Python (veja `pyproject.toml`):
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

    /__pycache__: Cache de bytecode do Python.

    schedule_appointment.py: Script para criar novos agendamentos.

    cancel_appointment.py: Script para remover agendamentos.

    verify_doctors_calendar.py: Script para checar horários livres.

