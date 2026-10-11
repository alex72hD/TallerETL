"""Limpieza y preparación de los DataFrames extraídos de MongoDB."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from src.etl_common import create_logger


class Transformacion:
    """Aplica limpieza reproducible y registra los cambios del proceso."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or create_logger()

    def transformar(
        self, dataframes: Mapping[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:
        """Transforma cada colección y conserva sus nombres originales."""
        transformed: dict[str, pd.DataFrame] = {}
        for name, frame in dataframes.items():
            try:
                transformed[name] = self.limpiar_dataframe(frame, name)
            except Exception:
                self.logger.exception("Falló la transformación de %s.", name)
                raise
        return transformed

    def limpiar_dataframe(self, dataframe: pd.DataFrame, nombre: str) -> pd.DataFrame:
        """Limpia nulos estructurales/duplicados y estandariza campos conocidos."""
        before = len(dataframe)
        self.logger.info(
            "Inicia transformación de %s (%s filas, %s columnas)",
            nombre,
            before,
            len(dataframe.columns),
        )

        frame = self._aplanar(dataframe.copy())
        normalized_columns = [
            self._normalizar_nombre(col) for col in frame.columns
        ]
        if len(set(normalized_columns)) != len(normalized_columns):
            raise ValueError(
                f"{nombre}: la normalización produce nombres de columna duplicados."
            )
        frame.columns = normalized_columns
        for column in frame.columns:
            frame[column] = frame[column].map(self._normalizar_valor)

        frame = frame.replace(r"^\s*$", np.nan, regex=True)
        empty_rows = int(frame.isna().all(axis=1).sum()) if len(frame.columns) else len(frame)
        if empty_rows:
            frame = frame.dropna(how="all")
            self.logger.info("%s: se eliminan %s filas completamente vacías", nombre, empty_rows)

        empty_columns = [col for col in frame.columns if frame[col].isna().all()]
        if empty_columns:
            frame = frame.drop(columns=empty_columns)
            self.logger.warning(
                "%s: se eliminan columnas totalmente nulas: %s",
                nombre,
                ", ".join(empty_columns),
            )

        duplicate_columns = [column for column in frame.columns if column != "_id"]
        duplicate_count = (
            int(frame.duplicated(subset=duplicate_columns).sum())
            if duplicate_columns
            else 0
        )
        if duplicate_count:
            frame = frame.drop_duplicates(subset=duplicate_columns).reset_index(drop=True)
        self.logger.info("%s: se eliminan %s registros duplicados", nombre, duplicate_count)

        for column in frame.columns:
            if column == "price":
                frame[column] = self._normalizar_precio(frame[column], nombre)
            elif self._es_columna_fecha(column):
                frame[column] = self._normalizar_fecha(frame[column], nombre, column)

        if "amenities" in frame.columns:
            frame["amenities_count"] = frame["amenities"].map(self._contar_elementos)
            self.logger.info(
                "%s: se conserva amenities en formato JSON y se deriva amenities_count",
                nombre,
            )

        if "date" in frame.columns:
            dates = pd.to_datetime(frame["date"], errors="coerce")
            for part in ("year", "month", "day", "quarter"):
                derived = f"date_{part}"
                if derived not in frame.columns:
                    frame[derived] = getattr(dates.dt, part).astype("Int64")
            self.logger.info("%s: se derivan año, mes, día y trimestre de date", nombre)

        if "price" in frame.columns:
            frame["price_category"] = self._categorizar_precios(frame["price"])
            self.logger.info(
                "%s: se deriva price_category mediante terciles de precios válidos",
                nombre,
            )

        self.logger.info(
            "Transformación de %s terminada: %s filas antes, %s después",
            nombre,
            before,
            len(frame),
        )
        return frame.reset_index(drop=True)

    def _aplanar(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Expande objetos anidados y serializa listas para una carga tabular."""
        rows: list[dict[str, Any]] = []

        def add_fields(target: dict[str, Any], prefix: str, value: Any) -> None:
            if isinstance(value, Mapping):
                for key, nested in value.items():
                    nested_key = f"{prefix}_{key}" if prefix else str(key)
                    add_fields(target, nested_key, nested)
            else:
                target[prefix] = value

        for record in dataframe.to_dict(orient="records"):
            flattened: dict[str, Any] = {}
            for key, value in record.items():
                add_fields(flattened, str(key), value)
            rows.append(flattened)
        return pd.DataFrame(rows, index=dataframe.index)

    @staticmethod
    def _normalizar_nombre(value: Any) -> str:
        if str(value).strip().lower() == "_id":
            return "_id"
        name = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value).strip().lower())
        return re.sub(r"_+", "_", name).strip("_")

    @staticmethod
    def _normalizar_valor(value: Any) -> Any:
        if value is None:
            return np.nan
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        if value.__class__.__name__ == "ObjectId":
            return str(value)
        return value

    def _normalizar_precio(self, series: pd.Series, nombre: str) -> pd.Series:
        original = series.notna()
        cleaned = series.astype("string").str.replace(r"[$,]", "", regex=True).str.strip()
        converted = pd.to_numeric(cleaned, errors="coerce")
        invalid = int((original & converted.isna()).sum())
        if invalid:
            self.logger.warning(
                "%s.price: %s valores no numéricos pasan a nulo",
                nombre,
                invalid,
            )
        return converted

    def _normalizar_fecha(
        self, series: pd.Series, nombre: str, column: str
    ) -> pd.Series:
        original = series.notna()
        parsed = pd.to_datetime(series, errors="coerce", format="mixed", utc=True)
        invalid = int((original & parsed.isna()).sum())
        if invalid:
            self.logger.warning(
                "%s.%s: %s fechas inválidas pasan a nulo", nombre, column, invalid
            )
        return parsed.dt.strftime("%Y-%m-%d")

    @staticmethod
    def _es_columna_fecha(column: str) -> bool:
        return column == "date" or column.endswith("_date")

    @staticmethod
    def _contar_elementos(value: Any) -> Any:
        if pd.isna(value):
            return pd.NA
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError:
            return pd.NA
        return len(parsed) if isinstance(parsed, (list, dict)) else pd.NA

    @staticmethod
    def _categorizar_precios(prices: pd.Series) -> pd.Series:
        categories = pd.Series(pd.NA, index=prices.index, dtype="string")
        valid = pd.to_numeric(prices, errors="coerce").dropna()
        if valid.empty:
            return categories
        if valid.nunique() == 1:
            categories.loc[valid.index] = "Único rango"
            return categories

        bins = pd.qcut(valid, q=3, labels=False, duplicates="drop")
        bin_count = int(bins.max()) + 1
        labels = {
            1: ["Único rango"],
            2: ["Bajo", "Alto"],
            3: ["Bajo", "Medio", "Alto"],
        }[bin_count]
        categories.loc[valid.index] = bins.map(lambda index: labels[int(index)]).astype("string")
        return categories
