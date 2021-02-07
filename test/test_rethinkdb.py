import rethinkdb
import random
import unittest
import dotenv
import os

dotenv.load_dotenv()

connection = rethinkdb.r.connect(db="test",
                                 host=os.environ["RETHINKDB_HOST"],
                                 port=os.environ["RETHINKDB_PORT"])

names = ["John Doe", "Jane Doe", "John Smith", "Lindsay Graham"]

ages = [13, 15, 34, 20, 64, 23]


class RethinkDBUnitTests(unittest.TestCase):
    def test_insertion(self):
        if "_data" not in rethinkdb.r.table_list().run(connection):
            rethinkdb.r.db("test").table_create("_data").run(connection)
        for _ in range(100):
            with open("/dev/random", "rb") as _random:
                rethinkdb.r.table("_data").insert({
                    "name":
                    random.choice(names),
                    "age":
                    random.choice(ages),
                    "random_data":
                    _random.read(64),
                    "accen_color":
                    0xFFFFFF
                }).run(connection)

        assert rethinkdb.r.table("_data").count() == 100

        rethinkdb.r.table("_data").delete().run(connection)

        rethinkdb.r.table_drop("_data")

    def test_stress(self):
        for _ in range(10):
            if "_data" not in rethinkdb.r.table_list().run(connection):
                rethinkdb.r.db("test").table_create("_data").run(connection)
            for _ in range(100):
                with open("/dev/random", "rb") as _random:
                    rethinkdb.r.table("_data").insert({
                        "name":
                        random.choice(names),
                        "age":
                        random.choice(ages),
                        "random_data":
                        _random.read(64),
                        "accen_color":
                        0xFFFFFF
                    }).run(connection)

            assert rethinkdb.r.table("_data").count() == 100

            rethinkdb.r.table("_data").delete().run(connection)

            rethinkdb.r.table_drop("_data")
