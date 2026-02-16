#!/bin/bash

# Skiba Bot - Cloud Update Script
# This script safely updates the bot running on Google Cloud VM

set -e  # Exit on any error

echo "=================================="
echo "Skiba Bot - Cloud Update Script"
echo "=================================="
echo ""

# Configuration
VM_NAME="skiba-bot"
ZONE="me-west1-a"
BOT_DIR="~/skiba-bot"

echo "Step 1/5: Connecting to Google Cloud VM..."
echo "-------------------------------------------"

# Create the update commands
UPDATE_COMMANDS=$(cat <<'REMOTE_SCRIPT'
set -e
cd ~/skiba-bot || { echo "Error: Bot directory not found!"; exit 1; }

echo ""
echo "Step 2/5: Checking current status..."
echo "-------------------------------------------"
docker-compose ps

echo ""
echo "Step 3/5: Pulling latest code from GitHub..."
echo "-------------------------------------------"
git fetch origin
git status
git pull origin master

echo ""
echo "Step 4/5: Rebuilding and restarting bot..."
echo "-------------------------------------------"
docker-compose down
docker-compose up -d --build

echo ""
echo "Step 5/5: Verifying new bot is running..."
echo "-------------------------------------------"
sleep 5
docker-compose ps
echo ""
echo "Checking logs (last 30 lines)..."
docker-compose logs --tail=30

echo ""
echo "=================================="
echo "✅ Update completed successfully!"
echo "=================================="
echo ""
echo "Bot is now running with the new version:"
echo "  - רוקי-סאן persona introduced"
echo "  - Natural conversation flow"
echo "  - Israeli-friendly tone"
echo ""
echo "To monitor logs: docker-compose logs -f"
echo "To check status: docker-compose ps"
echo ""
REMOTE_SCRIPT
)

# Execute commands on remote VM
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="$UPDATE_COMMANDS"

echo ""
echo "🎉 All done! Your bot is now updated and running."
echo ""
