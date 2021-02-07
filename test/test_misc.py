import asyncio
import os
import unittest

import aiohttp
import discord
import dotenv
import pytest
import requests
import youtube_dl


@pytest.fixture(scope="class")
def event_loop(request):
    request.cls.loop = asyncio.get_event_loop()
    yield request.cls.loop
    request.cls.loop.close()


dotenv.load_dotenv()

me_keys = ["id", "username", "avatar", "discriminator", "public_flags", "flags",
           "bot", "email", "verified", "locale",
           "mfa_enabled"]


@pytest.mark.usefixtures("event_loop")
class MiscTest(unittest.TestCase):
    def test_discord_api_async(self) -> None:
        async def _test_discord_api_async() -> None:
            async with aiohttp.ClientSession() as client:
                async with client.get("https://discord.com/api/v8/users/@me",
                                      headers={"Authorization": "Bot %s" % os.environ["BOT_TOKEN"]}) as request:
                    payload = await request.json()
                    for key in me_keys:
                        assert key in payload.keys()

        self.loop.run_until_complete(_test_discord_api_async())

    def test_discord_api(self) -> None:
        payload = requests.get("https://discord.com/api/v8/users/@me",
                               headers={"Authorization": "Bot %s" % os.environ["BOT_TOKEN"]}).json()
        for key in me_keys:
            assert key in payload.keys()

    def test_discord_webhook_async(self) -> None:
        async def _test_discord_webhook() -> None:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(os.environ["BOT_WEBHOOK"],
                                                   adapter=discord.AsyncWebhookAdapter(session))
                await webhook.send('Asynchronous webhook unit test complete!', username='DJ Discord Builder')

        self.loop.run_until_complete(_test_discord_webhook())

    def test_discord_webhook(self) -> None:
        webhook = discord.Webhook.partial(int(os.environ["WEBHOOK_ID"]), os.environ["WEBHOOK_TOKEN"],
                                          adapter=discord.RequestsWebhookAdapter())
        webhook.send('Synchronous webhook unit test complete!', username='DJ Discord Builder')

    def test_youtubedl(self) -> None:
        with youtube_dl.YoutubeDL() as ytdl:
            data = ytdl.extract_info(url="https://www.youtube.com/watch?v=ownHh9QIsRk", download=False)
        assert data
