# 🎙️ MiniMax AI播客生成器

一个基于MiniMax API的AI播客自动生成工具，可以根据话题、网址或PDF文档自动生成高质量的双人播客内容。

## 🌟 项目亮点

- ✅ **前后端分离**: React (localhost:3000) + Flask (localhost:5001)
- ✅ **流式生成**: SSE实时推送，边生成边播放
- ✅ **并行处理**: 内容解析、音色克隆、语音合成并行执行
- ✅ **Airbnb风格UI**: 现代化、简洁、响应式设计
- ✅ **完整追溯**: 所有API调用的Trace ID可追踪
- ✅ **自定义音色**: 支持音频文件上传进行音色克隆

## ✨ 核心功能

### V1版本（当前）
- ✅ **内容输入**: 支持话题、网址链接、PDF文档三种输入方式
- ✅ **音色定制**: 支持使用默认音色或自定义音色（录音/上传音频）
- ✅ **智能生成**: 自动生成自然流畅的双人对话脚本
- ✅ **语音合成**: 流式合成高质量播客音频
- ✅ **封面生成**: 自动生成漫画风格的播客封面图
- ✅ **实时播放**: 边生成边播放，提供流畅体验
- ✅ **可追溯**: 显示所有API调用的Trace ID
- ✅ **下载分享**: 支持下载播客音频、封面和脚本

### V2版本（规划中）
- ⏳ 二次编辑能力（修改脚本、更换音色等）
- ⏳ 与播客主持人自由对话

## 🚀 快速开始

### 环境要求
- **Python**: 3.7+
- **Node.js**: 14+
- **npm**: 6+
- **ffmpeg**: 用于音频处理

### ⚙️ 环境配置

项目使用相对路径配置，可适应开发和生产环境：

