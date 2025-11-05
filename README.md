# Daily Fortune API

这里将指导您完成项目的本地开发环境搭建与生产环境部署。

-   [**本地开发与测试**](#本地开发与测试-)
-   [**生产环境部署 (Ubuntu)**](#生产环境部署-ubuntu-)

---

## 本地开发与测试 🔧

本指南旨在帮助您在本地计算机（macOS 或 Linux）上快速搭建开发环境，以便运行、测试和贡献代码。

### 前提条件

在开始之前，请确保您的系统中已安装以下软件：

1.  **Git**: [https://git-scm.com/](https://git-scm.com/)
2.  **Python**: 3.11 或更高版本
3.  **MongoDB**: [MongoDB Community Server](https://www.mongodb.com/try/download/community)
4.  **Redis**: [Redis](https://redis.io/download)

> **macOS 用户提示**: 您可以使用 [Homebrew](https://brew.sh/) 轻松安装 MongoDB (`brew install mongodb-community`) 和 Redis (`brew install redis`)。

### 步骤 1：克隆仓库与环境设置

首先，克隆项目代码到本地，并为其创建一个独立的 Python 虚拟环境。

```bash
# 1. 克隆仓库
git clone https://github.com/oftx/daily-fortune-api.git
cd daily-fortune-api

# 2. 创建并激活 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装所有依赖项
pip install -r requirements.txt
```

> **提示**: 开发结束后，可运行 `deactivate` 命令退出虚拟环境。

### 步骤 2：配置本地环境变量

为了让应用连接到本地数据库，您需要在项目根目录下创建一个 `.env` 文件。

```bash
# 从模板文件复制一份配置
cp .env.example .env

# 使用你喜欢的编辑器（如 VS Code 或 Vim）打开 .env 文件
code .env
```

请确保 `.env` 文件中的配置与您的本地服务匹配。对于本地开发，以下是推荐配置：

```ini
# MongoDB - 使用一个专门用于开发的数据库名
DATABASE_URL="mongodb://localhost:27017"
DATABASE_NAME="daily_fortune_dev"

# JWT - 本地开发时可以使用任意字符串
SECRET_KEY="a_very_secret_key_for_local_dev"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Rate Limiting - 建议在本地开发时禁用，以方便调试
RATE_LIMITING_ENABLED=False
REDIS_URL="redis://localhost:6379"

# Timezone
APP_TIMEZONE="Asia/Shanghai"
DAY_RESET_OFFSET_SECONDS=0
USER_DEFAULT_TIMEZONE="Asia/Shanghai"

# Domain and CORS - 允许本地前端访问
API_DOMAIN="localhost:8000"
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

> **注意**: `.env` 文件已被 `.gitignore` 忽略，不会被提交到代码仓库中。

### 步骤 3：运行开发服务器

一切就绪后，启动 FastAPI 开发服务器。它支持**热重载**，代码更改后会自动重启。

```bash
# 确保虚拟环境已激活
uvicorn main:app --reload
```

服务器成功启动后，您将看到以下输出：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
...
INFO:     Application startup complete.
```

### 步骤 4：访问与测试

*   **API 交互式文档**:
    在浏览器中打开 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。您可以在这个由 Swagger UI 生成的页面上直接测试所有 API 端点。

*   **前端联调**:
    确保您的前端项目 `.env` 文件中的 API 地址指向 `http://127.0.0.1:8000`，然后启动前端开发服务器即可进行联调。

---

## 生产环境部署 (Ubuntu) 🚀

本指南将引导您在 **Ubuntu 22.04 LTS** 服务器上，使用 **Nginx**, **Gunicorn** 和 **Systemd** 对 API 进行生产环境部署。

### 架构概览

```
+-----------------------------------------------------------------------------------+
|                            External World / Internet                              |
+-----------------------------------------------------------------------------------+
                                      |
                                      | (1) HTTPS Request to api.your-domain.com
                                      v
+-----------------------------------------------------------------------------------+
|                                Ubuntu Server (VPS)                                |
|-----------------------------------------------------------------------------------|
|                                                                                   |
|    +-----------------------------+                                                |
|    |      Firewall (UFW)         |  Allows traffic on Port 443 (HTTPS)            |
|    +-----------------------------+                                                |
|                 |                                                                 |
|                 v                                                                 |
|    +-------------------------------------------------------------------------+    |
|    |                             Nginx Web Server                            |    |
|    |-------------------------------------------------------------------------|    |
|    | - Listens on Port 443                                                   |    |
|    | - Terminates SSL (Handles HTTPS Encryption/Decryption)                  |    |
|    | - Acts as a Reverse Proxy                                               |    |
|    | - Serves static files if needed (not in this case)                      |    |
|    +-------------------------------------------------------------------------+    |
|                                      |                                            |
|                                      | (2) Proxy Pass (HTTP Request)              |
|                                      v                                            |
|    +-------------------------------------------------------------------------+    |
|    |                        Gunicorn (WSGI Server)                           |    |
|    |-------------------------------------------------------------------------|    |
|    | - Binds to a local socket (e.g., 127.0.0.1:8000)                        |    |
|    | - Managed by Systemd ('daily-fortune-api.service')                      |    |
|    | - Manages a pool of worker processes                                    |    |
|    |                                                                         |    |
|    |  +------------------+  +------------------+  +------------------+       |    |
|    |  |  Uvicorn Worker  |  |  Uvicorn Worker  |  |  Uvicorn Worker  |  ...  |    |
|    |  +------------------+  +------------------+  +------------------+       |    |
|    |            |                     |                     |                |    |
|    +------------|---------------------|---------------------|----------------+    |
|                 |                     |                     |                     |
|                 |        (3) ASGI Application Call          |                     |
|                 +---------------------+---------------------+                     |
|                                       v                                           |
|    +-------------------------------------------------------------------------+    |
|    |                         FastAPI Application                             |    |
|    |-------------------------------------------------------------------------|    |
|    | - Python Code (`main.py`, Routers, Models, Services)                    |    |
|    | - Middleware (Logging, CORS, Rate Limiting)                             |    |
|    | - Business Logic (User Auth, Fortune Draw, Admin Actions)               |    |
|    | - Pydantic Data Validation                                              |    |
|    +-------------------------------------------------------------------------+    |
|                |                           |                                      |
|  (4) Rate Limit Check (TCP)      (5) Database I/O (TCP)                           |
|                v                           v                                      |
|    +-----------------------+     +-----------------------+                        |
|    |      Redis Server     |     |    MongoDB Server     |                        |
|    |-----------------------|     |-----------------------|                        |
|    | - Stores rate limit   |     | - Stores Users,       |                        |
|    |   counters            |     |   Fortunes, etc.      |                        |
|    | - Managed by Systemd  |     | - Managed by Systemd  |                        |
|    +-----------------------+     +-----------------------+                        |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### 前提条件

1.  一台可以通过 SSH 访问的 Ubuntu 服务器。
2.  一个域名或子域名，其 DNS `A` 记录已指向您服务器的公网 IP。
3.  以具有 `sudo` 权限的用户登录服务器。
4.  服务器防火墙 (UFW) 已启用并允许 SSH (22), HTTP (80) 和 HTTPS (443) 端口的流量。
    ```bash
    sudo ufw allow ssh
    sudo ufw allow http
    sudo ufw allow https
    sudo ufw enable
    ```

### 步骤 1：准备服务器环境

更新系统并安装所有必要的软件包。

```bash
# 更新软件包列表和系统
sudo apt update && sudo apt upgrade -y

# 安装 Python, Nginx, Git, Certbot 等基础工具
sudo apt install python3-pip python3-venv nginx git vim certbot python3-certbot-nginx -y

# 安装 MongoDB 数据库
# 强烈建议遵循官方最新指南: https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
sudo systemctl start mongod
sudo systemctl enable mongod

# 安装 Redis (用于速率限制)
sudo apt install redis-server -y
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 步骤 2：创建专用用户 🔒

为了安全起见，我们不应使用 `root` 用户运行应用。让我们创建一个专用的服务账户。

```bash
# 创建一个名为 'fortuneapi' 的用户，不允许其直接登录
sudo adduser --system --group fortuneapi
```

### 步骤 3：部署应用代码

我们将从 GitHub 克隆代码，并设置好 Python 虚拟环境。

```bash
# 克隆仓库到 /var/www 目录
sudo git clone https://github.com/oftx/daily-fortune-api.git /var/www/daily-fortune-api

# 将项目目录的所有权分配给新创建的用户
sudo chown -R fortuneapi:fortuneapi /var/www/daily-fortune-api

# 进入项目目录
cd /var/www/daily-fortune-api

# 以 'fortuneapi' 用户身份创建虚拟环境和安装依赖
sudo -u fortuneapi python3 -m venv venv
sudo -u fortuneapi /var/www/daily-fortune-api/venv/bin/pip install gunicorn
sudo -u fortuneapi /var/www/daily-fortune-api/venv/bin/pip install -r requirements.txt
```

### 步骤 4：配置生产环境变量

在项目根目录下创建一个 `.env` 文件，用于存放生产环境的敏感配置。

```bash
# 使用 Vim 创建并编辑 .env 文件
sudo vim /var/www/daily-fortune-api/.env
```

按 `i` 进入插入模式，粘贴以下内容。**请务必根据您的实际情况修改占位符**。

```ini
# MongoDB
DATABASE_URL="mongodb://localhost:27017"
DATABASE_NAME="daily_fortune_prod"

# JWT - ！！！重要：生成一个新的安全密钥用于生产环境！！！
# 在终端运行 `openssl rand -hex 32` 生成一个。
SECRET_KEY="<your_generated_32_byte_hex_secret_key>"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=43200 # 30 days

# Rate Limiting
RATE_LIMITING_ENABLED=True
REDIS_URL="redis://localhost:6379"

# Timezone
APP_TIMEZONE="Asia/Shanghai"
DAY_RESET_OFFSET_SECONDS=0
USER_DEFAULT_TIMEZONE="Asia/Shanghai"

# Domain and CORS - ！！！重要：替换为您的真实域名！！！
API_DOMAIN="api.your-project.com"
CORS_ORIGINS="https://your-frontend.com"
```

> **安全警告**:
> *   确保将 `<your_generated_32_byte_hex_secret_key>` 替换为您自己生成的**唯一**且**保密**的密钥。
> *   将 `API_DOMAIN` 和 `CORS_ORIGINS` 替换为您的生产环境域名。

完成编辑后，按 `Esc`，输入 `:wq` 并回车保存退出。最后，设置文件权限，仅允许 `fortuneapi` 用户读取。

```bash
# 设置 .env 文件所有权和权限
sudo chown fortuneapi:fortuneapi /var/www/daily-fortune-api/.env
sudo chmod 600 /var/www/daily-fortune-api/.env
```

### 步骤 5：配置 Systemd 服务

创建一个 Systemd 服务文件，让 API 应用能够作为后台服务持久运行，并实现开机自启。

```bash
# 创建服务文件
sudo vim /etc/systemd/system/daily-fortune-api.service
```

粘贴以下配置。注意，我们指定了服务以 `fortuneapi` 用户身份运行。

```ini
[Unit]
Description=Daily Fortune API Gunicorn Service
After=network.target

[Service]
# 使用我们创建的专用用户
User=fortuneapi
Group=fortuneapi

# 工作目录和环境变量文件路径
WorkingDirectory=/var/www/daily-fortune-api
EnvironmentFile=/var/www/daily-fortune-api/.env

# 启动命令
# Gunicorn 的 worker 数量通常建议设置为 (2 * CPU核心数) + 1
ExecStart=/var/www/daily-fortune-api/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000

# 确保服务在失败时会自动重启
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

现在，启动并启用这个新服务：

```bash
# 重新加载 Systemd 配置
sudo systemctl daemon-reload
# 启动服务
sudo systemctl start daily-fortune-api
# 设置为开机自启
sudo systemctl enable daily-fortune-api
```

> **故障排查**:
> *   检查服务状态: `sudo systemctl status daily-fortune-api`
> *   查看详细日志: `sudo journalctl -u daily-fortune-api.service -e`

### 步骤 6：配置 Nginx 反向代理

Nginx 将作为我们应用的前端，处理外部请求并将其转发到本地 8000 端口运行的 Gunicorn 服务。

```bash
# 创建 Nginx 配置文件，将 <your_domain> 替换为您的域名
sudo vim /etc/nginx/sites-available/<your_domain>.conf
```

粘贴以下配置，并将所有 `<your_domain>` 替换为您的真实域名：

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

启用此配置并重启 Nginx：

```bash
# 创建软链接以启用配置
sudo ln -s /etc/nginx/sites-available/<your_domain>.conf /etc/nginx/sites-enabled/

# 测试 Nginx 配置语法是否正确
sudo nginx -t

# 重启 Nginx 服务
sudo systemctl restart nginx
```

此时，您应该可以通过 `http://<your_domain>` 访问到 API 了。

### 步骤 7：启用 HTTPS (SSL加密)

最后，使用 Certbot 为您的域名自动获取并配置免费的 Let's Encrypt SSL 证书。

```bash
# 运行 Certbot，它将自动修改您的 Nginx 配置
# 将 <your_domain> 替换为您的域名
sudo certbot --nginx -d <your_domain>
```

在 Certbot 的交互式提示中：
1.  输入您的电子邮件地址（用于接收续订提醒）。
2.  同意服务条款。
3.  当询问是否将所有 HTTP 流量重定向到 HTTPS 时，选择 `2` (Redirect)
    ，这是推荐选项。

Certbot 会自动处理证书的获取、配置和未来的自动续订。

**部署完成！** 您的 API 现已通过 HTTPS 安全、稳定地运行在您的 Ubuntu 服务器上。