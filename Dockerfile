FROM python:3.10-slim

WORKDIR /streamlit_app

ENV PATH="/streamlit_app/venv/bin:$PATH"
COPY requirements.txt .
RUN python -m venv "$VIRTUAL_ENV" && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m nltk.downloader stopwords


COPY . .
EXPOSE 8501
CMD ["streamlit","run","main.py","--server.port=8501","--server.address=0.0.0.0","--server.fileWatcherType=poll"]
