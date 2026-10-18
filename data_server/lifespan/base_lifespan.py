from __future__ import annotations
import asyncio
import inspect
from fastapi import FastAPI
from typing import Any, Coroutine, Callable, Awaitable

class BaseLifespanHandler:
    _coroutines: asyncio.Queue[Coroutine[None, None, None]] = asyncio.Queue()
    _functions: asyncio.Queue[Callable[[FastAPI], Awaitable[None]]] = asyncio.Queue()
    _instance: BaseLifespanHandler | None = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def _execute_functions(cls, app: FastAPI):
        while not cls._functions.empty():
            func = await cls._functions.get()
            await func(app)

    @classmethod
    async def _execute_coroutines(cls):
        while not cls._coroutines.empty():
            func: Coroutine[None, None, None] = await cls._coroutines.get()
            await func
    
    @classmethod
    async def execute(cls, app: FastAPI):
        await asyncio.gather(
            cls._execute_functions(app),
            cls._execute_coroutines()
        )
    
    @classmethod
    def add_coroutine(cls, coro: Coroutine[None, None, None]) -> Coroutine[None, None, None]:
        if not inspect.iscoroutine(coro):
            raise TypeError("must be a coroutine")
        cls._coroutines.put_nowait(item=coro)
        return coro

    @classmethod
    def add_function(cls, func: Callable[[FastAPI], Awaitable[None]]) -> Callable[[FastAPI], Awaitable[None]]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("must be a coroutine function")
        cls._functions.put_nowait(item=func)
        return func