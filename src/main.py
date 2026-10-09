"""Punto de entrada del proceso ETL completo."""

from __future__ import annotations

import argparse

from src.carga import Carga
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
    extracted = Extraccion(
        uri=args.mongo_uri, database=args.database, logger=logger
    ).extraer()
    transformed = Transformacion(logger=logger).transformar(extracted)
    loaded = Carga(logger=logger).cargar(transformed)
    logger.info("Proceso ETL terminado correctamente: %s", loaded)


if __name__ == "__main__":
    main()
