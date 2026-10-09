"""Carga de los DataFrames transformados a SQLite y archivos Excel."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Mapping

import pandas as pd
from sqlalchemy import create_engine, text

from src.etl_common import PROJECT_ROOT, create_logger


class Carga:
    """Guarda cada colección como tabla SQLite y como libro XLSX."""

    def __init__(
        self,
        sqlite_path: str | Path | None = None,
        excel_dir: str | Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.sqlite_path = Path(sqlite_path or PROJECT_ROOT / "output" / "airbnb.sqlite")
        self.excel_dir = Path(excel_dir or PROJECT_ROOT / "output" / "excel")
        self.logger = logger or create_logger()

    def cargar(self, dataframes: Mapping[str, pd.DataFrame]) -> dict[str, int]:
        """Escribe y verifica las tablas SQLite y genera un XLSX por colección."""
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.excel_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{self.sqlite_path.resolve().as_posix()}")
        row_counts: dict[str, int] = {}

        try:
            for name, frame in dataframes.items():
                table = self._nombre_tabla(name)
                self.logger.info("Carga de %s iniciada: %s filas", table, len(frame))
                if len(frame.columns) == 0:
                    raise ValueError(
                        f"No se puede cargar {table}: el DataFrame está vacío y sin columnas."
                    )
                frame.to_sql(table, engine, if_exists="replace", index=False, chunksize=1000)
                with engine.connect() as connection:
                    loaded = connection.execute(
                        text(f'SELECT COUNT(*) FROM "{table}"')
                    ).scalar_one()
                if loaded != len(frame):
                    raise RuntimeError(
                        f"Verificación fallida para {table}: "
                        f"{loaded} cargadas, {len(frame)} esperadas."
                    )

                excel_path = self.excel_dir / f"{table}.xlsx"
                frame.to_excel(excel_path, index=False, engine="openpyxl")
                row_counts[table] = loaded
                self.logger.info(
                    "%s cargada y verificada: %s filas; XLSX: %s",
                    table,
                    loaded,
                    excel_path,
                )
        except Exception:
            self.logger.exception("Falló la carga a SQLite o la exportación XLSX.")
            raise
        finally:
            engine.dispose()
        return row_counts

    @staticmethod
    def _nombre_tabla(name: str) -> str:
        table = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip()).lower()
        if not table or not table[0].isalpha():
            table = f"airbnb_{table}"
        return table
