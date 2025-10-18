# 🚀 MiniMax AI 播客生成器 - 部署指南

## 📋 目录
1. [系统要求](#系统要求)
2. [快速开始](#快速开始)
3. [分步部署](#分步部署)
4. [测试验证](#测试验证)
5. [故障排查](#故障排查)

---

## 系统要求

### 必需软件
- **Python**: 3.7+
- **Node.js**: 14+
- **npm**: 6+
- **ffmpeg**: 用于音频处理（pydub 依赖）

### 安装 ffmpeg (如未安装)
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# 从 https://ffmpeg.org/download.html 下载并安装
```

---

## 快速开始

### 一键启动（推荐）

```bash
cd /Users/apple/PycharmProjects/ppn/ai_podcast_v2
./start_all.sh
```

启动后：
- **后端服务**: http://localhost:5001
- **前端应用**: http://localhost:3000

---

## 分步部署

### 步骤 1: 安装后端依赖

```bash
cd /Users/apple/PycharmProjects/ppn/ai_podcast_v2
pip3 install -r requirements.txt
```

### 步骤 2: 启动后端服务

```bash
cd backend
python3 app.py
```

你应该看到类似输出：
```
==================================================
🎙️  MiniMax AI 播客生成服务启动
📁 上传目录: /Users/apple/PycharmProjects/ppn/ai_podcast_v2/backend/uploads
📁 输出目录: /Users/apple/PycharmProjects/ppn/ai_podcast_v2/backend/outputs
==================================================
 * Running on http://0.0.0.0:5001
```

### 步骤 3: 安装前端依赖

打开新终端：

```bash
cd /Users/apple/PycharmProjects/ppn/ai_podcast_v2/frontend
npm install
```

### 步骤 4: 启动前端应用

```bash
npm start
```

前端会自动在浏览器打开 http://localhost:3000

---

## 测试验证

### 1. 健康检查

访问后端健康检查接口：
```bash
curl http://localhost:5001/health
```

应返回：
```json
{"status": "ok", "message": "AI 播客生成服务运行中"}
```

### 2. 快速测试

1. 在浏览器打开 http://localhost:3000
2. 在"输入内容"中输入一段文字，例如："讨论人工智能的发展趋势"
3. 保持默认音色设置（Speaker1: Mini, Speaker2: Max）
4. 点击"开始生成播客"
5. 观察实时日志和进度
6. 等待播客生成完成

### 3. 预期流程

生成过程中你会看到：
- ✅ 内容解析日志
- ✅ 音色准备日志
- ✅ 播放欢迎音频
- ✅ 脚本实时生成
- ✅ 语音合成进度
- ✅ 封面图生成
- ✅ 最终播客下载链接

---

## 故障排查

### 问题 1: 后端端口被占用

**错误**: `Address already in use`

**解决方案**:
```bash
# 查找占用 5001 端口的进程
lsof -i :5001

# 杀死该进程
kill -9 <PID>

# 或修改 backend/app.py 中的端口号
```

### 问题 2: 前端无法连接后端

**错误**: `Failed to fetch` 或 `CORS error`

**解决方案**:
1. 确保后端已启动（http://localhost:5001/health 可访问）
2. 检查 `frontend/package.json` 中的 proxy 配置
3. 清除浏览器缓存并刷新

### 问题 3: ffmpeg 未安装

**错误**: `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**解决方案**:
按照[系统要求](#系统要求)安装 ffmpeg

### 问题 4: Python 依赖安装失败

**错误**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
# 升级 pip
pip3 install --upgrade pip

# 重新安装依赖
pip3 install -r requirements.txt
```

### 问题 5: MiniMax API 调用失败

**错误**: `401 Unauthorized` 或 `Trace-ID: xxx` 显示错误

**解决方案**:
1. 检查 `backend/config.py` 中的 API Key 是否正确
2. 确认 API Key 未过期
3. 查看 Trace ID 到 MiniMax 后台排查

### 问题 6: 音频无法播放

**可能原因**:
- 音频文件路径错误
- 浏览器不支持音频格式

**解决方案**:
1. 检查浏览器控制台是否有错误
2. 确认 `backend/outputs/` 目录存在且有文件
3. 尝试直接访问音频 URL（如 http://localhost:5001/download/audio/xxx.mp3）

---

## 生产环境部署建议

### 1. 使用生产级服务器

**后端**: 使用 Gunicorn 或 uWSGI 代替 Flask 开发服务器

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

**前端**: 构建生产版本

```bash
cd frontend
npm run build

# 使用 serve 或 nginx 部署 build 目录
npm install -g serve
serve -s build -l 3000
```

### 2. 配置环境变量

创建 `.env` 文件存储敏感信息：

```bash
# backend/.env
MINIMAX_TEXT_API_KEY=your_api_key_here
MINIMAX_OTHER_API_KEY=your_api_key_here
FLASK_ENV=production
```

修改 `backend/config.py` 读取环境变量

### 3. 配置 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 4. 配置 HTTPS

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
sudo certbot --nginx -d your-domain.com
```

---

## 性能优化建议

1. **启用 Gzip 压缩** (Nginx)
2. **使用 CDN** 托管静态资源
3. **配置 Redis 缓存** 缓存频繁请求
4. **数据库存储** 保存历史播客记录
5. **负载均衡** 多实例部署

---

## 监控与日志

### 查看后端日志

```bash
cd backend
tail -f logs/app.log  # 如果配置了日志文件
```

### 查看前端日志

打开浏览器开发者工具（F12）→ Console

---

## 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 更新后端依赖
pip3 install -r requirements.txt

# 3. 更新前端依赖
cd frontend
npm install

# 4. 重新构建前端（生产环境）
npm run build

# 5. 重启服务
./start_all.sh
```

---

## 支持

遇到问题？
1. 查看 [PRD.md](./PRD.md) 了解架构设计
2. 查看 [README.md](./README.md) 了解项目概述
3. 提交 Issue 到 GitHub 仓库

---

**版本**: 1.0.0
**最后更新**: 2025-10-18
