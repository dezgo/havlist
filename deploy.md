# Deploying HavList to a Linux VPS

## 1. Server setup

```bash
sudo apt update && sudo apt install python3 python3-venv python3-pip nginx certbot python3-certbot-nginx -y
```

## 2. Clone and install

```bash
cd /opt
git clone <your-repo-url> havlist
cd havlist
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Environment

```bash
cp .env.example .env
# Edit .env:
#   SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
#   ANTHROPIC_API_KEY=<your key, optional — only needed for AI analysis>
```

## 4. Systemd service

Create `/etc/systemd/system/havlist.service`:

```ini
[Unit]
Description=HavList Inventory App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/havlist
EnvironmentFile=/opt/havlist/.env
ExecStart=/opt/havlist/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now havlist
```

## 5. Nginx reverse proxy

Create `/etc/nginx/sites-available/havlist`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/havlist /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 6. HTTPS (required for PWA + camera)

```bash
sudo certbot --nginx -d your-domain.com
```

## 7. File permissions

```bash
sudo mkdir -p /opt/havlist/uploads
sudo chown -R www-data:www-data /opt/havlist/uploads /opt/havlist/havlist.db
```
