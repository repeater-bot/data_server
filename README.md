# Data Server

一个基于 FastAPI 的虚拟文件服务器：把 `base_path` 目录映射成 HTTP API，
用 `index.json` 维护虚拟目录树，文件内容按 UUID 分片存放在
`files/<xx>/<yy>/<uuid>.bin` 中。
客户端只能访问索引里登记过的路径，不会直接接触真实文件系统。

## 功能特点

- 📁 **安全文件名** — 文件名仅存在于索引中，不会作为文件名落盘
- 📂 **虚拟目录** — 特殊目录结构不会触发文件系统的特殊行为
- ✍️ **写入即创建** — 目标不存在时自动创建节点和中间目录
- 🗑️ **删除** — 支持删除文件、空目录或递归删除整个目录
- 🔎 **存在检查** — 不读取内容即可判断路径是文件、目录还是不存在
- 🔍 **路径扫描** — `glob`（`recursive=true` 递归）按模式返回完整虚拟路径
- 🌲 **目录列表** — `list` 用 `recursive` 切换直接子项 / 递归后代路径
- 🧩 **正则匹配** — `rematch` 用 Python `re` 判断单个虚拟路径是否命中
- 🔧 **配置管理** — JSON 配置文件，支持多配置选择
- 🚀 **简单易用** — 一条命令启动，自带 OpenAPI 文档

## 环境要求

