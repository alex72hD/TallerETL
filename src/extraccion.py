"""Extracción de las colecciones de Airbnb Bogotá desde MongoDB."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from itertools import islice
from typing import Any

import pandas as pd
from pymongo import MongoClient

from src.etl_common import create_logger, get_mongodb_settings


class Extraccion:
    """Lee Listings, Reviews y Calendar de una base de datos MongoDB local."""

    COLECCIONES = ("Listings", "Reviews", "Calendar")

    def __init__(
        self,
        uri: str | None = None,
        database: str | None = None,
        logger: logging.Logger | None = None,
        client: Any | None = None,
    ) -> None:
        self.uri, self.database = get_mongodb_settings(uri, database)
        self.logger = logger or create_logger()
        self._client = client

    def extraer(self) -> dict[str, pd.DataFrame]:
        """Conecta con MongoDB y devuelve un DataFrame por colección requerida."""
        owns_client = self._client is None
        client = self._client or MongoClient(
            self.uri, serverSelectionTimeoutMS=5000
        )
        try:
            client.admin.command("ping")
            db = client[self.database]
            existing = set(db.list_collection_names())
            missing = [name for name in self.COLECCIONES if name not in existing]
            if missing:
                raise ValueError(
                    "Faltan colecciones requeridas en MongoDB: "
                    + ", ".join(missing)
                )

            self.logger.info(
                "Conexión a MongoDB exitosa; base de datos: %s", self.database
            )
            frames: dict[str, pd.DataFrame] = {}
            for name in self.COLECCIONES:
                documents = list(db[name].find({}))
                frames[name] = pd.DataFrame(documents)
                self.logger.info(
                    "Colección %s extraída: %s registros",
                    name,
                    len(frames[name]),
                )
            return frames
        except Exception:
            self.logger.exception("Falló la extracción desde MongoDB.")
            raise
        finally:
            if owns_client:
                client.close()

    def iterar_colecciones(
        self, batch_size: int = 50_000
    ) -> Iterator[tuple[str, Iterator[pd.DataFrame]]]:
        """Entrega las colecciones en bloques para limitar el uso de memoria."""
        if batch_size < 1:
            raise ValueError("batch_size debe ser mayor que cero.")

        owns_client = self._client is None
        client = self._client or MongoClient(
            self.uri, serverSelectionTimeoutMS=5000
        )
        try:
            client.admin.command("ping")
            db = client[self.database]
            existing = set(db.list_collection_names())
            missing = [name for name in self.COLECCIONES if name not in existing]
            if missing:
                raise ValueError(
                    "Faltan colecciones requeridas en MongoDB: "
                    + ", ".join(missing)
                )

            self.logger.info(
                "Conexión a MongoDB exitosa; base de datos: %s", self.database
            )
            for name in self.COLECCIONES:
                cursor = db[name].find({}).batch_size(batch_size)
                yield name, self._iterar_bloques(cursor, name, batch_size)
        except Exception:
            self.logger.exception("Falló la extracción desde MongoDB.")
            raise
        finally:
            if owns_client:
                client.close()

    def _iterar_bloques(
        self, cursor: Any, name: str, batch_size: int
    ) -> Iterator[pd.DataFrame]:
        count = 0
        try:
            while documents := list(islice(cursor, batch_size)):
                count += len(documents)
                yield pd.DataFrame(documents)
            self.logger.info(
                "Colección %s extraída en bloques: %s registros", name, count
            )
        except Exception:
            self.logger.exception("Falló la extracción de la colección %s.", name)
            raise
        finally:
            cursor.close()
