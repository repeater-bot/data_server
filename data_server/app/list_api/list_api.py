import orjson
from fastapi import HTTPException, Query
from fastapi.responses import Response
from ...server import ResourceServer


@ResourceServer.app.get("/operations/list/{static_file:path}", name = "list_dir")
async def list_dir(
    static_file: str,
    text_encoding: str | None = Query(None),
    recursive: bool = Query(False)
):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    items: list[str] = await file_manager.list_dir(
        static_file,
        recursive = recursive
    )
    return Response(
        content = orjson.dumps(items),
        media_type = "application/json",
        status_code = 200
    )
