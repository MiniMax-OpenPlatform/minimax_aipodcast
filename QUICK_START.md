# 🚀 快速启动指南

## ✅ 当前状态

- ✅ 后端已成功启动并测试（Flask on localhost:5001）
- ✅ 所有 Python 模块导入正确
- ✅ 健康检查接口正常工作
- ⏳ 前端待启动（React on localhost:3000）

---

## 📝 已完成测试

### 后端测试结果

```bash
# 健康检查
curl http://localhost:5001/health

# 响应
{
  "status": "ok",
  "message": "AI 播客生成服务运行中"
}
```

### 模块导入测试

```
✓ minimax_client imported
✓ content_parser imported
✓ voice_manager imported
✓ podcast_generator imported
✓ Flask app running
```

---

## 🎯 立即开始使用

### 步骤 1: 启动后端（已运行）

后端已在后台运行于 **http://localhost:5001**

如需重启：
```bash
cd /Users/apple/PycharmProjects/ppn/ai_podcast_v2
source venv/bin/activate
cd backend
python3 app.py
```

### 步骤 2: 启动前端

打开新终端：

```bash
cd /Users/apple/PycharmProjects/ppn/ai_podcast_v2/frontend
npm install
npm start
```

浏览器会自动打开 **http://localhost:3000**

---

## 🧪 快速功能测试

### 测试 1: 最简单的播客生成

1. 在前端页面输入框输入：
   ```
   今天我们来聊聊人工智能的最新发展趋势
   ```

2. 保持默认音色设置：
   - Speaker 1: Mini（女声）
   - Speaker 2: Max（男声）

3. 点击"开始生成播客"

4. 观察实时日志：
   - ✓ 内容解析
   - ✓ 音色准备
   - ✓ 脚本生成
   - ✓ 语音合成
   - ✓ 封面生成

5. 播放并下载生成的播客

### 测试 2: URL 解析测试

输入任意新闻网址，例如：
```
https://www.example.com/article
```

### 测试 3: PDF 解析测试

点击"上传 PDF"，选择一个文本型 PDF 文件

### 测试 4: 自定义音色测试

1. 选择"自定义音色"
2. 上传一段 20 秒左右的音频文件
3. 观察音色克隆过程和 Trace ID

---

## 📊 预期生成时间

根据 PRD 设计，完整播客生成流程：

| 步骤 | 预计时间 |
|------|---------|
| 内容解析 | 5-10 秒 |
| 音色克隆（如需要） | 30-60 秒 |
| 脚本生成 | 30-60 秒 |
| 语音合成 | 60-120 秒 |
| 封面生成 | 10-20 秒 |
| **总计** | **2-5 分钟** |

---

## 🔍 实时监控

### 查看后端日志

后端日志会显示所有 API 调用和 Trace ID：

```bash
# 如果后端在后台运行，查看输出
tail -f backend.log  # 如果有日志文件

# 或者查看终端输出
```

### 查看前端日志

打开浏览器开发者工具（F12）→ Console

### 查看 Trace ID

所有 API 调用的 Trace ID 会在前端页面底部显示，方便调试

---

## ⚠️ 常见问题

### 问题 1: 后端端口被占用

```bash
# 查找占用端口的进程
lsof -i :5001

# 杀死进程
kill -9 <PID>
```

### 问题 2: 前端端口被占用

```bash
# 查找占用端口的进程
lsof -i :3000

# 杀死进程
kill -9 <PID>
```

### 问题 3: CORS 错误

确保：
1. 后端已启动（http://localhost:5001/health 可访问）
2. 前端 package.json 中 proxy 配置正确

### 问题 4: 依赖缺失

```bash
# 重新安装 Python 依赖
cd /Users/apple/PycharmProjects/ppn/ai_podcast_v2
source venv/bin/activate
pip install -r requirements.txt

# 重新安装 Node 依赖
cd frontend
rm -rf node_modules
npm install
```

---

## 📁 项目文件位置

```
当前工作目录: /Users/apple/PycharmProjects/ppn/ai_podcast_v2

关键文件：
├── backend/
│   ├── app.py              # Flask 主服务（运行中）
│   ├── uploads/            # 用户上传文件存放处
│   └── outputs/            # 生成的播客存放处
├── frontend/
│   ├── src/
│   │   └── components/
│   │       └── PodcastGenerator.js  # 核心前端组件
│   └── package.json
├── venv/                   # Python 虚拟环境（已激活）
└── requirements.txt        # Python 依赖列表
```

---

## 🎯 下一步

1. **启动前端**: `cd frontend && npm install && npm start`
2. **打开浏览器**: http://localhost:3000
3. **输入内容**: 尝试生成第一个播客
4. **查看日志**: 观察实时生成过程
5. **下载成品**: 播放并下载生成的播客

---

## 📞 获取帮助

- **PRD 文档**: 查看 `PRD.md` 了解完整架构
- **部署指南**: 查看 `DEPLOYMENT.md` 了解详细部署步骤
- **项目说明**: 查看 `README.md` 了解功能特性

---

**当前版本**: V1.0.0 (MVP)
**最后测试**: 2025-10-18
**状态**: 后端运行正常 ✅ | 前端待启动 ⏳
