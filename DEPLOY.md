# Skiba Bot - Google Cloud Deployment Guide

## Step 1: Create Google Cloud Account

1. Go to https://cloud.google.com
2. Click "Get started for free" / "Start free"
3. Sign in with your Google account
4. Enter billing info (you get $300 free credit for 90 days)
5. Create a new project called "skiba-bot"

## Step 2: Install Google Cloud CLI (on your computer)

1. Download: https://cloud.google.com/sdk/docs/install
2. Run the installer
3. Open a new terminal and run:
```
gcloud init
```
4. Log in and select your "skiba-bot" project

## Step 3: Create a Virtual Machine (VM)

Run this command to create a small, cheap VM:

```bash
gcloud compute instances create skiba-bot \
  --zone=me-west1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=10GB \
  --tags=skiba-bot
```

**Cost**: e2-micro = ~$7-8/month (the cheapest option, enough for the bot)
**Zone**: me-west1-a = Tel Aviv (closest to Israel for best performance)

## Step 4: Connect to the VM

```bash
gcloud compute ssh skiba-bot --zone=me-west1-a
```

## Step 5: Install Docker on the VM

Run these commands on the VM (one by one):

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

Log out and back in:
```bash
exit
gcloud compute ssh skiba-bot --zone=me-west1-a
```

## Step 6: Upload Project Files to VM

From YOUR computer (not the VM), run:

```bash
gcloud compute scp --recurse "c:/Users/Eden/Desktop/skiba-bot-cloud" skiba-bot:~/skiba-bot --zone=me-west1-a
```

## Step 7: Create .env File on VM

Connect to the VM and create the .env file:

```bash
gcloud compute ssh skiba-bot --zone=me-west1-a
cd ~/skiba-bot
nano .env
```

Paste your real values:
```
GREEN_API_INSTANCE_ID=7105232057
GREEN_API_TOKEN=your_real_token_here
ANTHROPIC_API_KEY=your_real_key_here
GOOGLE_SHEET_ID=1f92zBisLCQHcSs5GyjZRXwlIW1H0CJkuidmtl72LX6c
MODEL_NAME=claude-sonnet-4-5-20250929
MAX_TOKENS=4096
TEMPERATURE=0.7
```

Press Ctrl+O to save, Ctrl+X to exit nano.

## Step 8: Upload Google Sheets Credentials

From YOUR computer, upload the credentials files:

```bash
gcloud compute scp "c:/Users/Eden/Desktop/test-project2/credentials.json" skiba-bot:~/skiba-bot/credentials.json --zone=me-west1-a

gcloud compute scp "c:/Users/Eden/Desktop/test-project2/token.pickle" skiba-bot:~/skiba-bot/token.pickle --zone=me-west1-a
```

## Step 9: Start the Bot

On the VM:

```bash
cd ~/skiba-bot
docker-compose up -d --build
```

Check it's running:
```bash
docker-compose logs -f
```

Press Ctrl+C to stop watching logs (bot keeps running).

## Daily Commands

### Check bot status:
```bash
docker-compose ps
```

### View recent logs:
```bash
docker-compose logs --tail=50
```

### Restart bot:
```bash
docker-compose restart
```

### Stop bot:
```bash
docker-compose down
```

### Update bot code:
1. Make changes on your computer
2. Upload new files:
```bash
gcloud compute scp --recurse "c:/Users/Eden/Desktop/skiba-bot-cloud" skiba-bot:~/skiba-bot --zone=me-west1-a
```
3. Rebuild and restart:
```bash
docker-compose up -d --build
```

## Troubleshooting

### Bot not responding?
```bash
docker-compose logs --tail=100
```
Look for errors in the output.

### Google Sheets not working?
The `token.pickle` may expire. If it does:
1. Run the bot locally on your computer once to refresh the token
2. Upload the new `token.pickle` to the VM

### VM stopped?
Google may stop free-tier VMs occasionally. Set it to restart automatically:
```bash
gcloud compute instances set-scheduling skiba-bot --zone=me-west1-a --restart-on-failure
```

## Costs Summary

| Resource | Monthly Cost |
|----------|-------------|
| e2-micro VM | ~$7-8 |
| Boot disk (10GB) | ~$0.50 |
| Network (minimal) | ~$0-1 |
| **Total** | **~$8-10/month** |

The $300 free credit covers ~30 months of running this bot.