- Python `>=3.11,<4.0`
- [Poetry](https://python-poetry.org/)

## 安装

```bash
git clone https://github.com/qeggs-dev/data-server.git
cd data-server
poetry install
```

## 快速开始

```bash
poetry run python file_server.py
```

直接使用虚拟环境：

```powershell
./.venv/Scripts/python.exe file_server.py
```

or

```bash
.venv/bin/python3 file_server.py
```

启动后读取当前目录下的 `configs/*.json`：

- 没有 JSON 文件：自动创建 `configs/default.json`（全部默认值）
- 只有一个 JSON 文件：直接使用
- 有多个 JSON 文件：打印列表并提示选择序号

## 配置文件

```json
{
    "host": "0.0.0.0",
    "port": 8000,
    "base_path": "./workspace",
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

以上是内置默认值。`configs/` 是本地运行时目录（已在 `.gitignore` 中忽略），
首次启动会自动生成 `default.json`，实际部署按需覆盖。

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
├── index.json              # 虚拟目录树（FileNode / DirNode）
└── files/
    └── <xx>/
        └── <yy>/
            └── <uuid>.bin  # 文件内容，按索引 UUID 分片存放
```

`<xx>` / `<yy>` 是 UUID 十六进制的前 2 位和第 3-4 位，用 256×256 个子目录
分散文件，避免单个目录堆积过多文件。数据文件始终按分片路径存放。

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

列出目录下的子项路径，返回完整虚拟路径数组。根目录使用 `/operations/list/`。

| 参数 | 位置 | 说明 |
| --- | --- | --- |
| `path` | path | 虚拟目录路径；根目录用 `/operations/list/` |
| `recursive` | query | 可选，默认 `false`；`true` 时递归列出所有后代路径 |

```bash
curl http://127.0.0.1:8000/operations/list/docs
# ["docs/a.md", "docs/sub"]

curl "http://127.0.0.1:8000/operations/list/docs?recursive=true"
# ["docs/a.md", "docs/sub", "docs/sub/c.md"]
```

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 目录（含根目录） | 200 | 完整虚拟路径数组，`Content-Type: application/json` |
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

### `GET /operations/exists/{path}`

检查虚拟路径是否存在，不读取文件内容。路径不存在不是错误，也返回 200。

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 文件 | 200 | `{"exists": true, "type": "file"}` |
| 目录（含根路径 `/operations/exists/`） | 200 | `{"exists": true, "type": "directory"}` |
| 不存在 | 200 | `{"exists": false, "type": null}` |

### `GET /operations/glob/{path}`

在 `path` 目录下按模式扫描，返回**相对工作区根目录的完整虚拟路径**。

| 参数 | 位置 | 说明 |
| --- | --- | --- |
| `path` | path | 扫描的起始目录；根目录用 `/operations/glob/` |
| `pattern` | query | 必填，glob 模式，例如 `*.md`、`sub/*.md`、`**/*.md` |
| `recursive` | query | 可选，默认 `false`；设为 `true` 时等价于 `**/<pattern>`，在任意深度匹配 |

- `*` / `?` / `[...]` 只匹配单个路径段；`**` 可以跨任意层目录。
- 裸模式（不含 `/` 和 `**`）只匹配起始目录的直接子项。
- `recursive=true` 时自动在 `path` 下递归匹配。
- 结果是 JSON 数组，元素是完整虚拟路径，包含匹配到的目录。

```bash
curl "http://127.0.0.1:8000/operations/glob/docs?pattern=*.md"
# ["docs/a.md"]

curl "http://127.0.0.1:8000/operations/glob/docs?pattern=*.md&recursive=true"
# ["docs/a.md", "docs/sub/c.md", "docs/sub/deep/d.md"]
```

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 正常扫描 | 200 | 路径数组，`Content-Type: application/json` |
| 起始路径不存在 | 404 | `{"detail": "Directory <path> not found"}` |
| 起始路径是文件 | 400 | `{"detail": "<path> is not a directory"}` |
| `pattern` 为空或全是 `/` | 400 | `{"detail": "pattern must not be empty"}` |
| 缺少 `pattern` | 422 | FastAPI 标准校验错误 |

> `glob` / `list` 的索引遍历，以及递归删除时的子树收集，
> 都在线程池中执行（`asyncio.to_thread`），不会长时间占用事件循环。

### `GET /operations/rematch/{path}`

用正则表达式匹配单条虚拟路径。

| 参数 | 位置 | 说明 |
| --- | --- | --- |
| `path` | path | 要匹配的虚拟路径 |
| `pattern` | query | 必填，Python `re` 语法；使用 `re.match`，从路径开头匹配 |

只做字符串匹配，**不检查路径是否真实存在**。

```bash
curl -G --data-urlencode "pattern=.*\\.md$" \
    http://127.0.0.1:8000/operations/rematch/docs/a.md
# {"matched": true, "path": "docs/a.md"}
```

| 情况 | 状态码 | 响应 |
| --- | --- | --- |
| 命中 / 不命中 | 200 | `{"matched": true/false, "path": "<path>"}` |
| `pattern` 为空 | 400 | `{"detail": "pattern must not be empty"}` |
| 无效正则 | 400 | `{"detail": "Invalid regular expression: ..."}` |
| 缺少 `pattern` | 422 | FastAPI 标准校验错误 |

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

删除会同时移除 `index.json` 中的节点和对应的数据文件
（`files/<xx>/<yy>/<uuid>.bin`）；数据文件已经丢失时仍可删除成功。
递归删除返回的数量包含目标目录本身。

### 错误响应

业务错误统一使用 `{"detail": "..."}`；未预期异常由中间件兜底为
`500 {"detail": "Internal Server Error"}`。

## 使用示例

```bash
# 读取图片
curl http://127.0.0.1:8000/operations/read/images/photo.jpg -o photo.jpg

# 以文本读取
curl "http://127.0.0.1:8000/operations/read/README.md?text_encoding=utf-8"

# 列根目录
curl http://127.0.0.1:8000/operations/list/

# 查文件信息
curl http://127.0.0.1:8000/operations/info/images/photo.jpg

# 检查是否存在
curl http://127.0.0.1:8000/operations/exists/images/photo.jpg

# 当前层扫描
curl "http://127.0.0.1:8000/operations/glob/images?pattern=*.jpg"

# 递归扫描
curl "http://127.0.0.1:8000/operations/glob/?pattern=*.md&recursive=true"

# 递归列出全部后代
curl "http://127.0.0.1:8000/operations/list/docs?recursive=true"

# 正则匹配单条路径
curl -G --data-urlencode "pattern=.*\\.md$" \
    http://127.0.0.1:8000/operations/rematch/docs/a.md

# 上传（目标不存在会自动创建）
curl -X POST -F "file=@photo.jpg" \
    http://127.0.0.1:8000/operations/write/images/photo.jpg

# 删除文件
curl -X DELETE http://127.0.0.1:8000/operations/delete/images/photo.jpg

# 递归删除目录
curl -X DELETE "http://127.0.0.1:8000/operations/delete/images?recursive=true"
```

## 项目结构

```
data_server/
├── app/            # HTTP 端点
├── configs/        # pydantic 配置模型
├── file_manager/   # 虚拟索引与文件存储
├── lifespan/       # 启动/退出钩子与 post-init
├── logger_init/    # loguru 与标准库 logging 接线
└── server/         # ResourceServer、异常处理、uvicorn 启动
configs/            # 运行时配置（首次启动生成，不入库）
file_server.py      # 入口脚本
```

## 安全说明

- 路径通过索引查找，`..` 之类的路径段只是普通键名，不会逃出 `base_path`。
- 服务本身**不带鉴权**。`Configs` 的内置默认监听 `0.0.0.0`；实际部署建议
  改为只监听 `127.0.0.1`，或在前面加反向代理并配置访问控制。

## 许可证

[MIT License](LICENSE)
