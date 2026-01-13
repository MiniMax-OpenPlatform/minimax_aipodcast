#!/bin/bash

echo "🎙️ MiniMax AI播客生成器 - 启动脚本"
echo "================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未找到Node.js，请先安装Node.js 16+"
    exit 1
fi

# 检查FFmpeg（音频处理必需）
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ 未找到FFmpeg，这是音频处理的必要依赖"
    echo "   请先安装: brew install ffmpeg"
    exit 1
fi

# 创建必要的目录
mkdir -p backend/uploads
mkdir -p backend/outputs

# 安装后端依赖
echo "📦 正在安装后端依赖..."
pip install -r requirements.txt

# 启动后端服务
echo ""
echo "🚀 正在启动后端服务 (Flask - Port 5001)..."
cd backend
python app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端（使用 React 开发服务器）
echo ""
echo "🌐 正在启动前端服务 (React - Port 3000)..."
cd ../frontend

# 安装前端依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

npm start &
FRONTEND_PID=$!

echo ""
echo "✅ 服务启动成功！"
echo ""
echo "📍 后端地址: http://localhost:5001"
echo "📍 前端地址: http://localhost:3000"
echo ""
echo "⚠️  按 Ctrl+C 停止服务"
echo ""

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait



