# VidSumAI Backend

FastAPI 后端服务，封装 yt-dlp 实现视频解析和下载功能。

## 快速启动

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# 运行测试
uv run pytest
```

## 项目结构

```
backend/
├── main.py              # FastAPI 应用入口，CORS 配置
├── models.py            # Pydantic 数据模型
├── routers/
│   └── download.py      # API 路由：解析、下载、进度、图片代理
├── services/
│   └── ytdlp.py         # yt-dlp 封装：YtdlpService 类
└── downloads/           # 临时下载目录（已 gitignore）
```

## 核心模块

### YtdlpService (`services/ytdlp.py`)

封装 yt-dlp Python API，提供视频解析和下载功能。

```python
from services.ytdlp import YtdlpService

service = YtdlpService()

# 解析视频
video_info = await service.parse_url("https://www.youtube.com/watch?v=xxx")

# 开始下载
task_id = await service.start_download(url, quality, output_dir)
```

**关键特性：**
- 使用 `asyncio.to_thread()` 避免阻塞事件循环
- 进度通过 `progress_hooks` 回调实时更新
- Bilibili 使用 `visitor=true` 模式 + 自定义 headers 绕过 412

### API 路由 (`routers/download.py`)

| 端点 | 说明 |
|------|------|
| `POST /api/parse` | 解析视频链接，返回标题、封面、清晰度列表 |
| `POST /api/start-download` | 创建下载任务，返回 task_id |
| `GET /api/download/{task_id}` | 流式下载文件 |
| `WS /api/ws/progress/{task_id}` | WebSocket 实时进度 |
| `GET /api/proxy/image` | 图片代理（绕过 B站防盗链） |

## Bilibili 支持

Bilibili 使用访客模式解析，无需登录：

```python
ydl_opts = {
    'extractor_args': {'bilibili': ['visitor=true']},
    'http_headers': {
        'User-Agent': '...',
        'Referer': 'https://www.bilibili.com/',
        'Origin': 'https://www.bilibili.com',
    },
}
```

**注意：** Bilibili 格式 ID（30080, 30280 等）不兼容 `best` 选择器，必须使用 `bv*+ba/b`。

## 数据模型

```python
class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    duration: int | None
    platform: str  # "YouTube", "Bilibili", etc.
    url: str
    max_quality: str
    formats: list[FormatInfo]

class FormatInfo(BaseModel):
    quality: str  # "1080p", "720p", etc.
    ext: str
    size: int | None
    url: str
```

## 已知问题

1. **yt-dlp finished hook** - 返回中间文件路径（如 `.f30280.m4a`），已通过 `output_path` 模板解决
2. **Bilibili 高清** - 1080P+ 需要登录 Cookies
3. **内存任务** - `YtdlpService.tasks` 字典在后端重启后丢失
