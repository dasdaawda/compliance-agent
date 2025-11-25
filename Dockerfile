FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "compliance_app.wsgi:application"]