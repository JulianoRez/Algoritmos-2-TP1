FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY geofrota geofrota
COPY assets assets
COPY data data

EXPOSE 8050
# Um único processo: a frota gerada fica na memória dele e é compartilhada
# pelas threads que atendem as requisições.
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "1", "--threads", "4", "--timeout", "120", "app:server"]
