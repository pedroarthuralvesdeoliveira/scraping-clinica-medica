# Automação e Scraping para SOFTCLYN

Este projeto consiste em um conjunto de scripts de automação e scraping para o sistema de agendamento do cliente. Utilizando Selenium, os scripts interagem com a interface web para realizar tarefas como agendamento e cancelamento de consultas e verificação de disponibilidade de médicos.

A aplicação expõe uma API RESTful (utilizando FastAPI e Celery) para gerenciar essas operações de forma assíncrona.

## Funcionalidades Principais

*   **Agendar Consulta (`schedule_appointment_task`):** Agenda uma nova consulta para um paciente com um profissional específico em uma data e horário determinados.
*   **Cancelar Consulta (`cancel_appointment_task`):** Cancela um agendamento existente com base no profissional, data, hora e nome do paciente.
*   **Verificar Disponibilidade (`verify_doctors_calendar_task`):** Verifica a agenda de um profissional. Pode ser usado para encontrar o próximo horário livre ou para checar a disponibilidade de um dia e hora específicos.

## Requisitos

*   Python 3.13+
*   Google Chrome
*   Servidor Redis (para Celery)
*   Variável de ambiente `API_KEY` configurada.
*   Dependências Python (veja `pyproject.toml`):
    *   `celery>=5.5.3`
    *   `fastapi>=0.120.0`
    *   `python-dotenv>=1.1.1`
    *   `redis>=7.0.1`
    *   `selenium>=4.37.0`
    *   `uvicorn>=0.38.0`
    *   `webdriver-manager>=4.0.2`

## Configuração

### 1. Dependências

Clone este repositório e instale as dependências. Se você estiver usando `uv`, basta executar:

```bash
uv sync
```

### 2. Variáveis de Ambiente

Copie o arquivo `.env.example` para um novo arquivo chamado `.env` e preencha com suas credenciais e a chave da API.

```bash
# Credenciais de acesso ao SOFTCLYN
SOFTCLYN_URL="sua_url_aqui"
SOFTCLYN_USER="seu_usuario_aqui"
SOFTCLYN_PASS="sua_senha_aqui"

# Chave da API para autenticação
API_KEY="SUA_CHAVE_DE_API_SECRETA"

# Configuração do broker Celery (Redis)
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

### 3. Executando os Serviços

Para iniciar a API, o worker Celery e o Redis (se não estiver rodando), você pode usar Docker Compose ou executá-los manualmente.

**Manual:**

1.  **Iniciar o Redis:** Certifique-se de que um servidor Redis esteja em execução, por exemplo:
    ```bash
    redis-server
    ```
2.  **Iniciar o Celery Worker:** Em um terminal separado:
    ```bash
    uv run celery -A celery_worker.celery worker --loglevel=info -c 4 --max-tasks-per-child=50    ```
3.  **Iniciar a FastAPI:** Em outro terminal separado:
    ```bash
    uvicorn api:app --host 0.0.0.0 --port 8000
    ```
    Ou 
    ```bash
    uv run api.py
    ```

## Utilizando a API

A API requer uma chave de autenticação que deve ser enviada no cabeçalho `X-API-Key`.

### Para Agendar uma Consulta

Endpoint: `/schedule`
Método: `POST`

```http
POST /schedule HTTP/1.1
Host: localhost:8000
X-API-Key: SUA_CHAVE_DE_API

Content-Type: application/json
{
    "medico": "Dr. Nome do Médico",
    "data_desejada": "DD/MM/AAAA",
    "horario_desejado": "HH:MM",
    "nome_paciente": "Nome Completo do Paciente",
    "data_nascimento": "DD/MM/AAAA",
    "cpf": "123.456.789-00",
    "telefone": "5511987654321",
    "tipo_atendimento": "Consulta",
    "convenio": "Nome do Convênio (opcional)"
}
```

### Para Cancelar uma Consulta

Endpoint: `/cancel`
Método: `POST`

```http
POST /cancel HTTP/1.1
Host: localhost:8000
X-API-Key: SUA_CHAVE_DE_API
Content-Type: application/json

{
    "medico": "Dr. Nome do Médico",
    "data_desejada": "DD/MM/AAAA",
    "horario_desejado": "HH:MM",
    "nome_paciente": "Nome Completo do Paciente"
}
```

### Para Verificar Disponibilidade

Endpoint: `/availability`
Método: `GET`

Parâmetros de Query:
*   `medico` (obrigatório): Nome do médico (ex: `Dr. Nome`)
*   `data_desejada` (opcional): Data específica para verificar (ex: `DD/MM/AAAA`)
*   `horario_desejado` (opcional): Horário específico para verificar (ex: `HH:MM`)
*   `horario_inicial` (opcional): Horário de início para um intervalo (ex: `HH:MM`)
*   `horario_final` (opcional): Horário de fim para um intervalo (ex: `HH:MM`)

Exemplos de requisição:

```http
GET /availability?medico=Dr.Nome&data_desejada=25/10/2025&horario_desejado=14:00 HTTP/1.1
Host: localhost:8000
X-API-Key: SUA_CHAVE_DE_API
```

```http
GET /availability?medico=Dr.Nome HTTP/1.1
Host: localhost:8000
X-API-Key: SUA_CHAVE_DE_API
```

### Verificando o Status da Tarefa

Endpoint: `/task_status/{task_id}`
Método: `GET`

Após enviar uma tarefa de agendamento, cancelamento ou verificação, você receberá um `task_id`. Use este endpoint para verificar o status e o resultado da tarefa.

```http
GET /task_status/SEU_TASK_ID_AQUI HTTP/1.1
Host: localhost:8000
X-API-Key: SUA_CHAVE_DE_API
```

## Estrutura de Pastas

```
.
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version
├── Dockerfile
├── README.md
├── api.py                     # Define a API FastAPI e seus endpoints.
├── cancel_appointment.py      # Lógica de scraping para cancelar agendamentos.
├── celery_worker.py           # Configuração do Celery e definição das tarefas assíncronas.
├── pyproject.toml             # Metadados do projeto e dependências Python.
├── schedule_appointment.py    # Lógica de scraping para agendar novos compromissos.
├── uv.lock                    # Gerenciamento de dependências com uv.
└── verify_doctors_calendar.py # Lógica de scraping para verificar disponibilidade.
├── .venv/                     # Ambiente virtual Python.
└── __pycache__/               # Cache de bytecode do Python.
```
