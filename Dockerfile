# Dockerfile

# Use uma imagem base do Python 3.13 (verifique se a versão slim atende, senão use a completa)
# Usando bookworm como base Debian para pacotes mais recentes
FROM python:3.13-slim-bookworm

# Evita prompts interativos durante a instalação de pacotes
ENV DEBIAN_FRONTEND=noninteractive \
    # Define o diretório de trabalho
    WORKDIR=/app \
    # Adiciona o diretório de scripts do uv ao PATH
    PATH="/root/.local/bin:${PATH}" \
    # Configurações de idioma/localidade (pode ajudar com caracteres especiais)
    LANG=pt_BR.UTF-8 \
    LANGUAGE=pt_BR:pt:en \
    LC_ALL=pt_BR.UTF-8

# Instala dependências do sistema:
# - wget e gnupg: para adicionar o repositório do Chrome
# - google-chrome-stable: o próprio navegador Chrome
# - locales: para gerar a localidade pt_BR.UTF-8
# - fonts-ipafont-gothic: fontes adicionais que podem ser necessárias para renderizar páginas
# - Limpa o cache do apt no final para reduzir o tamanho da imagem
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    locales \
    fonts-ipafont-gothic \
    && \
    # Configura a localidade pt_BR
    echo "pt_BR.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen pt_BR.UTF-8 && \
    # Adiciona o repositório do Google Chrome
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    # Instala o Chrome
    apt-get update && \
    apt-get install -y google-chrome-stable --no-install-recommends && \
    # Limpa o cache
    apt-get purge -y --auto-remove wget gnupg && \
    rm -rf /var/lib/apt/lists/*

# Instala o uv (gerenciador de pacotes e venv)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copia os arquivos de definição de dependências e versão do Python
COPY pyproject.toml uv.lock* .python-version* ./

# Instala as dependências do projeto usando uv
# O --system instala no ambiente global do container, o que é comum em Docker
RUN uv sync --system

# Copia o restante do código da aplicação para o diretório de trabalho /app
COPY . .

# Expõe a porta que a API FastAPI usará (se este container for a API)
EXPOSE 8000

# O CMD será definido/sobrescrito na configuração do serviço no Coolify
# Exemplo para API: CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
# Exemplo para Worker: CMD ["celery", "-A", "tasks", "worker", "--loglevel=info", "-c", "1"]