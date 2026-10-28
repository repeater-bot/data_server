from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from ...server import ResourceServer


def _range_not_satisfiable(size: int) -> JSONResponse:
    return JSONResponse(
        content = {
            "detail": "Range Not Satisfiable",
        },
        status_code = 416,
        headers = {
            "Content-Range": f"bytes */{size}",
            "Accept-Ranges": "bytes",
        }
    )


def _parse_range(value: str, size: int) -> tuple[int, int] | None:
    """Parse a single ``Range: bytes=...`` spec into inclusive bounds."""
    if not value.lower().startswith("bytes="):
        return None

    spec = value[6:].strip()
    if not spec or "," in spec or "-" not in spec:
        raise ValueError("unsupported range")

    start_text, end_text = spec.split("-", 1)
    if not start_text:
        suffix = int(end_text)
        if suffix <= 0 or size == 0:
            raise ValueError("invalid suffix range")
        start = max(size - suffix, 0)
        end = size - 1
    else:
        start = int(start_text)
        end = int(end_text) if end_text else size - 1
        if start < 0 or end < start or start >= size:
            raise ValueError("range out of bounds")
        end = min(end, size - 1)

    return start, end


@ResourceServer.app.get("/operations/read/{static_file:path}", name = "read_file")
async def read_file(
    static_file: str,
    request: Request,
    text_encoding: str | None = Query(None)
):
    resource_server_instance = ResourceServer.get_instance()
    if resource_server_instance is None:
        raise HTTPException(status_code=500, detail="Resource server not initialized")
    file_manager = resource_server_instance.file_manager

    range_header = request.headers.get("range")
    if range_header is not None:
        info = await file_manager.get_info(static_file)
        size = info.st_size
        try:
            bounds = _parse_range(range_header, size)
        except (TypeError, ValueError):
            return _range_not_satisfiable(size)
        if bounds is None:
            return _range_not_satisfiable(size)
        start, end = bounds
        data = await file_manager.read(
            static_file,
            start = start,
            length = end - start + 1
        )
        status_code = 206
        headers = {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(len(data)),
        }
    else:
        data = await file_manager.read(static_file)
        status_code = 200
        headers = {
            "Content-Length": str(len(data)),
        }

    headers["Accept-Ranges"] = "bytes"

    if text_encoding is not None:
        try:
            text = data.decode(text_encoding)
        except (UnicodeDecodeError, LookupError):
            raise HTTPException(status_code=400, detail="Invalid text encoding")

        return Response(
            content = text,
            media_type = "text/plain",
            status_code = status_code,
            headers = headers,
        )
    else:
        return Response(
            content = data,
            media_type = "application/octet-stream",
            status_code = status_code,
            headers = headers,
        )
