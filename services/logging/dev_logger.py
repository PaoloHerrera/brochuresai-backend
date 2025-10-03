import logging
import os
import threading

from config import settings

_lock = threading.Lock()
_configured = False


class PrintLogger:
    def __init__(self, name: str):
        self.name = name

    def _print(self, level: str, msg: str, *args):
        try:
            formatted = msg % args if args else msg
        except Exception:
            formatted = f"{msg} {args}" if args else msg
        print(f"{level}: [{self.name}] {formatted}")

    def debug(self, msg: str, *args):
        self._print("DEBUG", msg, *args)

    def info(self, msg: str, *args):
        self._print("INFO", msg, *args)

    def warning(self, msg: str, *args):
        self._print("WARNING", msg, *args)

    def error(self, msg: str, *args):
        self._print("ERROR", msg, *args)


def _project_root() -> str:
    # services/logging/dev_logger.py -> repo root two levels up
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    with _lock:
        if _configured:
            return

        # En modo desarrollo no configuramos handlers de archivo.
        # En producción, sólo configuramos archivo si FILE_LOGGING=true.
        if bool(getattr(settings, "dev_mode", True)) or not bool(
            getattr(settings, "file_logging", False)
        ):
            _configured = True
            return

        root = _project_root()
        log_dir = os.path.join(root, "logs")
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            # Si no se puede crear, usar directorio actual como fallback
            log_dir = os.getcwd()

        log_path = os.path.join(log_dir, "app.log")

        # Configuración simple de dev: todo a un único archivo, nivel DEBUG
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Evitar duplicar handlers si ya existe uno apuntando al mismo archivo
        same_handler = False
        for h in root_logger.handlers:
            if isinstance(h, logging.FileHandler):
                try:
                    if os.path.abspath(getattr(h, "baseFilename", "")) == os.path.abspath(log_path):
                        same_handler = True
                        break
                except Exception:
                    continue
        if not same_handler:
            root_logger.addHandler(file_handler)

        _configured = True


def get_logger(name: str):
    """
    Dev mode: devuelve un logger que usa print.
    Prod mode: devuelve logging.Logger con escritura a archivo ./logs/app.log.
    """
    _ensure_configured()
    if bool(getattr(settings, "dev_mode", True)) or not bool(
        getattr(settings, "file_logging", False)
    ):
        return PrintLogger(name)
    return logging.getLogger(name)
