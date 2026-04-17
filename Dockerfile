FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m nltk.downloader stopwords -d /usr/local/share/nltk_data stopwords


COPY . .
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1', 8501)); s.close()"

CMD ["streamlit","run","main.py","--server.port=8501","--server.address=0.0.0.0"]
