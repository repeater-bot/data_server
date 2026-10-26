import os
import io
import uuid
import fnmatch
import orjson
import asyncio
import aiofiles
from pathlib import Path
from .node import (
    FileNode,
    DirNode,
    Nodes,
    has_sub_items_notes,
    is_dir,
    is_file,
)
from .exceptions import DirectoryNotEmptyError
from ..lifespan import StartHandler

class FileManager:
    def __init__(self, root_dir: str | os.PathLike[str]):
        self.root_dir = Path(root_dir)
        self.root_node = DirNode(sub_items = {})
        self._index_lock: asyncio.Lock = asyncio.Lock()
        self._file_lock: asyncio.Lock = asyncio.Lock()
        self._init_coro = StartHandler.add_coroutine(self._load_index())

    async def _find_node(self, path: str) -> FileNode | DirNode | None:
        async with self._index_lock:
            # An empty path (or one made only of separators) addresses the root
            # node.  Dropping empty segments makes "" and "/" equivalent.
            path_notes = [note for note in path.split("/") if note]
            now_node: Nodes = self.root_node
            for note in path_notes:
                if has_sub_items_notes(now_node):
                    if note in now_node.sub_items:
                        now_node = now_node.sub_items[note]
                    else:
                        return None
                else:
                    return None
            return now_node

    async def _create_file_node(self, path: str) -> uuid.UUID:
        async with self._index_lock:
            path_notes = [note for note in path.split("/") if note]
            if not path_notes:
                raise ValueError("path must not be empty")
            now_node: Nodes = self.root_node
            dir_paths = path_notes[:-1]
            file_name = path_notes[-1]
            for note in dir_paths:
                if has_sub_items_notes(now_node):
                    if note in now_node.sub_items:
                        now_node = now_node.sub_items[note]
                    else:
                        node = DirNode(sub_items = {})
                        now_node.sub_items[note] = node
                        now_node = node
                else:
                    raise NotADirectoryError(f"{path} is not a directory")
            
            if has_sub_items_notes(now_node):
                if file_name in now_node.sub_items:
                    raise FileExistsError(f"{path} already exists")
                else:
                    file_id = self._gen_file_id()
                    now_node.sub_items[file_name] = FileNode(
                        name = file_name,
                        id = file_id,
                    )
                    return file_id
            else:
                raise NotADirectoryError(f"{path} is not a directory")

    async def _create_dir_node(self, path: str) -> DirNode:
        """Create ``path`` as a directory and return the created node.

        Missing parents are created.  The caller is responsible for
        persisting the index (``_update_index()``), mirroring
        ``_create_file_node()``.

        :raises ValueError: if ``path`` is empty
        :raises FileExistsError: if ``path`` already exists (file or directory)
        :raises NotADirectoryError: if a parent component is a file
        """
        async with self._index_lock:
            path_notes = [note for note in path.split("/") if note]
            if not path_notes:
                raise ValueError("path must not be empty")

            now_node: DirNode = self.root_node
            for note in path_notes[:-1]:
                child = now_node.sub_items.get(note)
                if child is None:
                    child = DirNode(sub_items = {})
                    now_node.sub_items[note] = child
                elif not is_dir(child):
                    raise NotADirectoryError(f"{path} is not a directory")
                now_node = child

            dir_name = path_notes[-1]
            if dir_name in now_node.sub_items:
                raise FileExistsError(f"{path} already exists")
            node = DirNode(sub_items = {})
            now_node.sub_items[dir_name] = node
            return node

    def _index_path(self) -> Path:
        return self.root_dir / "index.json"

    def _file_path(self, file_id: uuid.UUID) -> Path:
        hex_id = file_id.hex
        return (
            self.root_dir
            / "files"
            / hex_id[:2]
            / hex_id[2:4]
            / f"{hex_id}.bin"
        )

    async def _write_index_locked(self) -> None:
        """Write ``index.json``; the caller must hold ``_index_lock``."""
        async with self._file_lock:
            index_path = self._index_path()
            async with aiofiles.open(index_path, "wb") as index_file:
                await index_file.write(orjson.dumps(self.root_node.model_dump()))

    async def _update_index(self):
        async with self._index_lock:
            await self._write_index_locked()

    async def _load_index(self):
        async with self._index_lock:
            async with self._file_lock:
                index_path = self._index_path()
                self.root_dir.mkdir(parents=True, exist_ok=True)
                if not index_path.exists():
                    # A fresh workspace starts with an empty index instead of
                    # failing the lifespan startup.
                    self.root_node = DirNode(sub_items = {})
                    async with aiofiles.open(index_path, "wb") as index_file:
                        await index_file.write(
                            orjson.dumps(self.root_node.model_dump())
                        )
                    return
                async with aiofiles.open(index_path, "rb") as index_file:
                    index = await index_file.read()
                    self.root_node = DirNode(**orjson.loads(index))

    def _gen_file_id(self) -> uuid.UUID:
        return uuid.uuid4()

    @staticmethod
    async def _copy_range(
        src: aiofiles.threadpool.binary.AsyncBufferedIOBase,
        dst: aiofiles.threadpool.binary.AsyncBufferedIOBase,
        offset: int = 0,
        count: int | None = None,
        chunk_size: int = 1 << 20
    ) -> int:
        """
        Copy data from src to dst, starting at offset, and copying count bytes.

        :param src: The source file.
        :param dst: The destination file.
        :param offset: The offset to start copying from.
        :param count: The number of bytes to copy.
        :param chunk_size: The size of each chunk to copy.
        :return: The number of bytes copied.
        """
        if offset > 0:
            await src.seek(offset)
        elif offset < 0:
            raise ValueError("offset must be positive")

        if count is not None and count < 0:
            raise ValueError("count must be positive")
        
        copied = 0
        while count is None or copied < count:
            buf = await src.read(min(chunk_size, count - copied) if count is not None else chunk_size)
            if not buf:            # 遇到 EOF：区间被文件末尾截断
                break
            copied += await dst.write(buf)
        return copied

    @staticmethod
    async def _stream_size(
        src: aiofiles.threadpool.binary.AsyncBufferedIOBase,
        *,
        restore=True
    ) -> int:
        pos = await src.tell()                 # 不可 seek 的流在这里就抛错
        await src.seek(0, io.SEEK_END)
        size = await src.tell()
        if restore:
            await src.seek(pos, io.SEEK_SET)
        return size

    async def _read_file(
        self,
        id: uuid.UUID,
    ) -> bytes:
        async with self._file_lock:
            path = self._file_path(id)
            if not path.exists():
                raise FileNotFoundError(f"Data file {id} not found")
            async with aiofiles.open(path, "rb") as f:
                return await f.read()

    async def _write_file(
        self,
        id: uuid.UUID,
        data: bytes,
    ) -> int:
        async with self._file_lock:
            path = self._file_path(id)
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, "wb") as f:
                return await f.write(data)

    async def _append_file(
        self,
        id: uuid.UUID,
        data: bytes,
    ) -> None:
        async with self._file_lock:
            path = self._file_path(id)
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, "ab") as f:
                await f.write(data)

    async def _file_info(
        self,
        id: uuid.UUID
    ) -> os.stat_result:
        async with self._file_lock:
            path = self._file_path(id)
            return path.stat()
    
    async def _edit_file(
        self,
        id: uuid.UUID,
        data: bytes,
        start: int,
        end: int,
        copy_chunk_size: int = 1024
    ):
        async with self._file_lock:
            new_file_id = self._gen_file_id()
            scr_file_path = self._file_path(id)
            dst_file_path = self._file_path(new_file_id)
            dst_file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(scr_file_path, "rb") as f:
                async with aiofiles.open(dst_file_path, "wb") as new_f:
                    await self._copy_range(f, new_f, 0, start, chunk_size = copy_chunk_size)
                    await new_f.write(data)
                    await self._copy_range(f, new_f, end, chunk_size = copy_chunk_size)
            scr_file_path.unlink()
            return new_file_id

    async def get_node_type(self, path: str) -> str | None:
        """Return ``"file"``, ``"directory"`` or ``None`` for a virtual path."""
        node = await self._find_node(path)
        if node is None:
            return None
        return "file" if is_file(node) else "directory"

    @staticmethod
    def _compile_glob(pattern: str) -> tuple[str, ...]:
        """Split a glob pattern once; the result is reused for every path."""
        return tuple(part for part in pattern.split("/") if part)

    @staticmethod
    def _match_glob_parts(
        path_parts: list[str],
        pattern_parts: tuple[str, ...],
    ) -> bool:
        """Match already-split path parts against compiled glob parts."""
        if not pattern_parts:
            return False

        def match(
            path_parts: list[str],
            pattern_parts: tuple[str, ...]
        ) -> bool:
            if not pattern_parts:
                return not path_parts
            head = pattern_parts[0]
            rest = pattern_parts[1:]
            if head == "**":
                # ``**`` matches zero or more path segments.
                if match(path_parts, rest):
                    return True
                return bool(path_parts) and match(path_parts[1:], pattern_parts)
            if not path_parts:
                return False
            return (
                fnmatch.fnmatchcase(path_parts[0], head)
                and match(path_parts[1:], rest)
            )

        return match(path_parts, pattern_parts)

    def _match_paths_sync(self, path: str, pattern: str) -> list[str]:
        """Pure index traversal; run this in a worker thread."""
        pattern_parts = self._compile_glob(pattern)
        base_path = [note for note in path.split("/") if note]
        node: Nodes = self.root_node
        for note in base_path:
            if not has_sub_items_notes(node):
                raise NotADirectoryError(f"{path} is not a directory")
            child = node.sub_items.get(note)
            if child is None:
                raise FileNotFoundError(f"Directory {path} not found")
            node = child
        if not is_dir(node):
            raise NotADirectoryError(f"{path} is not a directory")
        base_node: DirNode = node

        results: list[str] = []
        # A bare pattern can only match direct children; avoid walking the
        # whole subtree for the common ``glob("*")`` case.
        if len(pattern_parts) == 1 and pattern_parts[0] != "**":
            name_pattern = pattern_parts[0]
            for name in base_node.sub_items:
                if fnmatch.fnmatchcase(name, name_pattern):
                    results.append("/".join(base_path + [name]))
            return sorted(results)

        def walk(node: DirNode, relative: list[str]) -> None:
            for name, child in node.sub_items.items():
                child_relative = relative + [name]
                if self._match_glob_parts(child_relative, pattern_parts):
                    results.append("/".join(base_path + child_relative))
                if is_dir(child):
                    walk(child, child_relative)

        walk(base_node, [])
        return sorted(results)

    async def _match_paths(self, path: str, pattern: str) -> list[str]:
        if not pattern.strip("/"):
            raise ValueError("pattern must not be empty")
        pattern = pattern.lstrip("/")

        async with self._index_lock:
            # The walk is CPU-bound and may be large; keep it off the event
            # loop while the index lock still guards against mutations.
            return await asyncio.to_thread(
                self._match_paths_sync,
                path,
                pattern
            )

    async def glob(
        self,
        path: str,
        pattern: str,
        recursive: bool = False
    ) -> list[str]:
        """Return virtual paths under ``path`` matching ``pattern``.

        ``*`` / ``?`` / ``[...]`` match within one path segment; ``**``
        matches any number of segments.  With ``recursive=True`` the pattern
        is applied below ``path`` at any depth.  Results are full virtual
        paths relative to the workspace root.
        """
        if not pattern.strip("/"):
            raise ValueError("pattern must not be empty")
        if recursive:
            pattern = f"**/{pattern.lstrip('/')}"
        return await self._match_paths(path, pattern)

    async def read(self, path: str) -> bytes:
        node = await self._find_node(path)
        if node is None:
            raise FileNotFoundError(f"File {path} not found")
        elif not is_file(node):
            raise IsADirectoryError(f"{path} is a directory")
        else:
            return await self._read_file(node.id)

    async def write(self, path: str, data: bytes) -> int:
        node = await self._find_node(path)
        if node is None:
            try:
                file_id = await self._create_file_node(path)
            except FileExistsError:
                # Another request created the same path concurrently.
                node = await self._find_node(path)
                if not is_file(node):
                    raise
                file_id = node.id
            else:
                # Persist the new node before storing its payload.
                await self._update_index()
            return await self._write_file(file_id, data)
        if not is_file(node):
            raise IsADirectoryError(f"{path} is a directory")
        return await self._write_file(node.id, data)

    @staticmethod
    def _collect_deletions(node: Nodes) -> tuple[list[uuid.UUID], int]:
        """Collect file ids and directory count of a subtree."""
        if is_file(node):
            return [node.id], 0

        file_ids: list[uuid.UUID] = []
        dir_count = 1
        stack: list[DirNode] = [node]
        while stack:
            current = stack.pop()
            for child in current.sub_items.values():
                if is_file(child):
                    file_ids.append(child.id)
                else:
                    dir_count += 1
                    stack.append(child)
        return file_ids, dir_count

    async def delete(self, path: str, recursive: bool = False) -> tuple[int, int]:
        """Delete a file or directory; returns ``(deleted_files, deleted_dirs)``.

        A non-empty directory requires ``recursive=True``; the root directory
        can never be deleted.
        """
        async with self._index_lock:
            path_notes = [note for note in path.split("/") if note]
            if not path_notes:
                raise PermissionError("Cannot delete the root directory")

            parent: DirNode = self.root_node
            for note in path_notes[:-1]:
                child = parent.sub_items.get(note)
                if child is None:
                    raise FileNotFoundError(f"File {path} not found")
                if not is_dir(child):
                    raise NotADirectoryError(f"{path} is not a directory")
                parent = child

            name = path_notes[-1]
            node = parent.sub_items.get(name)
            if node is None:
                raise FileNotFoundError(f"File {path} not found")
            if is_dir(node) and node.sub_items and not recursive:
                raise DirectoryNotEmptyError(f"Directory {path} is not empty")

            file_ids, dir_count = await asyncio.to_thread(
                self._collect_deletions,
                node
            )
            del parent.sub_items[name]
            await self._write_index_locked()

        async with self._file_lock:
            for file_id in file_ids:
                self._file_path(file_id).unlink(missing_ok=True)
        return len(file_ids), dir_count

    async def list_dir(
        self,
        path: str,
        recursive: bool = False
    ) -> list[str]:
        """List direct child paths, or all descendants with ``recursive=True``."""
        return await self._match_paths(path, "**" if recursive else "*")

    async def get_info(self, path: str) -> os.stat_result:
        node = await self._find_node(path)
        if node is None:
            raise FileNotFoundError(f"File {path} not found")
        elif not is_file(node):
            raise IsADirectoryError(f"{path} is a directory")
        else:
            return await self._file_info(node.id)