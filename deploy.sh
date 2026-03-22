#!/bin/bash
set -e

APP_DIR="/var/www/havlist"
SERVICE="havlist"

cd "$APP_DIR"

echo "Pulling latest changes..."
git pull origin main

echo "Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

echo "Restarting service..."
sudo systemctl restart "$SERVICE"

echo "Checking status..."
sleep 1
if systemctl is-active --quiet "$SERVICE"; then
    echo "Deploy complete — $SERVICE is running."
else
    echo "ERROR: $SERVICE failed to start!"
    sudo journalctl -u "$SERVICE" -n 10 --no-pager
    exit 1
fi
