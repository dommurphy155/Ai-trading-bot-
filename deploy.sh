# deploy.sh
#!/bin/bash

echo "==== Deployment started at $(date -Iseconds) ===="

# Update package lists and install required packages
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3.10-distutils build-essential libssl-dev libffi-dev python3-dev

# Create and activate virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install required Python packages
pip install --upgrade pip setuptools wheel

# Install packages from requirements.txt except MetaTrader5
pip install -r requirements.txt || true

# PM2 installation check
if ! command -v pm2 &> /dev/null; then
    echo "PM2 not found, installing Node.js 16.x and PM2..."
    curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
    sudo apt-get install -y nodejs
    sudo npm install -g pm2
fi

echo "Starting app with PM2..."
pm2 stop ai-trader-bot || true
pm2 delete ai-trader-bot || true
pm2 start main.py --name ai-trader-bot --interpreter ~/.venv/bin/python --watch

echo "==== Deployment complete ===="
