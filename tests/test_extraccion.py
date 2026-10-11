import logging
import unittest

from src.extraccion import Extraccion


class FakeCursor:
    def __init__(self, documents):
        self.documents = iter(documents)
        self.closed = False

    def batch_size(self, size):
        self.size = size
        return self

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.documents)

    def close(self):
        self.closed = True


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query):
        return FakeCursor(self.documents)


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

    def test_iterar_colecciones_entrega_bloques(self):
        database = FakeDatabase(
            {
                "Listings": FakeCollection([{"id": 1}, {"id": 2}, {"id": 3}]),
                "Reviews": FakeCollection([{"id": 4}]),
                "Calendar": FakeCollection([{"id": 5}, {"id": 6}]),
            }
        )
        extractor = Extraccion(
            database="airbnb_test",
            logger=logging.getLogger("test"),
            client=FakeClient(database),
        )

        result = {}
        for name, batches in extractor.iterar_colecciones(batch_size=2):
            result[name] = [len(frame) for frame in batches]

        self.assertEqual(
            result,
            {"Listings": [2, 1], "Reviews": [1], "Calendar": [2]},
        )

    def test_iterar_colecciones_rechaza_bloque_no_positivo(self):
        extractor = Extraccion(
            database="airbnb_test",
            logger=logging.getLogger("test"),
            client=FakeClient(FakeDatabase({})),
        )

        with self.assertRaisesRegex(ValueError, "mayor que cero"):
            next(extractor.iterar_colecciones(batch_size=0))


if __name__ == "__main__":
    unittest.main()
