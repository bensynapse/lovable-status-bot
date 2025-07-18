# Complete Setup Guide for Lovable Status Bot

This guide will walk you through getting all the required information to set up your `.env` file.

## 🤖 Step 1: Create a Telegram Bot and Get Token

### 1.1 Open Telegram and Find BotFather
- Open Telegram app (mobile or desktop)
- In the search bar, type: `@BotFather`
- Click on the verified BotFather (has a blue checkmark ✓)

### 1.2 Create Your Bot
- Send the message: `/newbot`
- BotFather will ask for a bot name. Example: `Lovable Status Monitor`
- Then choose a username ending in 'bot'. Example: `lovable_status_bot`

### 1.3 Save Your Token
BotFather will respond with:
```
Done! Congratulations on your new bot. You will find it at t.me/lovable_status_bot.

Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890

Keep your token secure and store it safely!
```

**SAVE THIS TOKEN!** This is your `TELEGRAM_BOT_TOKEN`

## 📢 Step 2: Create a Telegram Channel and Get Channel ID

### 2.1 Create a Channel
- In Telegram, click the menu (☰) or "New Message" icon
- Select "New Channel"
- Choose a name: Example: `Lovable Status Updates`
- Choose if it's public or private
- If public, create a username like `@lovable_status`

### 2.2 Add Your Bot as Admin
- Go to your channel
- Click channel name at the top → "Administrators"
- Click "Add Administrator"
- Search for your bot username (e.g., `@lovable_status_bot`)
- Give it permissions to post messages

### 2.3 Get Your Channel ID

#### For PUBLIC Channels:
Your channel ID is simply: `@your_channel_username`
Example: `@lovable_status`

#### For PRIVATE Channels:
1. Send any message to your channel
2. Open this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890/getUpdates
   ```

3. Look for your channel in the JSON response:
   ```json
   {
     "channel_post": {
       "chat": {
         "id": -1001234567890,
         "title": "Lovable Status Updates",
         "type": "channel"
       }
     }
   }
   ```

4. Your channel ID is the number (including the minus sign): `-1001234567890`

## 🔧 Step 3: Create Your .env File

### 3.1 Copy the template
```bash
cd /home/ben/Documents/ben\ is\ a\ dev/lovable\ alerts/lovable-status-bot
cp .env.example .env
```

### 3.2 Edit the .env file
```bash
nano .env
# or use your favorite editor
```

### 3.3 Fill in your values:
```env
# Replace with your actual bot token from Step 1.3
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890

# Replace with your channel ID from Step 2.3
# For public channel:
TELEGRAM_CHANNEL_ID=@lovable_status
# OR for private channel:
TELEGRAM_CHANNEL_ID=-1001234567890

# These can stay as defaults
RSS_FEED_URL=https://status.lovable.dev/feed.rss
CHECK_INTERVAL_MINUTES=5
DATABASE_PATH=lovable_status.db
LOG_LEVEL=INFO
```

## ✅ Step 4: Test Your Setup

### Test if your bot can send messages:
```bash
# Install dependencies first
pip install -r requirements.txt

# Run a quick test
python3 -c "
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
try:
    bot.send_message(
        chat_id=os.getenv('TELEGRAM_CHANNEL_ID'),
        text='✅ Bot setup successful! Ready to monitor Lovable status.'
    )
    print('✅ Test message sent successfully!')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

If you see the test message in your channel, you're ready to go!

## 🚀 Step 5: Run the Bot

### Option A: Docker (Recommended)
```bash
docker-compose up -d
```

### Option B: Direct Python
```bash
python main.py
```

## 🆘 Troubleshooting

### "Unauthorized" Error
- Check your bot token is correct (no extra spaces)
- Make sure you copied the entire token

### "Chat not found" Error
- Ensure bot is admin in the channel
- For private channels, use the numeric ID with minus sign
- For public channels, use @username format

### Bot Not Posting
- Check logs: `docker-compose logs` or check `lovable_status_bot.log`
- Verify the RSS feed is accessible: `curl https://status.lovable.dev/feed.rss`

## 📝 Quick Checklist

- [ ] Created bot with BotFather
- [ ] Saved bot token
- [ ] Created Telegram channel
- [ ] Added bot as channel admin
- [ ] Got channel ID
- [ ] Created .env file with correct values
- [ ] Tested bot can send messages
- [ ] Started bot with Docker or Python

Need help? Check the logs first, then verify each step above!