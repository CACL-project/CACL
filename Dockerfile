FROM python:3.12-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy CACL library and its pyproject.toml, then install in dev mode
COPY pyproject.toml .
COPY README_PYPI.md .
COPY ./cacl ./cacl
RUN pip install -e .

COPY ./app ./app
COPY ./scripts ./scripts
COPY ./tests ./tests

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
