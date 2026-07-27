FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8068
CMD ["gunicorn", "--bind", "0.0.0.0:8068", "--workers", "1", "--threads", "4", "--timeout", "600", "app.app:app"]
