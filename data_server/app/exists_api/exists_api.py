from fastapi import HTTPException
from fastapi.responses import JSONResponse
from ...server import ResourceServer


@ResourceServer.app.get("/operations/exists/{static_file:path}", name = "exists")
async def exists(static_file: str):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    node_type = await file_manager.get_node_type(static_file)
    return JSONResponse(
        content = {
            "exists": node_type is not None,
            "type": node_type,
        },
        status_code = 200
    )
