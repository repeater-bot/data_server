import re

from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from ...server import ResourceServer


@ResourceServer.app.get("/operations/rematch/{static_file:path}", name = "rematch")
async def rematch(static_file: str, pattern: str = Query(...)):
    if not pattern:
        raise HTTPException(status_code=400, detail="pattern must not be empty")
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid regular expression: {e}"
        ) from e

    return JSONResponse(
        content = {
            "matched": compiled.match(static_file) is not None,
            "path": static_file,
        },
        status_code = 200
    )
