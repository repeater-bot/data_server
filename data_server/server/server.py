import json
import asyncio
import uvicorn

from pathlib import Path
from loguru import logger
from fastapi import FastAPI
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Callable, Awaitable
from ..logger_init import logger_init
from ..configs import Configs
from ..file_manager import FileManager, DirectoryNotEmptyError
from .._info import __version__
from ._lifespan import Lifespan, FastAPILifespan

class ResourceServer:
    @staticmethod
    def create_app():
        app = FastAPI(
            title = "Workspace Data Server",
            description = "Virtualize a directory and store data.",
            version = __version__,
            lifespan = FastAPILifespan,
        )

        @app.exception_handler(FileNotFoundError)
        async def file_not_found_handler(request: Request, exc: FileNotFoundError):
            return JSONResponse({"detail": str(exc)}, status_code=404)

        @app.exception_handler(IsADirectoryError)
        async def is_a_directory_handler(request: Request, exc: IsADirectoryError):
            return JSONResponse({"detail": str(exc)}, status_code=400)

        @app.exception_handler(NotADirectoryError)
        async def not_a_directory_handler(request: Request, exc: NotADirectoryError):
            return JSONResponse({"detail": str(exc)}, status_code=400)

        @app.exception_handler(DirectoryNotEmptyError)
        async def directory_not_empty_handler(request: Request, exc: DirectoryNotEmptyError):
            return JSONResponse({"detail": str(exc)}, status_code=409)

        @app.exception_handler(FileExistsError)
        async def file_exists_handler(request: Request, exc: FileExistsError):
            return JSONResponse({"detail": str(exc)}, status_code=409)

        @app.exception_handler(PermissionError)
        async def permission_error_handler(request: Request, exc: PermissionError):
            return JSONResponse({"detail": str(exc)}, status_code=403)

        @app.middleware("http")
        async def http_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
            try:
                response = await call_next(request)
            except Exception as e:
                logger.exception(e)
                response = JSONResponse(
                    {
                        "detail": "Internal Server Error"
                    },
                    status_code = 500
                )
            return response
        return app
    
    app = create_app()
    _instance: "ResourceServer | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __init__(self):
        self._configs = self.load_configs()
        self.file_manager = FileManager(self._configs.base_path)
        self._uvicorn_config = uvicorn.Config(
            app = self.app,
            host = self._configs.host,
            port = self._configs.port,
            log_config = None
        )
    
    @staticmethod
    def load_configs():
        config_dir = Path("./configs")
        config_dir.mkdir(parents=True, exist_ok=True)
        config_files: list[Path] = sorted(config_dir.glob("*.json"))

        if len(config_files) == 0:
            logger.warning("No config files found in configs directory, creating default config file...")
            config_file = config_dir / "default.json"
            configs = Configs()
            with open(config_file, "w", encoding="utf-8") as file:
                json.dump(configs.model_dump(), file, indent=4, ensure_ascii=False)
            return configs
        elif len(config_files) == 1:
            config_file: Path = config_files[0]
        else:
            for index, file in enumerate(config_files):
                print(f"{index}: {file.name}")
            while True:
                try:
                    choice = int(input("Choose a config file: "))
                    config_file = config_files[choice]
                    break
                except (ValueError, IndexError):
                    logger.error("Invalid choice")
        if not config_file.exists():
            raise FileNotFoundError(f"Config file {config_file} does not exist")
        with open(config_file, "r", encoding="utf-8") as file:
            return Configs(**json.load(file))

    async def _run(self):
        logger_init(self._configs.logger)
        async with Lifespan(self.app) as lifespan:
            try:
                server = uvicorn.Server(
                    self._uvicorn_config
                )
                await server.serve()
            except Exception as e:
                logger.exception(e)

    def run(self):
        runner = asyncio.Runner(
            loop_factory = self._uvicorn_config.get_loop_factory()
        )
        try:
            runner.run(self._run())
        except KeyboardInterrupt:
            logger.info("Program terminated by user.")
