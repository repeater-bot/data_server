from __future__ import annotations
from ._base_configs_model import Configs

class GlobalConfigManager:
    _instance: GlobalConfigManager | None = None
    _configs: Configs | None = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_configs(cls) -> Configs:
        if cls._instance is None:
            cls._instance = GlobalConfigManager()
        return cls._instance._configs
    
    @classmethod
    def set_configs(cls, configs: Configs) -> None:
        cls._instance = GlobalConfigManager()
        cls._instance._configs = configs