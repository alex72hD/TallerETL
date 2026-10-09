import logging
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.carga import Carga


class CargaTests(unittest.TestCase):
    def test_carga_y_verifica_sqlite_y_exporta_xlsx(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            loader = Carga(
                sqlite_path=root / "airbnb.sqlite",
                excel_dir=root / "excel",
                logger=logging.getLogger("test"),
            )
            frames = {
                "Listings": pd.DataFrame({"id": [1, 2], "price": [100, 250]}),
                "Reviews": pd.DataFrame({"id": [10], "date": ["2025-01-01"]}),
            }

            loaded = loader.cargar(frames)

            self.assertEqual(loaded, {"listings": 2, "reviews": 1})
            connection = sqlite3.connect(root / "airbnb.sqlite")
            try:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM listings").fetchone()[0],
                    2,
                )
            finally:
                connection.close()
            self.assertEqual(
                pd.read_excel(root / "excel" / "listings.xlsx")["price"].tolist(),
                [100, 250],
            )

    def test_rechaza_dataframe_sin_columnas(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            loader = Carga(
                sqlite_path=Path(temporary_dir) / "airbnb.sqlite",
                excel_dir=Path(temporary_dir) / "excel",
                logger=logging.getLogger("test"),
            )

            with self.assertRaisesRegex(ValueError, "sin columnas"):
                loader.cargar({"Listings": pd.DataFrame()})


if __name__ == "__main__":
    unittest.main()
