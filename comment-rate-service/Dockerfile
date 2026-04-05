FROM bookstore-base:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["sh", "-c", "until python -c \"import os,socket; s=socket.socket(); s.settimeout(2); s.connect((os.getenv('DB_HOST','localhost'), int(os.getenv('DB_PORT','3306')))); s.close()\"; do sleep 2; done; python manage.py makemigrations core && python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
