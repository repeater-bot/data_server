from .server import ResourceServer
from .app import (
    read_file as _get_file,
    write_file as _write_file,
    delete_file as _delete_file,
    exists as _exists,
    glob_files as _glob,
    rematch as _rematch,
    list_dir as _list_dir,
    get_info as _get_info
)
from .lifespan import run_post_init as _run_post_init

__all__ = ["ResourceServer"]

_run_post_init()
