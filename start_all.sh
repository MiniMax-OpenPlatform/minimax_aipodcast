#!/bin/bash

echo "======================================"
echo "  🎙️ MiniMax AI 播客生成器"
echo "======================================"
echo ""

# 检查Python依赖
echo "📦 检查 Python 依赖..."
pip3 install -r requirements.txt

# 启动后端
echo ""
echo "🚀 启动后端服务 (Flask - Port 5001)..."
cd backend
python3 app.py &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 启动前端
echo ""
echo "🚀 启动前端服务 (React - Port 3000)..."
cd ../frontend

# 安装前端依赖（如果需要）
if [ ! -d "node_modules" ]; then
  echo "📦 安装前端依赖..."
  npm install
fi

npm start &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

echo ""
echo "======================================"
echo "✅ 服务启动完成！"
echo ""
echo "后端地址: http://localhost:5001"
echo "前端地址: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "======================================"

# 等待用户中断
wait
