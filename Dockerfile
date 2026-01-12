FROM python:3.12-slim

# Ускоряем зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем библиотеку CACL в режиме разработки
COPY ./cacl ./cacl
RUN pip install -e ./cacl

COPY ./app ./app

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
