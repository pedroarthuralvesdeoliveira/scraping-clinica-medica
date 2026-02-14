FROM python:3.13-slim-bookworm AS base
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /code
RUN pip install uv


FROM base AS python_deps
COPY pyproject.toml uv.lock* README.md ./

RUN uv venv /opt/venv
RUN . /opt/venv/bin/activate && uv sync --frozen

FROM base AS api
COPY --from=python_deps /opt/venv /opt/venv

COPY . .
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS worker
ENV DEBIAN_FRONTEND=noninteractive

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

RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

COPY --from=python_deps /opt/venv /opt/venv

COPY . .

ENV PATH="/opt/venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD celery -A app.worker.celery_app:celery inspect ping || exit 1

CMD ["uv", "run", "celery", "-A", "app.worker.celery_app:celery", "worker", "--loglevel=info", "-c", "1", "--max-tasks-per-child=10"]


FROM base AS orchestrator
COPY --from=python_deps /opt/venv /opt/venv
COPY . .
ENV PATH="/opt/venv/bin:$PATH"
CMD ["uv", "run", "python", "-m", "app.orchestrator"]