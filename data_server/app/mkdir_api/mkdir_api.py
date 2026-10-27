from fastapi import HTTPException
from fastapi.responses import JSONResponse
from ...server import ResourceServer


@ResourceServer.app.post("/operations/mkdir/{static_file:path}", name = "mkdir")
async def mkdir(static_file: str):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    path = await file_manager.mkdir(static_file)
    return JSONResponse(
        content = {
            "path": path,
        },
        status_code = 200
    )
