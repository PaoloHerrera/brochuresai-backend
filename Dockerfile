FROM python:3.12.5-slim

# Optimizar runtime Python y pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Install SQL Lite dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 libsqlite3-dev && rm -rf /var/lib/apt/lists/*

# Create a new user and group with home directory
RUN useradd -c "" -s /bin/false -m appuser

WORKDIR /app

COPY requirements.txt .

# Install Python dependencies and chromium as root
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m playwright install --with-deps chromium && \
    # Copy playwright browsers to appuser's cache directory
    mkdir -p /home/appuser/.cache && \
    cp -r /root/.cache/ms-playwright /home/appuser/.cache/ && \
    chown -R appuser:appuser /home/appuser/.cache

# Copiar el código ya con ownership de appuser para evitar una capa de chown
COPY --chown=appuser:appuser . .

# Simple entrypoint to run migrations before starting the app (applies all .sql files)
RUN printf '#!/bin/sh\nset -e\n\n: "${DATABASE_URL}"\nDB_PATH=${DATABASE_URL#sqlite:///}\nif [ -z "$DB_PATH" ] || [ "$DB_PATH" = "$DATABASE_URL" ]; then\n  DB_PATH="./data/brochuresai.db"\nfi\n\nDATA_DIR="$(dirname "$DB_PATH")"\necho "[migrate] using DB path: $DB_PATH"\n# Ensure data dir exists and is writable by appuser (bind mounts may appear as root)\nmkdir -p "$DATA_DIR"\nchown -R appuser:appuser "$DATA_DIR" 2>/dev/null || true\nchmod -R u+rwX "$DATA_DIR" 2>/dev/null || true\n\nif [ -d /app/migrations ]; then\n  for f in /app/migrations/*.sql; do\n    [ -e "$f" ] || continue\n    echo "[migrate] applying $f"\n    su -s /bin/sh -c "sqlite3 \"$DB_PATH\" < \"$f\"" appuser || true\n  done\nfi\n\n# Drop privileges and start server\nexec su -s /bin/sh -c "uvicorn main:app --host 0.0.0.0 --port 8000" appuser\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Switch to root so entrypoint can fix permissions on mounted volumes
USER root

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# CMD kept for reference but entrypoint starts the server itself
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
