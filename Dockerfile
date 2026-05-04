FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --no-dev

COPY main.py .
COPY src ./src

RUN uv sync --frozen --no-dev

RUN uv run python -m nltk.downloader stopwords -d /usr/local/share/nltk_data stopwords

CMD ["uv", "run", "streamlit", "run", "main.py"]
