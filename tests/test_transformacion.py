import logging
import unittest

import pandas as pd

from src.transformacion import Transformacion


class TransformacionTests(unittest.TestCase):
    def setUp(self):
        self.transformacion = Transformacion(logger=logging.getLogger("test"))

    def test_limpia_duplicados_precio_fecha_y_campos_anidados(self):
        data = pd.DataFrame(
            [
                {
                    "_id": "a",
                    "price": "$1,200",
                    "date": "2025-02-14",
                    "amenities": ["Wifi", "Kitchen"],
                    "host": {"name": "Ana"},
                    "empty": None,
                },
                {
                    "_id": "a",
                    "price": "$1,200",
                    "date": "2025-02-14",
                    "amenities": ["Wifi", "Kitchen"],
                    "host": {"name": "Ana"},
                    "empty": None,
                },
                {
                    "_id": "b",
                    "price": "$900",
                    "date": "invalid",
                    "amenities": ["Wifi"],
                    "host": {"name": "Luis"},
                    "empty": None,
                },
            ]
        )

        result = self.transformacion.limpiar_dataframe(data, "Listings")

        self.assertEqual(len(result), 2)
        self.assertEqual(result["price"].tolist(), [1200, 900])
        self.assertEqual(result.loc[0, "host_name"], "Ana")
        self.assertEqual(result.loc[0, "amenities_count"], 2)
        self.assertEqual(result.loc[0, "date_month"], 2)
        self.assertEqual(result.loc[0, "date_quarter"], 1)
        self.assertTrue(pd.isna(result.loc[1, "date"]))
        self.assertNotIn("empty", result.columns)

    def test_precios_vacios_no_fallan_y_quedan_sin_categoria(self):
        data = pd.DataFrame({"price": [None, "no disponible"]})

        result = self.transformacion.limpiar_dataframe(data, "Listings")

        self.assertEqual(result["price_category"].isna().sum(), len(result))

    def test_precios_identicos_se_asignan_a_un_rango(self):
        result = self.transformacion.limpiar_dataframe(
            pd.DataFrame({"id": [1, 2, 3], "price": [10, 10, 10]}), "Listings"
        )

        self.assertEqual(result["price_category"].tolist(), ["Único rango"] * 3)


if __name__ == "__main__":
    unittest.main()
