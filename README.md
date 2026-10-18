# Data Server

一个基于 FastAPI 的虚拟文件服务器：把 `base_path` 目录映射成 HTTP API，
用 `index.json` 维护虚拟目录树，文件内容单独存放在 `files/<uuid>.bin` 中。
客户端只能访问索引里登记过的路径，不会直接接触真实文件系统。

## 功能特点

- 📁 **安全文件名** — 文件名仅存在于索引中，不会作为文件名落盘
- 📂 **虚拟目录** — 特殊目录结构不会触发文件系统的特殊行为
- ✍️ **写入即创建** — 目标不存在时自动创建节点和中间目录
- 🗑️ **删除** — 支持删除文件、空目录或递归删除整个目录
- 🔧 **配置管理** — JSON 配置文件，支持多配置选择
- 🚀 **简单易用** — 一条命令启动，自带 OpenAPI 文档

## 环境要求

- Python `>=3.11,<4.0`（代码使用了 `StrEnum`）
- [Poetry](https://python-poetry.org/)（`poetry.toml` 已配置虚拟环境建在项目内 `.venv`）

## 安装

```bash
git clone https://github.com/qeggs-dev/data-server.git
cd data-server
poetry install
```

如果仓库里已经带有 `.venv`，也可以直接使用：

```powershell
.venv\Scripts\python.exe -V
```

## 快速开始

```bash
poetry run python file_server.py
```

Windows 下直接使用虚拟环境：

```powershell
.venv\Scripts\python.exe file_server.py
```

启动后读取当前目录下的 `configs/*.json`：

- 没有 JSON 文件：自动创建 `configs/default.json`（全部默认值）
- 只有一个 JSON 文件：直接使用
- 有多个 JSON 文件：打印列表并提示选择序号

仓库自带的 `configs/config.json` 监听 `http://127.0.0.1:4572`，
虚拟化根目录为 `./static`。

## 配置文件

```json
{
    "host": "127.0.0.1",
    "port": 4572,
    "base_path": "./static",
    "cache_size": 128,
    "cache_ttl": 60,
    "logger": {
        "file_path": "./logs/file-server-log-{time:YYYY-MM-DD_HH-mm-ss.SSS}.log",
        "level": "DEBUG",
        "rotation": "1 days",
        "retention": "7 days",
        "console_format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> - <level>{message}</level>",
        "file_format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} - {message}",
        "compression": "zip"
    }
}
```

| 字段 | 说明 |
| --- | --- |
| `host` | 监听地址，默认 `0.0.0.0` |
| `port` | 监听端口，默认 `8000` |
| `base_path` | 虚拟化根目录，相对当前工作目录；`index.json` 与 `files/` 生成在这里，默认 `./workspace` |
| `cache_size` / `cache_ttl` | **预留字段，当前版本未使用**（暂无缓存实现） |
| `logger.file_path` | 日志文件路径，支持 loguru 的 `{time:...}` 占位符 |
| `logger.level` | `TRACE` / `DEBUG` / `INFO` / `SUCCESS` / `WARNING` / `ERROR` / `CRITICAL` |
| `logger.rotation` / `logger.retention` | 交给 loguru 的轮转与保留策略 |
| `logger.console_format` / `logger.file_format` | 控制台与文件日志格式 |
| `logger.compression` | `gz` / `bz2` / `xz` / `lzma` / `tar` / `tar.gz` / `tar.bz2` / `tar.xz` / `zip`，或 `null` 关闭压缩 |

## 数据布局

```
<base_path>/
├── index.json          # 虚拟目录树（FileNode / DirNode）
└── files/
    └── <uuid>.bin      # 文件内容，按索引中的 UUID 命名
```

`index.json` 不存在时，首次启动会自动创建空索引；通过 HTTP 写入新路径时，
服务会自动创建缺失的节点与中间目录，并更新索引。

## API

所有端点都以 `/operations` 为前缀，URL 中的路径是相对于 `base_path`
的虚拟路径。交互式文档在 `/docs`，OpenAPI 描述在 `/openapi.json`。

### `GET /operations/read/{path}`

读取文件内容。

| 参数 | 位置 | 说明 |
| --- | --- | --- |
| `path` | path | 虚拟文件路径，例如 `images/photo.jpg` |
| `text_encoding` | query | 可选，指定编码后以文本返回，例如 `utf-8` |

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 普通文件 | 200 | 原始字节，`Content-Type: application/octet-stream` |
| 指定 `text_encoding` | 200 | 解码后的文本，`Content-Type: text/plain; charset=utf-8` |
| `text_encoding` 无效或编解码器不存在 | 400 | `{"detail": "Invalid text encoding"}` |
| 路径不存在 | 404 | `{"detail": "File <path> not found"}` |
| 路径是目录 | 400 | `{"detail": "<path> is a directory"}` |

### `GET /operations/list/{path}`

列出目录下的直接子项名称，返回 JSON 数组。根目录使用 `/operations/list/`。

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 目录（含根目录） | 200 | 名称数组，`Content-Type: application/json` |
| 路径不存在 | 404 | `{"detail": "Directory <path> not found"}` |
| 路径是文件 | 400 | `{"detail": "<path> is not a directory"}` |

### `GET /operations/info/{path}`

返回文件元信息，`Content-Type: application/json`：

```json
{
    "size": 12345,
    "st_mtime": 1792297108.85,
    "st_mtime_ns": 1792297108853883900,
    "st_atime": 1792297109.40,
    "st_atime_ns": 1792297109400950700,
    "st_mode": "0b1000000110110110"
}
```

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 普通文件 | 200 | 上面的 JSON |
| 路径不存在 | 404 | `{"detail": "File <path> not found"}` |
| 路径是目录 | 400 | `{"detail": "<path> is a directory"}` |

### `POST /operations/write/{path}`

写入文件。请求体为 `multipart/form-data`，文件字段名必须是 `file`。

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 目标已存在 | 200 | 覆盖写入，返回写入字节数的文本 |
| 目标不存在 | 200 | 自动创建节点与中间目录并写入，返回字节数文本 |
| 父路径是文件 | 400 | `{"detail": "<path> is not a directory"}` |
| 目标是目录 | 400 | `{"detail": "<path> is a directory"}` |
| 缺少 `file` 字段 | 422 | FastAPI 标准校验错误 |

新建节点时会把索引写回 `index.json`；写入的数据在重启服务后仍可读取。

### `DELETE /operations/delete/{path}`

删除文件或目录。

| 参数 | 位置 | 说明 |
| --- | --- | --- |
| `path` | path | 虚拟文件或目录路径 |
| `recursive` | query | 可选，默认 `false`；目录非空时必须设为 `true` |

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 删除文件 | 200 | `{"deleted_files": 1, "deleted_dirs": 0}` |
| 删除空目录 | 200 | `{"deleted_files": 0, "deleted_dirs": 1}` |
| 非空目录且 `recursive=false` | 409 | `{"detail": "Directory <path> is not empty"}` |
| 路径不存在 | 404 | `{"detail": "File <path> not found"}` |
| 删除根目录 | 403 | `{"detail": "Cannot delete the root directory"}` |

删除会同时移除 `index.json` 中的节点和对应的 `files/<uuid>.bin`；
数据文件已经丢失时仍可删除成功。递归删除返回的数量包含目标目录本身。

### 错误响应

业务错误统一使用 `{"detail": "..."}`；未预期异常由中间件兜底为
`500 {"detail": "Internal Server Error"}`。

## 使用示例

```bash
# 读取图片
curl http://127.0.0.1:4572/operations/read/images/photo.jpg -o photo.jpg

# 以文本读取
curl "http://127.0.0.1:4572/operations/read/README.md?text_encoding=utf-8"

# 列根目录
curl http://127.0.0.1:4572/operations/list/

# 查文件信息
curl http://127.0.0.1:4572/operations/info/images/photo.jpg

# 上传（目标不存在会自动创建）
curl -X POST -F "file=@photo.jpg" \
    http://127.0.0.1:4572/operations/write/images/photo.jpg

# 删除文件
curl -X DELETE http://127.0.0.1:4572/operations/delete/images/photo.jpg

# 递归删除目录
curl -X DELETE "http://127.0.0.1:4572/operations/delete/images?recursive=true"
```

## 测试

测试位于 `tests/`，只依赖标准库和项目已有运行时依赖，不需要 pytest：

```powershell
.venv\Scripts\python.exe -m unittest discover -v
```

当前共 165 个用例；接口契约、已修复缺陷和仍存在的非接口问题见
[`tests/KNOWN_ISSUES.md`](tests/KNOWN_ISSUES.md)。

## 项目结构

```
data_server/
├── app/            # HTTP 端点（read / write / delete / list / info）
├── configs/        # pydantic 配置模型
├── file_manager/   # 虚拟索引与文件存储
├── lifespan/       # 启动/退出钩子与 post-init
├── logger_init/    # loguru 与标准库 logging 接线
└── server/         # ResourceServer、异常处理、uvicorn 启动
configs/            # 运行时配置
file_server.py      # 入口脚本
tests/              # 单元测试
```

## 安全说明

- 路径通过索引查找，`..` 之类的路径段只是普通键名，不会逃出 `base_path`。
- 服务本身**不带鉴权**。`Configs` 的内置默认监听 `0.0.0.0`，仓库自带的
  `configs/config.json` 监听 `127.0.0.1`；若要对外提供服务，请在前面加
  反向代理并配置访问控制。

## 许可证

[MIT License](LICENSE)
