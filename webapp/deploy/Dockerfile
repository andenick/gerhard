# Gerhard website — production image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/webapp

WORKDIR /app

COPY webapp/requirements.txt /app/webapp/requirements.txt
RUN pip install --no-cache-dir -r /app/webapp/requirements.txt

COPY webapp /app/webapp

# vendor plotly at build time; build_cache runs as an init step in compose
RUN python /app/webapp/data_pipeline/vendor.py || true

EXPOSE 8080
CMD ["gunicorn", "app.main:app", "--chdir", "/app/webapp", \
     "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8080", "--timeout", "120"]
