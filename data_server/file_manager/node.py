import uuid
from typing import Self, Union, Any
from pydantic import BaseModel
from typing_extensions import TypeIs

class FileNode(BaseModel):
    """
    File node
    """
    name: str
    id: uuid.UUID

class DirNode(BaseModel):
    """
    Directory node
    """
    sub_items: dict[str, FileNode | Self]

Nodes = Union[FileNode, DirNode]

HasSubItemsNodes = Union[DirNode]

def is_file(node: Any) -> TypeIs[FileNode]:
    return isinstance(node, FileNode)

def is_dir(node: Any) -> TypeIs[DirNode]:
    return isinstance(node, DirNode)

def is_notes(node: Any) -> TypeIs[Nodes]:
    return isinstance(node, (FileNode, DirNode))

def has_sub_items_notes(node: Any) -> TypeIs[HasSubItemsNodes]:
    return isinstance(node, (DirNode))