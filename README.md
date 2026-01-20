# 🎙️ MiniMax AI 播客生成器

一个基于 MiniMax API 的 AI 播客自动生成工具，可以根据话题、网址或 PDF 文档自动生成高质量的双人播客内容。

## 🌟 项目亮点

- ✅ **前后端分离**: React (localhost:3000) + Flask (localhost:5001)
- ✅ **并行处理**: 脚本生成、语音合成、封面生成并行执行
- ✅ **渐进式播放**: 音频边生成边可播放
- ✅ **完整追溯**: 所有 API 调用的 Trace ID 可追踪
- ✅ **自定义音色**: 支持音频文件上传进行音色克隆

## ✨ 核心功能

### V1 版本（当前）
- ✅ **内容输入**: 支持话题、网址链接、PDF 文档三种输入方式
- ✅ **音色定制**: 支持使用默认音色或自定义音色
- ✅ **智能生成**: 自动生成自然流畅的双人对话脚本
- ✅ **语音合成**: 流式合成高质量播客音频
- ✅ **封面生成**: 自动生成漫画风格的播客封面图
- ✅ **实时播放**: 边生成边播放，提供流畅体验
- ✅ **下载分享**: 支持下载播客音频、封面和脚本

## 🚀 快速开始

### 环境要求

- **Python**: 3.7+
- **Node.js**: 16+
- **FFmpeg**: 用于音频处理

### 安装 FFmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### 一键启动

```bash
cd minimax_aipodcast
./start.sh
```

### 分步启动

**1. 安装后端依赖**
```bash
pip install -r requirements.txt
```

**2. 启动后端服务**
```bash
cd backend
python app.py
```

**3. 安装前端依赖（新终端）**
```bash
cd frontend
npm install
```

**4. 启动前端应用**
```bash
npm start
```

**5. 访问应用**
- 前端: http://localhost:3000
- 后端: http://localhost:5001

## 📖 使用指南

### 步骤 1：配置 API Key
在页面顶部输入你的 MiniMax API Key

### 步骤 2：输入内容
选择以下三种方式之一：
- **话题模式**: 直接输入想要讨论的话题
- **网址模式**: 输入文章或网页链接
- **PDF 模式**: 上传 PDF 文档

### 步骤 3：选择音色
- **默认音色**: Mini（女声）+ Max（男声）
- **自定义音色**: 上传音频文件进行克隆

### 步骤 4：生成播客
点击 "开始生成播客" 按钮，系统将自动完成生成

### 步骤 5：下载分享
生成完成后可以下载音频、封面和脚本

## 🔧 技术架构

### 后端
- **框架**: Flask
- **API 集成**: MiniMax (文本生成、TTS、音色克隆、图像生成)
- **内容解析**: BeautifulSoup (网页), PyPDF2 (PDF)
- **音频处理**: pydub + FFmpeg

### 前端
- **框架**: React
- **状态管理**: React Hooks
- **实时通信**: Server-Sent Events (SSE)

## 📊 项目结构

```
minimax_aipodcast/
├── backend/                      # Flask 后端
│   ├── app.py                   # Flask 主服务
│   ├── config.py                # 配置管理
│   ├── minimax_client.py        # MiniMax API 客户端
│   ├── content_parser.py        # 内容解析（网页/PDF）
│   ├── voice_manager.py         # 音色管理
│   ├── audio_utils.py           # 音频处理
│   ├── podcast_generator.py     # 播客生成核心
│   ├── assets/                  # BGM 音频文件
│   ├── uploads/                 # 上传文件目录
│   └── outputs/                 # 生成文件目录
├── frontend/                     # React 前端
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── PodcastGenerator.js
│   │   │   └── PodcastGenerator.css
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
├── start.sh                      # 启动脚本
├── requirements.txt              # Python 依赖
├── 快速开始.md                    # 快速入门指南
├── 使用指南.md                    # 详细使用文档
└── README.md                     # 项目说明
```

## ⚠️ 注意事项

1. **音频文件要求**:
   - 自定义音色建议使用 10-30 秒的清晰音频
   - 支持常见音频格式（WAV、MP3 等）

2. **网页解析**:
   - 某些网站可能有反爬虫机制
   - 建议使用公开可访问的网页

3. **PDF 解析**:
   - 支持文本型 PDF
   - 扫描版 PDF 可能无法正确解析

## 🐛 故障排除

### 后端服务无法启动
- 检查端口 5001 是否被占用
- 确认 Python 依赖已正确安装

### FFmpeg 未找到
- 确认已安装 FFmpeg
- 检查 FFmpeg 是否在系统 PATH 中

### 音色克隆失败
- 确认音频文件格式正确
- 检查音频时长不超过限制

## 📄 许可证

本项目仅供学习和研究使用。

## 🙏 致谢

- [MiniMax](https://www.minimaxi.com/) - 提供强大的 AI 能力
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [React](https://reactjs.org/) - 前端框架
- [pydub](https://github.com/jiaaro/pydub) - 音频处理

---

💡 如有问题或建议，欢迎反馈！
