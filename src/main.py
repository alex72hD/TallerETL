"""Punto de entrada del proceso ETL completo."""

from __future__ import annotations

import argparse

from src.carga import Carga, ResumenMensualCalendario
from src.etl_common import create_logger
from src.extraccion import Extraccion
from src.transformacion import Transformacion


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL de Airbnb Bogotá")
    parser.add_argument("--mongo-uri", help="URI de MongoDB (o AIRBNB_MONGODB_URI)")
    parser.add_argument(
        "--database", help="Base MongoDB (o AIRBNB_MONGODB_DATABASE)"
    )
    args = parser.parse_args()

    logger = create_logger()
    logger.info("Inicia el proceso ETL de Airbnb Bogotá")
    extractor = Extraccion(
        uri=args.mongo_uri, database=args.database, logger=logger
    )
    transformation = Transformacion(logger=logger)
    loader = Carga(logger=logger)
    loaded = {}
    for name, batches in extractor.iterar_colecciones():
        transformed_batches = (
            transformation.limpiar_dataframe(batch, name) for batch in batches
        )
        if name == "Calendar":
            # Calendar (~7M filas) va completo a SQLite; a Excel se exporta
            # resumido por mes porque el XLSX completo no es práctico.
            resumen = ResumenMensualCalendario()
            loaded["calendar"] = loader.cargar_bloques(
                name, resumen.observar(transformed_batches), exportar_excel=False
            )
            loader.exportar_resumen_calendario(resumen.dataframe())
        else:
            loaded[name.lower()] = loader.cargar_bloques(name, transformed_batches)
    logger.info("Proceso ETL terminado correctamente: %s", loaded)


if __name__ == "__main__":
    main()
