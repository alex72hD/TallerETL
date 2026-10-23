"""Carga de los DataFrames transformados a SQLite y archivos Excel."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.worksheet._write_only import WriteOnlyWorksheet
from sqlalchemy import create_engine, text

from src.etl_common import PROJECT_ROOT, create_logger


class Carga:
    """Guarda cada colección como tabla SQLite y como libro XLSX."""

    EXCEL_MAX_ROWS = 1_048_576

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
        row_counts = {}
        for name, frame in dataframes.items():
            table = self._nombre_tabla(name)
            row_counts[table] = self.cargar_bloques(name, [frame])
        return row_counts

    def cargar_bloques(
        self,
        name: str,
        dataframes: Iterable[pd.DataFrame],
        exportar_excel: bool = True,
    ) -> int:
        """Carga bloques a SQLite y, si se pide, a un XLSX por hojas.

        Con ``exportar_excel=False`` solo se escribe SQLite; se usa para Calendar
        (7 millones de filas), que se exporta resumido por mes en otro archivo.
        """
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.excel_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{self.sqlite_path.resolve().as_posix()}")
        table = self._nombre_tabla(name)
        workbook: Workbook | None = None
        columns: list[str] | None = None
        loaded = 0
        sheet: WriteOnlyWorksheet | None = None
        sheet_number = 0
        sheet_rows = 0
        excel_path = self.excel_dir / f"{table}.xlsx"

        try:
            self.logger.info("Carga de %s iniciada por bloques", table)
            for frame in dataframes:
                if len(frame.columns) == 0:
                    raise ValueError(
                        f"No se puede cargar {table}: el DataFrame está vacío y sin columnas."
                    )
                if columns is None:
                    columns = list(frame.columns)
                elif list(frame.columns) != columns:
                    raise ValueError(
                        f"El esquema de los bloques de {table} no es consistente."
                    )
                if frame.empty:
                    continue

                frame.to_sql(
                    table,
                    engine,
                    if_exists="replace" if loaded == 0 else "append",
                    index=False,
                    chunksize=1000,
                )
                if not exportar_excel:
                    loaded += len(frame)
                    continue
                if workbook is None:
                    if self.EXCEL_MAX_ROWS < 2:
                        raise ValueError("EXCEL_MAX_ROWS debe permitir encabezado y datos.")
                    workbook = Workbook(write_only=True)
                    sheet, sheet_number, sheet_rows = self._nueva_hoja(
                        workbook, table, sheet_number, columns
                    )
                if sheet is None:
                    raise RuntimeError(f"No se pudo crear una hoja XLSX para {table}.")

                for values in frame.itertuples(index=False, name=None):
                    if sheet_rows >= self.EXCEL_MAX_ROWS:
                        sheet, sheet_number, sheet_rows = self._nueva_hoja(
                            workbook, table, sheet_number, columns
                        )
                    sheet.append([self._valor_excel(value) for value in values])
                    sheet_rows += 1
                loaded += len(frame)

            if loaded == 0:
                raise ValueError(f"No hay filas para cargar en {table}.")
            if columns is None or (exportar_excel and workbook is None):
                raise RuntimeError(f"No se creó la salida XLSX para {table}.")

            with engine.connect() as connection:
                verified_count = connection.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar_one()
            if verified_count != loaded:
                raise RuntimeError(
                    f"Verificación fallida para {table}: "
                    f"{verified_count} cargadas, {loaded} esperadas."
                )
            if workbook is not None:
                workbook.save(excel_path)
                self.logger.info(
                    "%s cargada y verificada: %s filas; XLSX: %s (%s hojas)",
                    table,
                    verified_count,
                    excel_path,
                    sheet_number,
                )
            else:
                self.logger.info(
                    "%s cargada y verificada en SQLite: %s filas (sin XLSX completo)",
                    table,
                    verified_count,
                )
        except Exception:
            self.logger.exception("Falló la carga a SQLite o la exportación XLSX.")
            raise
        finally:
            if workbook is not None:
                workbook.close()
            engine.dispose()
        return loaded

    def exportar_resumen_calendario(self, resumen: pd.DataFrame) -> Path:
        """Exporta el calendario agregado por mes a un XLSX liviano."""
        if resumen.empty:
            raise ValueError("El resumen mensual de Calendar está vacío.")
        self.excel_dir.mkdir(parents=True, exist_ok=True)
        path = self.excel_dir / "calendar.xlsx"
        resumen.to_excel(path, index=False, sheet_name="calendar_mensual")
        leidas = len(pd.read_excel(path))
        if leidas != len(resumen):
            raise RuntimeError(
                f"Verificación fallida del resumen de Calendar: {leidas} != {len(resumen)}."
            )
        self.logger.info(
            "Resumen mensual de Calendar exportado y verificado: %s meses; XLSX: %s",
            len(resumen),
            path,
        )
        return path

    @staticmethod
    def _nueva_hoja(
        workbook: Workbook,
        table: str,
        sheet_number: int,
        columns: list[str],
    ) -> tuple[WriteOnlyWorksheet, int, int]:
        sheet_number += 1
        sheet = workbook.create_sheet(f"{table}_{sheet_number:03d}")
        sheet.append(columns)
        return sheet, sheet_number, 1

    @staticmethod
    def _valor_excel(value: object) -> object:
        if value is None or value is pd.NA:
            return None
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, float) and np.isnan(value):
            return None
        return value

    @staticmethod
    def _nombre_tabla(name: str) -> str:
        table = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip()).lower()
        if not table or not table[0].isalpha():
            table = f"airbnb_{table}"
        return table


class ResumenMensualCalendario:
    """Acumula, bloque a bloque, el calendario agregado por año y mes.

    Calendar tiene una fila por anuncio y día (~7 millones). Resumirlo por mes
    (días disponibles, % de disponibilidad, anuncios distintos) permite
    exportarlo a Excel sin superar sus límites ni la memoria.
    """

    def __init__(self) -> None:
        self._filas: dict[tuple[int, int], list[int]] = {}
        self._anuncios: dict[tuple[int, int], set] = {}

    def observar(self, bloques: Iterable[pd.DataFrame]) -> Iterable[pd.DataFrame]:
        """Itera los bloques sin alterarlos y acumula sus agregados."""
        for frame in bloques:
            self._acumular(frame)
            yield frame

    def _acumular(self, frame: pd.DataFrame) -> None:
        if not {"date_year", "date_month", "available"} <= set(frame.columns):
            return
        valid = frame.dropna(subset=["date_year", "date_month"])
        available = valid["available"].astype(bool)
        grouped = valid.assign(_disp=available).groupby(
            [valid["date_year"].astype(int), valid["date_month"].astype(int)]
        )
        for key, group in grouped:
            counts = self._filas.setdefault(key, [0, 0])
            counts[0] += len(group)
            counts[1] += int(group["_disp"].sum())
            if "listing_id" in group.columns:
                self._anuncios.setdefault(key, set()).update(
                    group["listing_id"].dropna().unique().tolist()
                )

    def dataframe(self) -> pd.DataFrame:
        """Devuelve el resumen ordenado por año y mes."""
        rows = []
        for (year, month), (total, disponibles) in sorted(self._filas.items()):
            rows.append(
                {
                    "anio": year,
                    "mes": month,
                    "total_dias_anuncio": total,
                    "dias_disponibles": disponibles,
                    "dias_no_disponibles": total - disponibles,
                    "pct_disponibilidad": round(100 * disponibles / total, 2),
                    "anuncios_distintos": len(self._anuncios.get((year, month), ())),
                }
            )
        return pd.DataFrame(rows)