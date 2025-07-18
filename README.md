# Lovable Status Telegram Bot

A Python bot that monitors Lovable.dev status page and posts incident updates to a Telegram channel.

## Features

- Monitors RSS feed from status.lovable.dev every 5 minutes
- Posts new incidents to Telegram channel
- Updates existing incidents when status changes
- SQLite database to track posted incidents
- Docker support for easy deployment
- Comprehensive logging

## Prerequisites

- Python 3.11+ (for local deployment)
- Docker & Docker Compose (for containerized deployment)
- Telegram Bot Token
- Telegram Channel ID

## Setup Instructions

### 1. Create a Telegram Bot

1. Open Telegram and search for @BotFather
2. Send `/newbot` and follow the instructions
3. Save the bot token you receive

### 2. Get Your Channel ID

1. Add your bot as an administrator to your Telegram channel
2. Send a message to the channel
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for the `"chat":{"id":` field - this is your channel ID

### 3. Configure the Bot

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHANNEL_ID=@your_channel_or_-123456789
   ```

## Deployment Options

### Option 1: Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

### Option 2: Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

### Option 3: Systemd Service (Linux)

1. Create a service file `/etc/systemd/system/lovable-status-bot.service`:

```ini
[Unit]
Description=Lovable Status Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/lovable-status-bot
Environment="PATH=/usr/local/bin:/usr/bin"
ExecStart=/usr/bin/python3 /path/to/lovable-status-bot/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:
```bash
sudo systemctl enable lovable-status-bot
sudo systemctl start lovable-status-bot
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| TELEGRAM_BOT_TOKEN | Your Telegram bot token | Required |
| TELEGRAM_CHANNEL_ID | Your Telegram channel ID | Required |
| RSS_FEED_URL | Status page RSS feed URL | https://status.lovable.dev/feed.rss |
| CHECK_INTERVAL_MINUTES | How often to check for updates | 5 |
| DATABASE_PATH | SQLite database file path | lovable_status.db |
| LOG_LEVEL | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |

## Message Format

The bot posts incidents in the following format:

```
🚨 INCIDENT: Chat requests failing

🔍 Status: Identified
📝 Description: We are currently experiencing a large amount of chat requests failing. The issue is being fixed.

🔗 View Details

⏰ Updated: 2025-07-18 13:27 UTC
```

Status emojis:
- ✅ Resolved
- 🔍 Identified  
- 👀 Monitoring
- 🔎 Investigating
- ❓ Unknown

## Troubleshooting

### Bot not posting messages
1. Check bot token is correct
2. Ensure bot is admin in the channel
3. Verify channel ID (use @username for public channels or -123456789 for private)
4. Check logs for errors

### Database errors
- Delete `lovable_status.db` to reset the database
- Ensure write permissions in the directory

### Connection errors
- Check internet connectivity
- Verify RSS feed URL is accessible
- Check Telegram API status

## Development

### Running tests
```bash
python -m pytest tests/
```

### Adding new features
1. Status filtering by severity
2. Multiple channel support
3. Custom message templates
4. Webhook support for instant updates

## License

MIT