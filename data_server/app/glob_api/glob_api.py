import orjson
from fastapi import HTTPException, Query
from fastapi.responses import Response
from ...server import ResourceServer


def _get_file_manager():
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    return resource_server_instance.file_manager


@ResourceServer.app.get("/operations/glob/{static_file:path}", name = "glob")
async def glob_files(static_file: str, pattern: str = Query(...)):
    if not pattern.strip("/"):
        raise HTTPException(status_code=400, detail="pattern must not be empty")
    file_manager = _get_file_manager()
    paths = await file_manager.glob(static_file, pattern)
    return Response(
        content = orjson.dumps(paths),
        media_type = "application/json",
        status_code = 200
    )


@ResourceServer.app.get("/operations/rglob/{static_file:path}", name = "rglob")
async def rglob_files(static_file: str, pattern: str = Query(...)):
    if not pattern.strip("/"):
        raise HTTPException(status_code=400, detail="pattern must not be empty")
    file_manager = _get_file_manager()
    paths = await file_manager.rglob(static_file, pattern)
    return Response(
        content = orjson.dumps(paths),
        media_type = "application/json",
        status_code = 200
    )
