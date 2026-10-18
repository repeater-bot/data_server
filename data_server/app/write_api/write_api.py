from fastapi import HTTPException, File, UploadFile
from fastapi.responses import Response
from ...server import ResourceServer


@ResourceServer.app.post("/operations/write/{static_file:path}", name = "write_file")
async def write_file(
    static_file: str,
    file: UploadFile = File(...)
):
    resource_server_instance = ResourceServer.get_instance()
    if not resource_server_instance:
        raise HTTPException(status_code=500, detail="Resource server not initialized")

    file_manager = resource_server_instance.file_manager
    write_count = await file_manager.write(static_file, await file.read())
    return Response(
        content = str(write_count),
        media_type = "text/plain",
        status_code=200,
    )
