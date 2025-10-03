BrochuresAI Backend

Una API en FastAPI para generar brochures profesionales a partir de sitios web de empresas. Incluye scraping con filtros internos y perfiles sociales específicos, composición asistida por LLM, renderizado PDF con Playwright y rate limiting.

Características
- Scraper con filtros: solo enlaces informativos internos; sociales específicos de la empresa.
- Concurrencia controlada en scraping de detalles y presupuesto de texto.
- Prompts optimizados para selección de enlaces y generación de brochure.
- Render PDF con Playwright (Chromium) y CSS de impresión inline.
- Cache en Redis para detalles y rate limiting por IP.
- Logs con modo dev y opción de escritura a archivo en producción.

Requisitos
- Python 3.13 (recomendado, compatible con slim en Docker).
- Redis accesible (local o contenedor).
- Playwright Chromium instalado (Dockerfile ya lo instala; en local: `python -m playwright install chromium`).

Instalación (local)
- Crear y activar entorno virtual.
- Instalar dependencias: `pip install -r requirements.txt`.
- Instalar Playwright Chromium: `python -m playwright install chromium`.
- Copiar `.env.example` a `.env` y ajustar variables.
- Ejecutar API: `uvicorn main:app --reload --port 8000`.

Arranque con Docker Compose
- `docker-compose up --build`
- Expondrá la API en `http://localhost:8000/` y Redis en `6379`.

Configuración
- Variables principales están documentadas en `docs/configuration.md`.
- Archivo `.env` es leído por Pydantic Settings (ver `config.py`).
- Flags clave:
  - `SCRAPER_LOG_VERBOSE`: controla verbosidad de logs en scraper y cliente OpenAI.
  - `PLAYWRIGHT_*`: controla concurrencia y tiempo de renderizado PDF.

Flujo de enlaces y scraping
- `services/scraper.py` extrae título, texto y enlaces del DOM.
- `services/common/link_utils.py` separa enlaces informativos internos y sociales específicos.
- Enlaces externos no sociales se descartan.
- Concurrencia y presupuesto:
  - `SCRAPER_MAX_CONCURRENCY` (en `services/common/config.py`): límite de scraping concurrente.
  - `DETAILS_MAX_CHARS` (en `services/common/config.py`): tope de caracteres agregados para prompts.

Endpoints principales
- `POST /api/v1/create_brochure`: crea brochure HTML a partir de una URL.
- `POST /api/v1/download_brochure_pdf`: devuelve el PDF del brochure.

Testing
- Ejecutar tests: `pytest -q`.
- La suite valida filtrado de enlaces, headers del scraper, configuración y utilidades.

Notas de despliegue
- En producción, establecer `DEV_MODE=false` y `FILE_LOGGING=true` para logs a archivo.
- Ajustar `PLAYWRIGHT_MAX_CONCURRENCY` según recursos.
- `SCRAPER_LOG_VERBOSE=false` recomendado por defecto.

Configurables relevantes
- En entorno (`.env` / variables): ver `docs/configuration.md`.
- En código (tunables):
  - `OPENAI_DEFAULT_MODEL`: `gpt-5-mini`.
  - `SCRAPER_DEFAULT_TIMEOUT`: timeout HTTP por solicitud.
  - `SCRAPER_MAX_CONCURRENCY`: semáforo de scraping concurrente.
  - `DETAILS_MAX_CHARS`: presupuesto de texto para prompts.