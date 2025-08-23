FROM python:3.12.5-slim

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

COPY . .
# Set ownership to appuser
RUN chown -R appuser:appuser /app

# Switch back to appuser for runtime
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
