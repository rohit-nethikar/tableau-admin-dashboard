# Platform-neutral image for the Tableau Admin Dashboard.
# Keep this image single-instance while the app uses SQLite + an in-process scheduler.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=5000 \
    APP_DATA_DIR=/app/data

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/data

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('APP_PORT','5000'); urllib.request.urlopen('http://127.0.0.1:' + port + '/health', timeout=3).read()" || exit 1

CMD ["python", "app.py"]
