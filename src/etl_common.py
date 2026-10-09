"""Configuración compartida para el proceso ETL."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_settings() -> None:
    """Carga variables del archivo .env, sin sobrescribir el entorno actual."""
    load_dotenv(PROJECT_ROOT / ".env")


def create_logger(log_dir: str | Path | None = None) -> logging.Logger:
    """Crea un logger de consola y archivo compartido por una ejecución ETL."""
    logger = logging.getLogger("airbnb_etl")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    target_dir = Path(log_dir) if log_dir else PROJECT_ROOT / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / f"log_{datetime.now():%Y%m%d_%H%M%S}.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.info("Archivo de log: %s", log_path)
    return logger


def get_mongodb_settings(
    uri: str | None = None, database: str | None = None
) -> tuple[str, str]:
    """Resuelve la URI y el nombre de la base MongoDB desde argumentos o .env."""
    load_settings()
    resolved_uri = uri or os.getenv("AIRBNB_MONGODB_URI", "mongodb://localhost:27017")
    resolved_database = database or os.getenv("AIRBNB_MONGODB_DATABASE")
    if not resolved_database:
        raise ValueError(
            "Configura AIRBNB_MONGODB_DATABASE en .env o proporciona el nombre "
            "de la base de datos."
        )
    return resolved_uri, resolved_database
