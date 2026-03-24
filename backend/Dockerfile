FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar todas las dependencias (incluyendo gunicorn pinned en requirements.txt)
RUN pip install --no-cache-dir --retries=5 --timeout=120 -r requirements.txt

# Copiar código
COPY . .

# Ejecutar como usuario no-root para limitar blast radius ante un RCE.
# Los directorios de escritura (staticfiles, media, models_cache) se crean
# aquí para que appuser tenga permisos; los volúmenes de producción se montan
# sobre estos puntos y heredan la propiedad del mount host.
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/staticfiles /app/media /app/models_cache \
    && chown -R appuser:appuser /app \
    && chmod +x /app/start-web.sh

USER appuser

# Exponer puerto
EXPOSE 8000

# Script de inicio por defecto (aplica migrate y levanta gunicorn)
CMD ["./start-web.sh"]
