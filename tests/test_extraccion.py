import logging
import unittest

from src.extraccion import Extraccion


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query):
        return self.documents


class FakeDatabase:
    def __init__(self, collections):
        self.collections = collections

    def list_collection_names(self):
        return list(self.collections)

    def __getitem__(self, name):
        return self.collections[name]


class FakeClient:
    def __init__(self, database):
        self.database = database
        self.admin = self

    def command(self, name):
        self.command_name = name

    def __getitem__(self, name):
        return self.database


class ExtraccionTests(unittest.TestCase):
    def test_extrae_las_tres_colecciones(self):
        database = FakeDatabase(
            {
                "Listings": FakeCollection([{"id": 1}]),
                "Reviews": FakeCollection([]),
                "Calendar": FakeCollection([{"id": 2}, {"id": 3}]),
            }
        )
        extractor = Extraccion(
            database="airbnb_test",
            logger=logging.getLogger("test"),
            client=FakeClient(database),
        )

        result = extractor.extraer()

        self.assertEqual(list(result), ["Listings", "Reviews", "Calendar"])
        self.assertEqual([len(frame) for frame in result.values()], [1, 0, 2])

    def test_falla_si_falta_una_coleccion(self):
        database = FakeDatabase({"Listings": FakeCollection([])})
        extractor = Extraccion(
            database="airbnb_test",
            logger=logging.getLogger("test"),
            client=FakeClient(database),
        )

        with self.assertRaisesRegex(ValueError, "Faltan colecciones"):
            extractor.extraer()


if __name__ == "__main__":
    unittest.main()
