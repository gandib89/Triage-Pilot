FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ollama is a separate service (see docker-compose.yml) — this image is the
# API tier only, so it can scale independently of the LLM host.
ENV DJANGO_SETTINGS_MODULE=backend.settings
EXPOSE 8000

CMD python manage.py migrate --noinput \
    && python manage.py collectstatic --noinput \
    && gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
