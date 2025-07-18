#!/usr/bin/env python3
import sys
import os
# Add the virtual environment path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'venv/lib/python3.13/site-packages'))
"""
Interactive setup script for Lovable Status Bot
Helps users configure their .env file step by step
"""

import os
import sys
import requests
from dotenv import load_dotenv

def print_header():
    print("\n" + "="*60)
    print("🤖 LOVABLE STATUS BOT - SETUP WIZARD")
    print("="*60 + "\n")

def print_section(title):
    print(f"\n{'─'*40}")
    print(f"📋 {title}")
    print(f"{'─'*40}\n")

def validate_bot_token(token):
    """Validate bot token by making a test API call"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        data = response.json()
        if data.get('ok'):
            bot_info = data.get('result', {})
            print(f"✅ Valid bot token! Bot name: @{bot_info.get('username', 'unknown')}")
            return True
        else:
            print(f"❌ Invalid token: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error validating token: {e}")
        return False

def test_channel_access(token, channel_id):
    """Test if bot can send messages to the channel"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                'chat_id': channel_id,
                'text': '✅ Bot setup test successful! Your bot can post to this channel.'
            }
        )
        data = response.json()
        if data.get('ok'):
            print("✅ Test message sent successfully!")
            return True
        else:
            error = data.get('description', 'Unknown error')
            if 'chat not found' in error.lower():
                print("❌ Channel not found. Make sure:")
                print("   - For public channels: use @channelname format")
                print("   - For private channels: use the numeric ID (e.g., -1001234567890)")
                print("   - Bot is added as administrator to the channel")
            elif 'not enough rights' in error.lower():
                print("❌ Bot doesn't have permission to post. Add bot as channel admin!")
            else:
                print(f"❌ Error: {error}")
            return False
    except Exception as e:
        print(f"❌ Error testing channel: {e}")
        return False

def get_channel_id_instructions():
    print("\n📱 HOW TO GET YOUR CHANNEL ID:\n")
    print("For PUBLIC channels:")
    print("  → Just use: @your_channel_username\n")
    print("For PRIVATE channels:")
    print("  1. Send a message to your channel")
    print("  2. Visit this URL (replace YOUR_BOT_TOKEN):")
    print("     https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates")
    print("  3. Find the 'chat' object with your channel")
    print("  4. Copy the 'id' value (including the minus sign)")
    print("\nExample IDs:")
    print("  Public:  @lovable_status")
    print("  Private: -1001234567890\n")

def setup_wizard():
    print_header()
    
    # Check if .env already exists
    if os.path.exists('.env'):
        print("⚠️  A .env file already exists!")
        overwrite = input("Do you want to create a new configuration? (y/N): ").lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    print("This wizard will help you set up your Telegram bot.\n")
    print("First, you need to create a bot on Telegram:")
    print("1. Open Telegram and search for @BotFather")
    print("2. Send /newbot and follow the instructions")
    print("3. Copy the bot token you receive\n")
    
    # Get bot token
    print_section("STEP 1: Bot Token")
    while True:
        token = input("Enter your bot token: ").strip()
        if not token:
            print("❌ Token cannot be empty!")
            continue
        
        print("\nValidating bot token...")
        if validate_bot_token(token):
            break
        
        retry = input("\nDo you want to try again? (Y/n): ").lower()
        if retry == 'n':
            print("Setup cancelled.")
            return
    
    # Get channel ID
    print_section("STEP 2: Channel Setup")
    print("Make sure you have:")
    print("✓ Created a Telegram channel")
    print("✓ Added your bot as administrator to the channel")
    
    get_channel_id_instructions()
    
    while True:
        channel_id = input("Enter your channel ID: ").strip()
        if not channel_id:
            print("❌ Channel ID cannot be empty!")
            continue
        
        print(f"\nTesting access to channel: {channel_id}")
        if test_channel_access(token, channel_id):
            break
        
        print("\n1. View instructions again")
        print("2. Try a different channel ID")
        print("3. Cancel setup")
        choice = input("\nYour choice (1/2/3): ").strip()
        
        if choice == '1':
            get_channel_id_instructions()
        elif choice == '3':
            print("Setup cancelled.")
            return
    
    # Advanced settings
    print_section("STEP 3: Advanced Settings (Optional)")
    print("Press Enter to use default values\n")
    
    check_interval = input("Check interval in minutes (default: 5): ").strip()
    if not check_interval:
        check_interval = "5"
    
    log_level = input("Log level - INFO/DEBUG/WARNING/ERROR (default: INFO): ").strip().upper()
    if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        log_level = "INFO"
    
    # Create .env file
    print_section("Creating Configuration")
    
    env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={token}
TELEGRAM_CHANNEL_ID={channel_id}

# Feed Configuration
RSS_FEED_URL=https://status.lovable.dev/feed.rss
CHECK_INTERVAL_MINUTES={check_interval}

# Database Configuration
DATABASE_PATH=lovable_status.db

# Logging Configuration
LOG_LEVEL={log_level}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Configuration file created successfully!")
    
    # Final instructions
    print_section("Setup Complete!")
    print("Your bot is now configured. To start monitoring:\n")
    print("With Docker:")
    print("  docker-compose up -d\n")
    print("With Python:")
    print("  python main.py\n")
    print("View logs:")
    print("  docker-compose logs -f  (Docker)")
    print("  tail -f lovable_status_bot.log  (Python)\n")
    print("Happy monitoring! 🚀")

if __name__ == "__main__":
    try:
        setup_wizard()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)