from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ...server import ResourceServer


class MoveRequest(BaseModel):
    destination: str


@ResourceServer.app.post("/operations/move/{static_file:path}", name = "move")
async def move(static_file: str, request: MoveRequest):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager
    source, destination = await file_manager.move(
        static_file,
        request.destination
    )
    return JSONResponse(
        content = {
            "source": source,
            "destination": destination,
        },
        status_code = 200
    )
