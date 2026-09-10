FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DJANGO_DEBUG=1 DJANGO_COLLECTSTATIC=1 python manage.py collectstatic --noinput && rm -f .local-secret
RUN useradd --create-home notebook && mkdir -p /data/media && chown -R notebook:notebook /app /data
USER notebook
ENV DJANGO_DEBUG=0 DJANGO_MEDIA_ROOT=/data/media DATABASE_URL=sqlite:////data/db.sqlite3
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "90"]
