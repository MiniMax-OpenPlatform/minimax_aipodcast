#!/bin/bash
# AI Podcast 一键部署脚本
# 在云服务器上执行此脚本

set -e  # 遇到错误立即退出

echo "🚀 开始部署 AI Podcast 应用..."

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 1. 安装依赖
echo "📦 安装系统依赖..."
apt update
apt install -y git python3 python3-pip python3-venv nodejs npm nginx ffmpeg

# 安装 PM2
npm install -g pm2

# 2. 克隆代码
echo "📥 克隆项目代码..."
cd /home/mibo
if [ -d "ai_podcast_v1" ]; then
    echo "项目已存在,更新代码..."
    cd ai_podcast_v1
    git pull
else
    git clone https://github.com/MMMibo/ai_podcast_v1.git
    cd ai_podcast_v1
fi

# 3. 配置后端
echo "🔧 配置后端..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install Flask Flask-Cors requests pydub PyPDF2 beautifulsoup4 lxml

# 确保 app.py 监听所有接口
if ! grep -q "host='0.0.0.0'" app.py; then
    echo "⚠️  警告: app.py 可能未配置监听 0.0.0.0"
fi

# 4. 配置前端
echo "🎨 配置前端..."
cd ../frontend
npm install

# 创建生产环境配置
cat > .env.production << 'EOF'
REACT_APP_API_URL=http://47.103.24.213:5001
EOF

# 构建前端
npm run build

# 5. 启动后端
echo "🚀 启动后端服务..."
cd ../backend
pm2 delete podcast-backend 2>/dev/null || true
pm2 start app.py --interpreter ./venv/bin/python3 --name podcast-backend
pm2 save
pm2 startup | tail -n 1 | bash  # 设置开机自启

# 6. 配置 Nginx
echo "🌐 配置 Nginx..."
cat > /etc/nginx/sites-available/ai-podcast << 'EOF'
server {
    listen 80;
    server_name 47.103.24.213;

    # 前端
    location / {
        root /home/mibo/ai_podcast_v1/frontend/build;
        try_files $uri /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }

    # 静态资源
    location /outputs/ {
        alias /home/mibo/ai_podcast_v1/backend/outputs/;
    }
}
EOF

# 启用配置
ln -sf /etc/nginx/sites-available/ai-podcast /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 7. 配置防火墙
echo "🔥 配置防火墙..."
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5001/tcp

# 8. 设置权限
echo "🔐 设置文件权限..."
chown -R mibo:mibo /home/mibo/ai_podcast_v1
chmod -R 755 /home/mibo/ai_podcast_v1/frontend/build
chmod -R 755 /home/mibo/ai_podcast_v1/backend/outputs

echo "✅ 部署完成!"
echo ""
echo "📌 访问地址: http://47.103.24.213"
echo "📌 后端状态: pm2 status"
echo "📌 查看日志: pm2 logs podcast-backend"
