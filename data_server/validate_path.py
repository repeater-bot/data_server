import os
from pathlib import Path

def validate_path(
        base_path: str | os.PathLike,
        new_path: str | os.PathLike,
        embed:bool = True
    ) -> bool:
    """
    验证路径是否合法

    :param base_path: 基础路径
    :param new_path: 新路径
    :param embed: 是否嵌入基础路径
    :return: 是否合法
    """
    # 转换为Path对象以便于操作
    base = Path(base_path).resolve()
    new = Path(new_path)
    
    if embed:
        # 获取基础路径的绝对路径
        requested_path = (base / new).resolve()
    else:
        requested_path = new.resolve()
    
    # 检查路径是否在base_path的子目录内
    return requested_path.is_relative_to(base)