from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from ...server import ResourceServer


@ResourceServer.app.get("/operations/info/{static_file:path}", name = "get_info")
async def get_info(static_file: str, text_encoding: str | None = Query(None)):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    items = await file_manager.get_info(static_file)
    return JSONResponse(
        content = {
            "size": items.st_size,
            "st_mtime": items.st_mtime,
            "st_mtime_ns": items.st_mtime_ns,
            "st_atime": items.st_atime,
            "st_atime_ns": items.st_atime_ns,
            "st_mode": bin(items.st_mode),
        },
        status_code = 200
    )
