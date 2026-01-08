FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY . .

CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]

