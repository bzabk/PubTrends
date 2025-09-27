FROM python:3.10-slim

WORKDIR /streamlit_app

ENV PATH="/streamlit_app/venv/bin:$PATH"
COPY requirements.txt .
RUN python -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip -r requirements.txt && \
    python -m nltk.downloader stopwords


COPY . .
EXPOSE 8501
ENTRYPOINT ["streamlit","run","main.py","--server.port=8501"]
