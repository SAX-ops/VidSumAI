# VidSumAI 项目状态文档

> 最后更新: 2026-04-25

## 项目概述

VidSumAI 是一款支持多平台的网络视频下载器，基于 MoSCoW 法则进行优先级管理。

- **GitHub**: https://github.com/SAX-ops/VidSumAI
- **本地路径**: Z:/DocumentinZ/00MyProject/VidSumAI

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Nuxt.js 3 + TailwindCSS |
| 后端 | Python FastAPI |
| 下载引擎 | yt-dlp (subprocess 调用) |
| 通信 | REST API + WebSocket |
| UI 风格 | 深色极简，参考 snapvee.com |

## 当前状态: MVP 完成 ✅

### 已完成 (Must Have)

- [x] 基本下载功能：输入 URL，解析视频信息，下载视频
- [x] 主流网站支持：YouTube、TikTok、Instagram、Bilibili
- [x] 清晰度选择：支持 1080p、720p、480p、仅音频
- [x] 进度显示：WebSocket 实时推送下载进度
- [x] 深色极简 UI：红黄渐变品牌色，参考 snapvee.com 风格

### 待开发 (Should Have)

- [ ] 批量下载：支持多个链接同时提交
- [ ] 任务管理：查看历史下载记录
- [ ] 文件打开：下载完成后可直接打开文件

### 暂不开发 (Could Have)

- [ ] AI 智能总结：视频内容摘要

### 不做 (Won't Have)

- 视频格式转换
- 加密网站下载
- 会员/登录态内容

## 项目结构

```
VidSumAI/
├── backend/                    # Python FastAPI 后端
│   ├── main.py                # FastAPI 入口
│   ├── models.py              # Pydantic 数据模型
│   ├── requirements.txt       # Python 依赖
│   ├── routers/
│   │   └── download.py        # 下载路由 (parse, download, WebSocket)
│   ├── services/
│   │   └── ytdlp.py           # yt-dlp 封装服务
│   ├── tests/
│   │   ├── test_download.py   # 路由测试
│   │   └── test_ytdlp.py      # 服务测试
│   └── downloads/             # 下载文件存储
├── frontend/                   # Vue/Nuxt.js 前端
│   ├── nuxt.config.ts         # Nuxt 配置
│   ├── tailwind.config.ts     # TailwindCSS 配置
│   ├── app.vue                # 根组件
│   ├── pages/
│   │   └── index.vue          # 首页
│   ├── components/
│   │   ├── DownloadInput.vue  # URL 输入组件
│   │   ├── QualitySelector.vue # 清晰度选择组件
│   │   ├── ProgressTracker.vue # 进度条组件
│   │   └── PlatformList.vue   # 平台展示组件
│   ├── composables/
│   │   └── useWebSocket.ts    # WebSocket Hook
│   └── types/
│       └── index.ts           # TypeScript 类型定义
└── docs/
    └── superpowers/
        ├── specs/             # 设计文档
        └── plans/             # 实现计划
```

## API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /api/parse | 解析视频信息 |
| POST | /api/start-download | 开始下载任务 |
| GET | /api/download/{task_id} | 下载文件 |
| WebSocket | /api/ws/progress/{task_id} | 实时进度 |

## 启动方式

### 后端
```bash
cd backend
# 安装依赖
uv pip install -r requirements.txt

# 启动服务
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd frontend
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 测试状态

所有测试通过 ✅

```bash
# 运行测试
cd backend && uv run pytest tests/ -v

# 测试结果
tests/test_download.py::test_parse_endpoint PASSED
tests/test_download.py::test_parse_endpoint_invalid_url PASSED
tests/test_ytdlp.py::test_parse_url_returns_video_info PASSED
tests/test_ytdlp.py::test_parse_url_invalid_returns_empty_formats PASSED

4 passed in 10.79s
```

## Git 提交历史

```
de5f478 feat: VidSumAI MVP complete - video download with progress tracking
958b4c9 feat: complete home page with all components integrated
9efdf02 feat: add PlatformList component showing supported platforms
0221fe3 feat: add ProgressTracker component with WebSocket support
5c15fca feat: add QualitySelector component for quality picking
b1811b6 feat: add DownloadInput component with URL parsing
ac59ab6 feat: setup Nuxt.js frontend with TailwindCSS and types
a0e7e29 feat: add download router with parse, download, and WebSocket endpoints
019fe57 feat: add yt-dlp service for URL parsing and video download
```

## 下一步工作

### 优先级 1: Should Have 功能
1. **批量下载**
   - 修改 DownloadInput 支持多 URL 输入
   - 后端支持并发下载任务
   - 前端显示多任务进度

2. **任务管理**
   - 添加任务历史记录存储
   - 创建任务列表页面
   - 支持任务状态查看

3. **文件打开**
   - 下载完成后提供打开按钮
   - 调用系统默认程序打开文件

### 优先级 2: UI 优化
- 响应式布局优化
- 移动端适配
- 动画效果增强

### 优先级 3: 部署
- Docker 容器化
- 生产环境配置
- 域名和 HTTPS

## 重要笔记

1. **yt-dlp 行为**: 对无效 URL 不会抛出异常，而是返回空格式列表
2. **端口冲突**: 后端默认端口 8000，如被占用可使用 8001
3. **Windows 兼容**: 使用 uv 管理 Python 依赖，避免 venv 激活问题
4. **UI 设计**: 参考 snapvee.com 的深色主题和红黄渐变品牌色

## 相关文档

- [设计文档](docs/superpowers/specs/2026-04-25-vidsumai-design.md)
- [实现计划](docs/superpowers/plans/2026-04-25-vidsumai-mvp.md)
