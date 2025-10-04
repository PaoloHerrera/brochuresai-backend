Configuración de BrochuresAI

Este documento describe las variables de entorno y opciones de configuración relevantes. Las variables se cargan desde `.env` mediante `config.Settings` y algunos ajustes avanzados se definen en `services/common/config.py`.

Variables de entorno (.env)
- `OPENAI_API_KEY` (string, opcional): API key para OpenAI. Si se omite, el sistema puede operar en modo limitado (dependiendo de `MOCK_LLM`).
- `MAX_BROCHURES_PER_USER` (int, default `3`): cuota por usuario anónimo.
- `DEV_MODE` (bool, default `true`): activa modo desarrollo. En dev se usa un logger simplificado con `print`.
- `FILE_LOGGING` (bool, default `false`): en producción, habilita logs a archivo `./logs/app.log`.
- `TRUST_PROXY` (bool, default `false`): confiar en cabeceras `X-Forwarded-For`/`X-Real-IP` si está detrás de proxy confiable.
- `RATE_LIMIT_MAX_PER_MINUTE` (int, default `10`): límite de solicitudes por minuto.
- `RATE_LIMIT_WINDOW_SECONDS` (int, default `60`): ventana de rate limiting.
- `PLAYWRIGHT_MAX_CONCURRENCY` (int, default `2`): semáforo global para creación de PDFs.
- `PLAYWRIGHT_PDF_TIMEOUT_MS` (int, default `30000`): timeout de render PDF.
- `PLAYWRIGHT_DISABLE_JS` (bool, default `true`): deshabilita JS durante render PDF para mayor estabilidad.
- `SCRAPER_ACCEPT_LANGUAGE` (string, default `en-US,en;q=0.9`): valor para header `Accept-Language` del scraper.
- `SCRAPER_LOG_VERBOSE` (bool, default `false`): controla verbosidad de logs en `services/scraper.py` y `services/openai/openai_client.py`.
- `ALLOWED_ORIGINS` (CSV, default `http://localhost:5173,http://localhost:4173`): orígenes permitidos para CORS.
- `CACHE_COMPRESS` (bool, default `false`): habilita compresión de payloads cacheados.
- `CACHE_COMPRESSION_ALGO` (string, default `gzip`): algoritmo de compresión.
- `CACHE_COMPRESS_MIN_BYTES` (int, default `10240`): tamaño mínimo para comprimir.
- `REDIS_URL` (string, opcional): URL de Redis. En Docker Compose se define por servicio.
- `DATABASE_URL` (string, opcional): ruta SQLite (por defecto `sqlite:///./data/brochuresai.db` en Compose).
- `MOCK_LLM` (bool, opcional): habilita un flujo alternativo sin llamadas reales si está implementado.

Tuning avanzado (definido en código)
Estas opciones viven en `services/common/config.py` para evitar cambios de comportamiento accidental por entorno:
- `OPENAI_DEFAULT_MODEL`: modelo por defecto (`gpt-5-mini`).
- `SCRAPER_DEFAULT_TIMEOUT`: timeout de solicitudes HTTP del scraper (segundos). Default `10`.
- `SCRAPER_MAX_CONCURRENCY`: semáforo para scraping concurrente de detalles. Default `6`.
- `DETAILS_MAX_CHARS`: presupuesto máximo de caracteres agregados antes de enviar al LLM. Default `30000`.

Política de enlaces
- Informativos: solo se conservan enlaces internos (mismo dominio o subdominios).
- Sociales: se incluyen únicamente perfiles/canales válidos de dominios sociales reconocidos y específicos de la empresa.
- Externos no sociales: descartados.

Buenas prácticas
- Producción: `DEV_MODE=false`, `FILE_LOGGING=true`, `SCRAPER_LOG_VERBOSE=false`.
- Definir `ALLOWED_ORIGINS` con los dominios de frontend en producción, sin comodines.
- Ajustar `PLAYWRIGHT_MAX_CONCURRENCY` y `SCRAPER_MAX_CONCURRENCY` según CPU/RAM.
- Mantener `SCRAPER_ACCEPT_LANGUAGE` consistente con el idioma objetivo para mejorar relevancia.