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
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS worker
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip curl gnupg \
    ca-certificates \
    libglib2.0-0 libnss3 libgdk-pixbuf-2.0-0 \
    libatk-bridge2.0-0 libatk1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
    libxcursor1 libxdamage1 libxext6 libxfixes3 \
    libxi6 libxrandr2 libxrender1 \
    libxss1 libxtst6 libgbm1 \
    fonts-liberation libasound2 \
    && rm -rf /var/lib/apt/lists/*


RUN CHROME_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) \
    && echo "Instalando Chrome-for-Testing versão $CHROME_VERSION" \
    \
    && wget -O chrome.zip "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION/linux64/chrome-linux64.zip" \
    && unzip chrome.zip -d /opt && rm chrome.zip \
    && ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome \
    \
    && wget -O chromedriver.zip "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver.zip -d /opt && rm chromedriver.zip \
    && ln -s /opt/chromedriver-linux64/chromedriver /usr/bin/chromedriver

COPY --from=python_deps /opt/venv /opt/venv
COPY . .

ENV PATH="/opt/venv/bin:$PATH"
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV SELENIUM_MANAGER_DISABLED=1 

CMD ["uv", "run", "celery", "-A", "celery_worker.celery", "worker", "--loglevel=info", "-c", "4", "--max-tasks-per-child=50"]