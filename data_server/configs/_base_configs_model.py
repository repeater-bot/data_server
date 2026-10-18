from pydantic import BaseModel, Field
from ._logger import LoggerConfig

class Configs(BaseModel):
    # server configs
    host: str = "0.0.0.0"
    port: int = 8000

    base_path: str = "./workspace"
    cache_size: int = 128
    cache_ttl: int | float = 60
    logger: LoggerConfig = Field(default_factory=LoggerConfig)