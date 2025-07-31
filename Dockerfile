FROM python:3.10-slim

WORKDIR /streamlit_app

RUN python -m venv venv
ENV PATH="/streamlit_app/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
EXPOSE 8501
ENTRYPOINT ["streamlit","run","main.py","--server.port=8501"]
