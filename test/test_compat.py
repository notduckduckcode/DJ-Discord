import unittest
import string
import ctypes
import os
import re


class CompatTests(unittest.TestCase):
    """The goal of these tests are to determine if Python is able to perform tasks that are nescessary for DJ Discord"""
    def test_assign(self):
        if _ := 0:
            assert True

    def test_io(self):
        with open(os.devnull, "w") as devnull:
            print("String", 1, None, b"\x00", file=devnull)
        assert True

    def test_dict(self):
        data = {"a": 5}

        assert {"a": "b"} | {"b": "a"} == {"a": "b", "b": "a"}
        assert list(data.keys()) == ["a"]
        assert list(data.values()) == [5]
        assert data.get("a") == 5
        data.pop("a")
        assert not data

    def test_strutils(self):
        assert "tacocat"[::-1] == "tacocat"
        assert ord("a") == 97
        assert ord("а") == 1072
        assert "".join(["d", "j", "d", "i", "s", "c", "o", "r",
                        "d"]) == 'djdiscord'
        assert chr(1072) == "а"
        assert chr(97) == "a"
        assert "{foo[a]} is a good {bar[a]} %s".format(
            foo={"a": "An apple"
                 }, bar={"a": "fruit"}) % ":)" == "An apple is a good fruit :)"
        assert string.capwords("foobar") == "Foobar"

    def test_ctypes(self):
        membuf = ctypes.create_string_buffer(2048)
        assert membuf.raw == b"\x00" * 2048 and ctypes.sizeof(membuf) == 2048

        class Dot(ctypes.Structure):
            _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]

        dot = Dot(10, 20)
        assert dot.x == 10
        assert dot.y == 20

        pointer = ctypes.c_int * 10
        rng = pointer(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

        assert list(rng) == list(range(1, 11))

        assert not ctypes.POINTER(ctypes.c_int)()

    def test_regex(self):
        regex = re.compile(r"([A-Z])\w+")
        assert regex.match("Hello World")
        assert regex.findall("And to all a Merry Christmas!") == [
            'A', 'M', 'C'
        ]
        assert regex.sub("Python", "FooBar is cool") == "Python is cool"