**开发环境**：
- 前端通过 `package.json` 的 `proxy` 配置自动代理到后端 (http://localhost:5001)
- 无需额外配置，开箱即用

**生产环境**：
- 通过 Nginx 反向代理 `/api` 到后端服务
- 前端使用相对路径请求，自动适配域名
- 详见 [DEPLOYMENT.md](./DEPLOYMENT.md)

如需自定义 API 地址，可在 `frontend/.env` 中配置：
```bash
# 使用同源（推荐，通过 Nginx 反向代理）
REACT_APP_API_URL=

# 或指定完整 URL（跨域部署时）
# REACT_APP_API_URL=http://your-backend-domain:5001
```

### 一键启动

```bash
cd /Users/apple/PycharmProjects/ppn/ai_podcast_v2
./start_all.sh
```

### 分步启动

**1. 安装后端依赖**
```bash
pip3 install -r requirements.txt
```

**2. 启动后端服务**
```bash
cd backend
python3 app.py
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

### 步骤1：输入内容
选择以下三种方式之一：
- **话题模式**: 直接输入想要讨论的话题
- **网址模式**: 输入文章或网页链接
- **PDF模式**: 上传PDF文档

### 步骤2：选择音色
- **默认音色**: 
  - Max（男声）- 稳重专业
  - Mini（女声）- 活泼亲切
  
- **自定义音色**:
  - 勾选"使用自定义音色"
  - 上传音频文件（建议20秒内）
  - 或直接录音（自动录制20秒）

### 步骤3：生成播客
点击"开始生成播客"按钮，系统将：
1. 解析输入内容
2. 播放欢迎音频
3. 生成播客脚本（流式显示）
4. 合成语音（实时播放）
5. 生成播客封面

### 步骤4：下载分享
生成完成后可以：
- 下载完整播客音频
- 下载播客封面图
- 下载播客脚本文本

## 🎨 设计特色

### Airbnb风格UI
- 清新简洁的界面设计
- 流畅的动画效果
- 友好的交互体验

### 流式处理
- 脚本生成即时显示
- 语音合成边生成边播放
- 无需等待，体验流畅

### 智能优化
- 并行处理多个任务
- 减少总体生成时间
- 提高用户体验

## 🔧 技术架构

### 后端
- **框架**: Flask
- **API集成**: MiniMax (文本生成、TTS、音色克隆、图像生成)
- **内容解析**: BeautifulSoup (网页), PyPDF2 (PDF)

### 前端
- **纯HTML/CSS/JavaScript**: 无需复杂框架
- **响应式设计**: 适配各种屏幕尺寸
- **实时通信**: Server-Sent Events (SSE)

## 📝 API说明

### MiniMax API密钥

项目使用两个API密钥：

1. **文本模型密钥** (M2-preview-1004)
   - 用于生成播客脚本和封面提示词

2. **其他服务密钥** (TTS、音色克隆、图像生成)
   - 用于语音合成、音色克隆、图像生成

### 默认音色

- **Mini (女声)**: `moss_audio_aaa1346a-7ce7-11f0-8e61-2e6e3c7ee85d`
- **Max (男声)**: `moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85`

## ⚠️ 注意事项

1. **音频文件要求**:
   - 自定义音色建议使用20秒以内的清晰音频
   - 支持常见音频格式（WAV、MP3等）

2. **网页解析**:
   - 某些网站可能有反爬虫机制
   - 建议使用公开可访问的网页

3. **PDF解析**:
   - 支持文本型PDF
   - 扫描版PDF可能无法正确解析

4. **Voice ID规范**:
   - 长度范围 [8, 256]
   - 首字符必须为英文字母
   - 允许数字、字母、-、_
   - 末位字符不可为 -、_

## 🐛 故障排除

### 后端服务无法启动
- 检查端口5001是否被占用
- 确认Python依赖已正确安装

### 音色克隆失败
- 确认音频文件格式正确
- 检查音频时长不超过限制
- 查看trace ID排查具体错误

### 网页解析失败
- 确认URL可以正常访问
- 尝试使用其他网页
- 查看后端日志了解详细错误

### 录音功能不可用
- 检查浏览器麦克风权限
- 使用HTTPS协议（或localhost）
- 尝试上传音频文件替代

## 📊 项目结构

```
ai_podcast_v2/
├── backend/                      # Flask 后端
│   ├── app.py                   # Flask 主服务
│   ├── config.py                # 配置管理
│   ├── minimax_client.py        # MiniMax API 客户端
│   ├── content_parser.py        # 内容解析（网页/PDF）
│   ├── voice_manager.py         # 音色管理
│   ├── audio_utils.py           # 音频处理
│   ├── podcast_generator.py    # 播客生成核心
│   ├── uploads/                 # 上传文件目录
│   └── outputs/                 # 生成文件目录
├── frontend/                     # React 前端
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── PodcastGenerator.js   # 核心组件
│   │   │   └── PodcastGenerator.css
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── index.js
│   │   └── index.css
│   └── package.json
├── PRD.md                        # 产品需求文档
├── DEPLOYMENT.md                 # 部署指南
├── requirements.txt              # Python 依赖
├── start_all.sh                 # 一键启动脚本
└── README.md                     # 项目说明
```

## 🔮 未来计划

- [ ] 支持更多语音合成选项（语速、音调、情感等）
- [ ] 添加播客模板（不同风格的对话模式）
- [ ] 支持多人播客（3人或更多）
- [ ] 添加背景音乐混音功能
- [ ] 支持视频播客生成
- [ ] 云端部署版本

## 📄 许可证

本项目仅供学习和研究使用。

## 🙏 致谢

- [MiniMax](https://www.minimaxi.com/) - 提供强大的AI能力
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - 网页解析
- [PyPDF2](https://pypdf2.readthedocs.io/) - PDF解析

---

## 💬 交流社区

欢迎加入微信交流群，与其他开发者一起讨论 AI 播客技术：

<div align="center">
  <img src="./images/wechat_qr.png" alt="微信交流群" width="300"/>
  <p><i>扫码加入微信交流群</i></p>
</div>

---

💡 如有问题或建议，欢迎反馈！



