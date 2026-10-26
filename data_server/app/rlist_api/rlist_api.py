import orjson
from fastapi import HTTPException
from fastapi.responses import Response
from ...server import ResourceServer


@ResourceServer.app.get("/operations/rlist/{static_file:path}", name = "rlist")
async def rlist(static_file: str):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    paths = await file_manager.rlist(static_file)
    return Response(
        content = orjson.dumps(paths),
        media_type = "application/json",
        status_code = 200
    )
