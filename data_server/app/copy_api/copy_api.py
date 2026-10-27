from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ...server import ResourceServer


class CopyRequest(BaseModel):
    destination: str


@ResourceServer.app.post("/operations/copy/{static_file:path}", name = "copy")
async def copy(static_file: str, request: CopyRequest):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    source, destination, copied_files, copied_dirs = await file_manager.copy(
        static_file,
        request.destination
    )
    return JSONResponse(
        content = {
            "source": source,
            "destination": destination,
            "copied_files": copied_files,
            "copied_dirs": copied_dirs,
        },
        status_code = 200
    )
