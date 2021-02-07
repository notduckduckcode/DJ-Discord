import traceback
import datetime
import typing
import uuid

import asyncpg
import psutil
import motor.motor_asyncio

from utils.objects import AfterCogInvokeOp
from utils.objects import AfterCommandInvoke
from utils.objects import BeforeCogInvokeOp
from utils.objects import BeforeCommandInvokeOp
from utils.objects import DocumentEvaluation
from utils.objects import ErrorOp


class DJDiscordDatabaseManager:
    def __init__(self, mongo_client: motor.motor_asyncio.AsyncIOMotorClient) -> None:
        self._mongo_client = mongo_client
        self.mongodb = self._mongo_client.djdiscord

    async def log(
            self,
            op: typing.Union[BeforeCogInvokeOp, AfterCogInvokeOp,
                             BeforeCommandInvokeOp, AfterCommandInvoke,
                             ErrorOp],
            info: typing.Optional[dict] = None,
            error: typing.Optional[Exception] = None,
            case_id: typing.Optional[uuid.UUID] = None) -> DocumentEvaluation:
        memory_sample = psutil.virtual_memory()
        payload = {
            "op": int(op),
            "info": info,
            "logged_at": datetime.datetime.now(),
            "system_info": {
                "cpu": psutil.cpu_percent(),
                "ram": memory_sample.used / memory_sample.total,
                "disk": psutil.disk_usage("/"),
            }
        }

        if error := getattr(error, "original", error):
            if isinstance(error, str):
                payload.update({"error": error})

            payload.update({
                "error":
                "".join(
                    traceback.TracebackException.from_exception(
                        error).format()).strip()
            })

        if case_id is not None:
            payload.update({"case_id": case_id.hex})

        return await self.mongodb.logs.insert_one(payload)

    async def get(self, **kwargs) -> list:
        """**`[coroutine]`** get -> Fetch accounts that fit a keyword argument"""

        return await self.mongodb.playlists.find_one(kwargs)
