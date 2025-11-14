# ---- Estágio 1: Base (Python + uv) ----
# Usamos um "apelido" 'AS base' para este estágio
FROM python:3.13-slim-bookworm AS base
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /code
RUN pip install uv

# ---- Estágio 2: Dependências Python ----
# Instala TODAS as dependências Python em uma pasta separada
FROM base AS python_deps
COPY pyproject.toml uv.lock* README.md ./

# --- CORREÇÃO AQUI ---
# 1. Cria o virtual environment
RUN uv venv /opt/venv
# 2. Ativa o venv e instala as dependências DENTRO dele
RUN . /opt/venv/bin/activate && uv sync --frozen
# --- FIM DA CORREÇÃO ---

# ---- Estágio 3: Imagem Final da API (Leve) ----
# Este é o nosso alvo 'api'
FROM base AS api
# Copia apenas o .venv com as dependências prontas
COPY --from=python_deps /opt/venv /opt/venv
# Copia o código-fonte
COPY . .
# Seta o PATH para que o 'uv' e 'python' usem o .venv
ENV PATH="/opt/venv/bin:$PATH"
# Expõe a porta da API
EXPOSE 8000
# Define o comando da API
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


# ---- Estágio 4: Imagem Final do Worker (Pesada) ----
# Este é o nosso alvo 'worker'
FROM base AS worker
# 1. Instala as dependências de sistema (apt-get) para o Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libgbm1 \
    libu2f-udev \
    ca-certificates \
    xvfb \
    && rm -rf /var/lib/apt/lists/*


# 2. Instala o Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 3. Copia o .venv com as dependências Python
COPY --from=python_deps /opt/venv /opt/venv
# 4. Copia o código-fonte
COPY . .
# 5. Seta as ENVs do Chrome
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
# 6. Seta o PATH para usar o .venv
ENV PATH="/opt/venv/bin:$PATH"
# 7. Define o comando do Worker
CMD ["uv", "run", "celery", "-A", "celery_worker.celery", "worker", "--loglevel=info", "-c", "8", "--max-tasks-per-child=50"]