# VidSumAI

多平台视频下载工具，支持 YouTube、TikTok、Instagram、Bilibili 等 50+ 平台。

## 功能特性

- **多平台支持** - YouTube、TikTok、Instagram、Bilibili、Twitter/X 等
- **高清下载** - 支持 360p ~ 8K 分辨率选择
- **实时进度** - WebSocket 实时推送下载进度、速度、剩余时间
- **封面预览** - 解析后显示视频封面、标题、时长等信息
- **无水印** - 自动获取无水印版本（TikTok、Instagram）

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Nuxt.js 3 + TailwindCSS |
| 后端 | Python FastAPI |
| 下载引擎 | yt-dlp (Python API) |
| 通信 | REST API + WebSocket |

## 快速开始

### 环境要求

- Node.js 18+
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Python 包管理)
- ffmpeg (视频合并)

### 安装

```bash
# 克隆仓库
git clone https://github.com/SAX-ops/VidSumAI.git
cd VidSumAI

# 安装前端依赖
cd frontend
npm install

# 安装后端依赖
cd ../backend
uv sync
```

### 启动

```bash
# 启动后端 (端口 8000)
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# 启动前端 (端口 3000)
cd frontend
npm run dev
```

访问 http://localhost:3000

## 项目结构

```
VidSumAI/
├── frontend/                # Nuxt.js 前端
│   ├── pages/              # 页面组件
│   ├── components/         # 可复用组件
│   ├── types/              # TypeScript 类型定义
│   └── nuxt.config.ts      # Nuxt 配置
├── backend/                 # FastAPI 后端
│   ├── routers/            # API 路由
│   ├── services/           # 业务逻辑
│   ├── models.py           # Pydantic 模型
│   └── main.py             # 应用入口
└── CLAUDE.md               # Claude Code 开发文档
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/parse` | 解析视频链接 |
| POST | `/api/start-download` | 开始下载任务 |
| GET | `/api/download/{task_id}` | 下载文件 |
| WS | `/api/ws/progress/{task_id}` | 实时进度推送 |
| GET | `/api/proxy/image` | 图片代理（B站防盗链） |

## 支持平台

| 平台 | 解析 | 下载 | 备注 |
|------|------|------|------|
| YouTube | ✅ | ✅ | |
| TikTok | ✅ | ✅ | 无水印 |
| Instagram | ✅ | ✅ | 无水印 |
| Bilibili | ✅ | ✅ | 高清需登录 |
| Twitter/X | ✅ | ✅ | |

## 开发说明

### Python 环境

本项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 依赖，所有 Python 命令需通过 `uv run` 执行：

```bash
# ✅ 正确
uv run python main.py
uv run pytest

# ❌ 错误
python main.py
pip install xxx
```

## 免责声明

本项目仅供学习交流使用，请勿用于商业用途。下载内容版权归原作者所有，请遵守相关平台服务条款及当地法律法规。

## License

MIT
