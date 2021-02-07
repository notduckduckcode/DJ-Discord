import asyncio
import time
import unittest

import pytest


def _benchmark_function(function, *args, **kwargs):
    start = time.time()
    function(*args, **kwargs)
    return time.time() - start


@pytest.fixture(scope="class")
def event_loop(request):
    request.cls.loop = asyncio.get_event_loop()
    yield request.cls.loop
    request.cls.loop.close()


@pytest.mark.usefixtures("event_loop")
class AsyncTests(unittest.TestCase):
    def test_sleep(self):
        async def _test_sleep(time: int) -> None:
            await asyncio.sleep(time)

        delta = _benchmark_function(self.loop.run_until_complete,
                                    _test_sleep(5))
        assert round(delta) == 5

    def test_task(self):
        async def _sub_task1() -> None:
            return

        async def _sub_task2() -> None:
            return

        async def _test_task() -> None:
            await asyncio.gather(_sub_task1(), _sub_task2())

        self.loop.run_until_complete(_test_task())

    def test_run(self):
        async def _sub_task() -> str:
            return "I am an asyncio sub task!"

        assert asyncio.run(_sub_task()) == "I am an asyncio sub task!"

    def test_shield(self):
        async def _shielded_coro() -> str:
            return "Captain America's shield got nothing on this"

        async def _test_shield() -> None:
            try:
                future = _shielded_coro()
                res = await asyncio.shield(future)
                future.close()
                assert res == "Captain America's shield got nothing on this"
            except asyncio.CancelledError:
                assert False

        self.loop.run_until_complete(_test_shield())

    def test_wait(self):
        async def _sub_task() -> str:
            await asyncio.sleep(2)
            return "Thanks for waiting"

        async def _test_wait() -> None:
            try:
                await asyncio.wait_for(_sub_task(), timeout=1)
                assert False
            except asyncio.TimeoutError:
                assert True

        self.loop.run_until_complete(_test_wait())

    def test_threads(self) -> None:
        def _blocking_sub_task() -> str:
            print("I like to block asynchronous tasks")
            time.sleep(5)
            return "And I just finished execution!"

        async def _test_threads() -> str:
            return await asyncio.gather(asyncio.to_thread(_blocking_sub_task),
                                        asyncio.sleep(5))

        assert self.loop.run_until_complete(_test_threads())
