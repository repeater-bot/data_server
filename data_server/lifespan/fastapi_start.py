from __future__ import annotations
import asyncio
from fastapi import FastAPI
from typing import Coroutine, Callable, Awaitable
from .base_lifespan import BaseLifespanHandler

class FastAPIStartHandler(BaseLifespanHandler):
    _coroutines: asyncio.Queue[Coroutine[None, None, None]] = asyncio.Queue()
    _functions: asyncio.Queue[Callable[[FastAPI], Awaitable[None]]] = asyncio.Queue()
    _instance: FastAPIStartHandler | None = None