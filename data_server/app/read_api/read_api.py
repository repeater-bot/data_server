from fastapi import HTTPException, Query
from fastapi.responses import Response
from ...server import ResourceServer


@ResourceServer.app.get("/operations/read/{static_file:path}", name = "read_file")
async def read_file(static_file: str, text_encoding: str | None = Query(None)):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    data = await file_manager.read(static_file)
    if text_encoding is not None:
        try:
            encoding_data = data.decode(text_encoding)
        except (UnicodeDecodeError, LookupError):
            raise HTTPException(status_code=400, detail="Invalid text encoding")

        return Response(
            content = encoding_data,
            media_type = "text/plain",
            status_code = 200,
        )
    else:
        return Response(
            content = data,
            media_type = "application/octet-stream",
            status_code = 200,
        )
