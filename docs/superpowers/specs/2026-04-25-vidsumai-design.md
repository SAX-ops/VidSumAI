# VidSumAI 设计文档

## Context

开发一款支持多平台的网络视频下载器 VidSumAI，基于 MoSCoW 法则进行优先级管理。第一版为最小 MVP，仅包含核心下载功能。

## 项目概要

| 维度 | 选择 |
|------|------|
| 前端 | Vue 3 + Nuxt.js 3 |
| 后端 | Python FastAPI |
| 下载引擎 | yt-dlp (subprocess 调用) |
| 传输方式 | 浏览器流式下载 |
| UI 风格 | 深色极简，参考 snapvee.com |
| 范围 | 最小 MVP |

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                    Browser (Vue)                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐ │
│  │ URL输入  │  │ 清晰度  │  │    下载进度条       │ │
│  └─────────┘  └─────────┘  └─────────────────────┘ │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP/WebSocket
┌───────────────────────▼─────────────────────────────┐
│              Python Backend (FastAPI)                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐ │
│  │链接解析  │  │格式提取  │  │    流式传输        │ │
│  └─────────┘  └─────────┘  └─────────────────────┘ │
│                       │                              │
│              ┌────────▼────────┐                     │
│              │    yt-dlp       │                     │
│              │   (subprocess)  │                     │
│              └─────────────────┘                     │
└─────────────────────────────────────────────────────┘
```

## MoSCoW 优先级

### Must Have (MVP)
- [x] 基本下载功能：输入 URL，解析视频信息，下载视频
- [x] 主流网站支持：YouTube、TikTok、Instagram、Bilibili
- [x] 清晰度选择：支持 1080p、720p、480p、仅音频
- [x] 进度显示：WebSocket 实时推送下载进度

### Should Have (第二版)
- [ ] 批量下载：支持多个链接同时提交
- [ ] 任务管理：查看历史下载记录
- [ ] 文件打开：下载完成后可直接打开文件

### Could Have (后续)
- [ ] AI 智能总结：视频内容摘要（暂不实现）

### Won't Have
- 视频格式转换
- 加密网站下载
- 会员/登录态内容

## UI 设计规范

### 品牌识别
- **Logo**：播放键图标 + 渐变色背景
- **主色**：红黄渐变 (#ff6b6b → #feca57)
- **背景**：深色 (#0a0a0f)
- **文字**：白色为主，灰色 (#888) 为辅

### 核心页面
1. **首页**
   - 大标题："8K 无水印 视频一键下载"
   - 卖点标签：极速解析、8K 超高清、无水印、批量下载
   - 下载输入框 + "免费下载" 按钮
   - 清晰度选择芯片
   - 三步引导流程
   - 支持平台展示
   - 社会证明数据
   - FAQ 部分

### 交互流程
```
用户粘贴链接 → 系统自动识别平台 → 显示可用清晰度 → 用户选择 → 点击下载 → 实时进度 → 下载完成
```

## API 设计

### 端点

```
POST /api/parse
  - 输入：{ url: string }
  - 输出：{ title, thumbnail, formats: [{quality, ext, size}] }

GET /api/download/{task_id}
  - 流式返回视频文件
  - Header: Content-Disposition: attachment

WebSocket /ws/progress/{task_id}
  - 实时推送：{ percent, speed, eta, downloaded }
```

### 数据模型

```python
class VideoInfo:
    title: str
    thumbnail: str
    formats: list[Format]

class Format:
    quality: str  # "1080p", "720p", etc.
    ext: str      # "mp4", "webm", etc.
    size: int     # bytes

class DownloadTask:
    id: str
    url: str
    status: str  # "pending", "downloading", "completed", "failed"
    progress: float  # 0-100
```

## 技术实现

### 后端 (Python FastAPI)

```python
# 核心依赖
- fastapi
- uvicorn
- yt-dlp (通过 subprocess 调用)
- websockets

# 关键实现
1. /api/parse: 调用 yt-dlp --dump-json 获取视频信息
2. /api/download: 调用 yt-dlp 下载，流式传输到客户端
3. WebSocket: 通过 yt-dlp progress hook 推送进度
```

### 前端 (Vue + Nuxt.js)

```javascript
// 核心依赖
- nuxt 3
- @nuxtjs/tailwindcss (样式)
- socket.io-client (WebSocket)

// 关键组件
1. DownloadInput: URL 输入 + 解析按钮
2. QualitySelector: 清晰度选择
3. ProgressTracker: 进度条显示
4. PlatformList: 支持平台展示
```

## 验证方案

1. **功能测试**
   - 输入 YouTube 链接，验证解析和下载
   - 输入 TikTok 链接，验证解析和下载
   - 测试清晰度选择功能
   - 验证进度条实时更新

2. **边界测试**
   - 无效链接处理
   - 网络错误处理
   - 大文件下载稳定性

3. **UI 测试**
   - 响应式布局（桌面端）
   - 深色主题一致性
   - 交互流程顺畅

## 文件结构

```
vidsumai/
├── frontend/              # Nuxt.js 前端
│   ├── pages/
│   │   └── index.vue     # 首页
│   ├── components/
│   │   ├── DownloadInput.vue
│   │   ├── QualitySelector.vue
│   │   ├── ProgressTracker.vue
│   │   └── PlatformList.vue
│   └── nuxt.config.ts
├── backend/               # FastAPI 后端
│   ├── main.py           # 入口
│   ├── routers/
│   │   └── download.py   # 下载路由
│   ├── services/
│   │   └── ytdlp.py      # yt-dlp 封装
│   └── requirements.txt
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-25-vidsumai-design.md
```
