#!/bin/bash

echo "🎙️ MiniMax AI播客生成器 - 启动脚本"
echo "================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

# 创建必要的目录
mkdir -p backend/uploads
mkdir -p backend/outputs

# 安装依赖
echo "📦 正在安装依赖..."
pip3 install -r requirements.txt

# 启动后端服务
echo ""
echo "🚀 正在启动后端服务..."
cd backend
python3 app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端（使用Python的简单HTTP服务器）
echo ""
echo "🌐 正在启动前端服务..."
cd ..
python3 -m http.server 8000 &
FRONTEND_PID=$!

echo ""
echo "✅ 服务启动成功！"
echo ""
echo "📍 请在浏览器中访问: http://localhost:8000/index.html"
echo ""
echo "⚠️  按 Ctrl+C 停止服务"
echo ""

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait



