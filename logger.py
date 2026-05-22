import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    """Configure root logger: RotatingFileHandler (logs/app.log) + StreamHandler."""
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(stream_handler)

    _init_sentry()


def _init_sentry() -> None:
    """
    Initialise Sentry si SENTRY_DSN est défini dans l'environnement.

    Comportement :
    - Sans SENTRY_DSN : retour immédiat, aucun import sentry_sdk, zéro overhead.
    - Avec SENTRY_DSN : LoggingIntegration capture automatiquement
        WARNING+ → breadcrumb Sentry
        ERROR+   → événement Sentry (inclut les erreurs LLM du gateway)
    - Non-bloquant : toute erreur d'initialisation est loggée et ignorée.
    """
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                LoggingIntegration(
                    level=logging.WARNING,      # WARNING+ → breadcrumb
                    event_level=logging.ERROR,  # ERROR+   → événement Sentry
                ),
            ],
            traces_sample_rate=0.0,
            environment=os.getenv("APP_ENV", "production"),
            release=os.getenv("APP_VERSION", "unknown"),
        )
        logging.getLogger(__name__).info(
            "Sentry initialisé (env=%s, dsn=...%s)",
            os.getenv("APP_ENV", "production"),
            dsn[-6:],
        )
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Sentry init échoué (non bloquant) : %s", exc
        )
