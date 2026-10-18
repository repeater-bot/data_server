from fastapi import FastAPI
from ..lifespan import (
    StartHandler,
    ExitHandler,
    FastAPIStartHandler,
    FastAPIExitHandler,
)

class Lifespan:
    def __init__(self, app: FastAPI) -> None:
        self._app = app
    
    async def enter_lifespan(self):
        await StartHandler.execute(app=self._app)

    async def exit_lifespan(self):
        await ExitHandler.execute(app=self._app)
    
    async def __aenter__(self):
        return await self.enter_lifespan()
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self.exit_lifespan()

class FastAPILifespan:
    def __init__(self, app: FastAPI) -> None:
        self._app = app

    async def enter_lifespan(self):
        await FastAPIStartHandler.execute(app=self._app)

    async def exit_lifespan(self):
        await FastAPIExitHandler.execute(app=self._app)

    async def __aenter__(self):
        return await self.enter_lifespan()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self.exit_lifespan()