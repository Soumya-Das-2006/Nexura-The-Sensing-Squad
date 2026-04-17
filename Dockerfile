FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for Prophet/psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --settings=nexura.settings.production || true

EXPOSE 8000

CMD ["gunicorn", "nexura.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
