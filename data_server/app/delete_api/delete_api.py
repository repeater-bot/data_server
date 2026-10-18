from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from ...server import ResourceServer


@ResourceServer.app.delete("/operations/delete/{static_file:path}", name = "delete_file")
async def delete_file(static_file: str, recursive: bool = Query(False)):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    deleted_files, deleted_dirs = await file_manager.delete(
        static_file,
        recursive = recursive
    )
    return JSONResponse(
        content = {
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs,
        },
        status_code = 200
    )
