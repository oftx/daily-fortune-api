## 本地开发与测试

本指南将帮助您在本地计算机（macOS 或 Linux）上快速搭建开发环境，以便运行、测试和贡献代码。

### 前提条件

1.  **Git**: 您的计算机上已安装 [Git](https://git-scm.com/)。
2.  **Python**: 已安装 Python 3.11 或更高版本。
3.  **MongoDB**: 本地已安装并运行 MongoDB 服务。您可以从 [MongoDB 官网](https://www.mongodb.com/try/download/community) 下载或使用 [Homebrew](https://brew.sh/) (`brew install mongodb-community`) 安装。
4.  **Redis**: 本地已安装并运行 Redis 服务。您可以使用 [Homebrew](https://brew.sh/) (`brew install redis`) 安装。

### 1. 克隆与环境设置

首先，将项目克隆到您的本地机器，并设置好独立的 Python 虚拟环境。

```bash
# 克隆仓库
git clone https://github.com/oftx/daily-fortune-api.git
cd daily-fortune-api

# 创建并激活 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 在虚拟环境中安装所有开发依赖
pip install -r requirements.txt
```
> **提示**: 当您完成开发后，可以在终端中运行 `deactivate` 命令来退出虚拟环境。

### 2. 配置本地环境变量

为了让应用能够连接到本地的数据库和 Redis，您需要在项目根目录下创建一个 `.env` 文件。

```bash
# 从模板复制一份 .env 文件
cp .env.example .env

# 使用你喜欢的编辑器打开 .env 文件进行配置
# 例如使用 vim 或 VS Code
vim .env
```

`.env` 文件是本地开发的私有配置，已被 `.gitignore` 忽略，不会提交到 Git 仓库。请确保其内容如下，以匹配本地服务：

```env
# MongoDB
DATABASE_URL="mongodb://localhost:27017"
DATABASE_NAME="daily_fortune_dev" # 使用一个专门用于开发的数据库名

# JWT - 可以使用任意字符串用于本地开发
SECRET_KEY="local_secret_key_for_testing_only"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Rate Limiting - 可以在本地开发时禁用以方便调试
RATE_LIMITING_ENABLED=False
REDIS_URL="redis://localhost:6379"

# Timezone and Reset Logic
APP_TIMEZONE="Asia/Shanghai"
DAY_RESET_OFFSET_SECONDS=0
USER_DEFAULT_TIMEZONE="Asia/Shanghai"

# Domain and CORS
API_DOMAIN="localhost:8000"
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```
> **注意**: 在本地开发时，将 `RATE_LIMITING_ENABLED` 设置为 `False` 可以避免在频繁测试 API 时被速率限制阻挡。

### 3. 运行开发服务器

完成以上配置后，您就可以启动 FastAPI 的开发服务器了。服务器支持热重载 (hot-reloading)，这意味着您对代码的任何修改都会被自动检测并重新加载，无需手动重启。

在项目根目录（确保虚拟环境已激活），运行以下命令：

```bash
# 同时激活虚拟环境并启动 Uvicorn 开发服务器
source venv/bin/activate && uvicorn main:app --reload
```

如果一切顺利，您将在终端看到类似以下的输出：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Rate limiting is DISABLED.
INFO:     Application startup complete.
```

现在，您的 API 服务器已经在本地的 8000 端口上运行了。

### 4. 访问与测试

*   **API 文档**: 打开浏览器并访问 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。您会看到由 FastAPI 自动生成的 Swagger UI 交互式 API 文档。您可以在这里直接测试每一个 API 端点。
*   **前端联调**: 确保您的 `daily-fortune-client` 前端项目的 `.env` 文件中 `VITE_API_BASE_URL` 指向 `http://127.0.0.1:8000`。然后启动前端开发服务器，即可进行前后端联调测试。


## 生产环境部署流程 (Ubuntu)

本指南将引导您在 Ubuntu 22.04 LTS 或更高版本的服务器上，使用 Nginx、Gunicorn 和 Systemd 对 `daily-fortune-api` 进行生产环境部署。

### 前提条件

1.  一台可以通过 SSH 访问的 Ubuntu 服务器。
2.  一个域名或子域名（例如 `api.your-project.com`），其 DNS A 记录已指向您服务器的 IP 地址。
3.  以具有 `sudo` 权限的用户身份登录服务器。
4.  服务器防火墙 (UFW) 已配置并允许 SSH (22), HTTP (80), 和 HTTPS (443) 端口的流量。
    ```bash
    sudo ufw allow ssh
    sudo ufw allow http
    sudo ufw allow https
    sudo ufw enable
    ```

### 1. 准备服务器环境

首先，更新系统并安装所有必要的软件包。

```bash
# 更新软件包列表和系统
sudo apt update && sudo apt upgrade -y

# 安装 Python, Nginx, Git, Vim, Certbot 等基础工具
sudo apt install python3-pip python3-venv nginx git vim certbot python3-certbot-nginx -y

# 安装 MongoDB 数据库
# 请遵循官方最新指南: https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
# 安装后启动并设置为开机自启
sudo systemctl start mongod
sudo systemctl enable mongod

# 安装 Redis (用于速率限制)
sudo apt install redis-server -y
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 2. 部署应用代码

我们将从 GitHub 克隆项目代码并设置好 Python 虚拟环境。

```bash
# 克隆官方仓库到 /var/www 目录
sudo git clone https://github.com/oftx/daily-fortune-api.git /var/www/daily-fortune-api

# 将项目目录的所有权分配给当前用户
# 这将自动获取您的用户名并设置权限
sudo chown -R $(whoami):$(whoami) /var/www/daily-fortune-api

# 进入项目目录
cd /var/www/daily-fortune-api

# 创建并激活 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 在虚拟环境中安装 Gunicorn 和项目依赖
pip install gunicorn
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录下创建一个 `.env` 文件，用于存放生产环境的全部配置。

```bash
# 使用 Vim 创建并编辑 .env 文件
vim .env
```

进入 Vim 后，按 `i` 键进入插入模式，将以下内容**完整地**粘贴到文件中。然后按 `Esc` 键，输入 `:wq` 并按 `Enter` 保存并退出。**请务必根据您的实际情况修改**相应的值。

```env
# MongoDB
DATABASE_URL="mongodb://localhost:27017"
DATABASE_NAME="daily_fortune"

# JWT - IMPORTANT: Generate a new key for production!
# Use `openssl rand -hex 32` in your terminal to generate one.
SECRET_KEY="<your_generated_secret_key>"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Rate Limiting
RATE_LIMITING_ENABLED=True
REDIS_URL="redis://localhost:6379"

# Timezone and Reset Logic
APP_TIMEZONE="Asia/Shanghai"
DAY_RESET_OFFSET_SECONDS=0
USER_DEFAULT_TIMEZONE="Asia/Shanghai"

# Domain and CORS - IMPORTANT: Replace with your actual domains
API_DOMAIN="api.your-project.com"
CORS_ORIGINS="https://your-frontend.com,http://localhost:5173"
```
> **重要**:
> *   请务必将 `<your_generated_secret_key>` 替换为您自己生成的安全密钥。
> *   确认 `API_DOMAIN` 替换为您的后端域名，`CORS_ORIGINS` 中的 `https://your-frontend.com` 替换为您的前端域名。

### 4. 配置 Systemd 服务

为了让我们的 API 应用能够作为后台服务持久运行，并实现开机自启，我们需要创建一个 Systemd 服务文件。

```bash
# 创建服务文件
sudo vim /etc/systemd/system/daily-fortune-api.service
```

按 `i` 键进入插入模式，将以下内容粘贴到文件中。

```ini
[Unit]
Description=Daily Fortune API Gunicorn Service
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/daily-fortune-api
EnvironmentFile=/var/www/daily-fortune-api/.env
ExecStart=/var/www/daily-fortune-api/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```
> **注意**: 此配置指定服务以 `root` 用户身份运行。这是一个可行的配置，但请注意在生产环境中遵循最小权限原则。
>
按 `Esc` 键，输入 `:wq` 并按 `Enter` 保存并退出。

现在，启动并启用这个新创建的服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start daily-fortune-api
sudo systemctl enable daily-fortune-api
```

您可以通过 `sudo systemctl status daily-fortune-api` 来检查服务是否成功运行。如果遇到问题，请使用 `sudo journalctl -u daily-fortune-api.service -e` 查看详细日志。

### 5. 配置 Nginx 反向代理

Nginx 将作为我们应用的前端，处理外部的 HTTP/HTTPS 请求，并将其转发到在本地 8000 端口运行的 Gunicorn 服务。

```bash
# 创建 Nginx 配置文件
# 将 <your_domain> 替换为您的域名，例如 api.your-project.com
sudo vim /etc/nginx/conf.d/<your_domain>.conf
```

按 `i` 键进入插入模式，将以下内容粘贴到文件中，并将 `<your_domain>` 替换为您的域名：

```nginx
server {
    listen 80;
    server_name <your_domain>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
按 `Esc` 键，输入 `:wq` 并按 `Enter` 保存并退出。

测试 Nginx 配置并重启服务：

```bash
sudo nginx -t
sudo systemctl restart nginx
```

此时，您应该可以通过 `http://<your_domain>` 访问到 API 的欢迎信息了。

### 6. 启用 HTTPS (SSL加密)

最后，我们使用 Certbot 为您的域名自动获取并配置免费的 Let's Encrypt SSL 证书。

```bash
# 运行 Certbot，它将自动修改您的 Nginx 配置
# 将 <your_domain> 替换为您的域名
sudo certbot --nginx -d <your_domain>
```

在 Certbot 的交互式提示中：
1.  输入您的电子邮件地址。
2.  同意服务条款。
3.  当询问是否将 HTTP 流量重定向到 HTTPS 时，选择 `2` (Redirect)。

Certbot 会自动处理证书的获取、配置和未来的自动续订。

**部署完成！** 您的 `daily-fortune-api` 现已安全、稳定地运行在您的 Ubuntu 服务器上。
