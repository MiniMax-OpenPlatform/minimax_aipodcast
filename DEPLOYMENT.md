# 🚀 云服务器部署指南

## 服务器信息
- **IP**: 47.103.24.213
- **用户**: mibo
- **系统**: Linux (推测 Ubuntu/CentOS)

## 部署步骤

### 1️⃣ 连接服务器

```bash
ssh mibo@47.103.24.213
```

### 2️⃣ 安装必要环境

```bash
# 更新包管理器
sudo apt update  # Ubuntu/Debian
# 或
sudo yum update  # CentOS/RHEL

# 安装 Git
sudo apt install git -y

# 安装 Python 3 和 pip
sudo apt install python3 python3-pip python3-venv -y

# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# 安装 Nginx
sudo apt install nginx -y

# 安装 PM2
sudo npm install -g pm2
```

### 3️⃣ 克隆代码

```bash
cd ~
git clone https://github.com/MMMibo/ai_podcast_v1.git
cd ai_podcast_v1
```

### 4️⃣ 配置后端

```bash
cd ~/ai_podcast_v1/backend
python3 -m venv venv
source venv/bin/activate
pip install Flask Flask-Cors requests pydub PyPDF2 beautifulsoup4 lxml
```

### 5️⃣ 配置前端

```bash
cd ~/ai_podcast_v1/frontend
npm install

# 创建生产环境配置（使用相对路径，通过 Nginx 反向代理）
cat > .env.production << 'EOF'
# 留空表示使用同源请求，通过 Nginx 反向代理到后端
REACT_APP_API_URL=
EOF

# 构建前端
npm run build
```

> **说明**：使用相对路径配置，前端将通过 Nginx 反向代理访问后端 API，无需硬编码服务器地址，更安全且易于维护。

### 6️⃣ 启动服务

```bash
# 启动后端 (使用 PM2)
cd ~/ai_podcast_v1/backend
pm2 start app.py --interpreter ./venv/bin/python3 --name podcast-backend
pm2 save
pm2 startup

# 配置 Nginx (详见文档)
```

## 访问地址
http://47.103.24.213

更多详情请查看完整版文档。
