#!/usr/bin/env python3
"""
Simplified monitor script for GitHub Actions
"""
import os
import sys
import feedparser
import requests
import sqlite3
from datetime import datetime
import re

# Configuration from environment
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
RSS_FEED_URL = os.getenv('RSS_FEED_URL', 'https://status.lovable.dev/feed.rss')
DATABASE_PATH = 'lovable_status.db'

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            guid TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT,
            description TEXT,
            link TEXT,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            telegram_message_id INTEGER,
            last_updated TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized")

def clean_html(html_text):
    """Remove HTML tags and clean text"""
    if not html_text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Remove redundant status prefix
    text = re.sub(r'^Status:\s*(Resolved|Identified|Monitoring|Investigating)\s*', '', text, flags=re.IGNORECASE)
    return text.strip()

def extract_status(text):
    """Extract status from text"""
    text_lower = text.lower()
    if 'resolved' in text_lower:
        return 'Resolved'
    elif 'identified' in text_lower:
        return 'Identified'
    elif 'monitoring' in text_lower:
        return 'Monitoring'
    elif 'investigating' in text_lower:
        return 'Investigating'
    return 'Unknown'

def send_telegram_message(text):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"Message sent successfully: {result['result']['message_id']}")
            return result['result']['message_id']
        else:
            print(f"Failed to send message: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def format_message(incident):
    """Format incident for Telegram"""
    status_emoji = {
        'Resolved': '✅',
        'Identified': '🔍',
        'Monitoring': '👀',
        'Investigating': '🔎',
        'Unknown': '❓'
    }
    
    emoji = status_emoji.get(incident['status'], '❓')
    
    message = f"🚨 *INCIDENT: {incident['title']}*\n\n"
    message += f"{emoji} *Status:* {incident['status']}\n"
    
    if incident.get('description'):
        clean_desc = clean_html(incident['description'])
        if clean_desc:
            message += f"📝 *Description:* {clean_desc}\n"
    
    if incident.get('link'):
        message += f"\n🔗 [View Details]({incident['link']})\n"
    
    message += f"\n⏰ _Updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}_"
    
    return message

def check_incident_exists(guid):
    """Check if incident already exists in database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT guid FROM incidents WHERE guid = ?', (guid,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_incident(incident):
    """Save incident to database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO incidents 
        (guid, title, status, description, link, telegram_message_id, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        incident['guid'],
        incident['title'],
        incident['status'],
        incident.get('description', ''),
        incident.get('link', ''),
        incident.get('telegram_message_id'),
        datetime.now()
    ))
    conn.commit()
    conn.close()

def send_test_message():
    """Send a test message to verify bot is working"""
    test_message = """🔔 *Bot Status Check*

✅ Lovable Status Bot is active and monitoring
📡 Checking every 5 minutes for new incidents
🔍 Currently filtering: Active incidents only

_This is an automated test message_"""
    
    print("Sending test message...")
    message_id = send_telegram_message(test_message)
    if message_id:
        print(f"Test message sent successfully! ID: {message_id}")
        return True
    else:
        print("Failed to send test message")
        return False

def main():
    print("Starting Lovable Status Monitor (Simple Mode)")
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"Channel: {TELEGRAM_CHANNEL_ID}")
    print(f"Feed URL: {RSS_FEED_URL}")
    
    # Send test message on first run or if requested
    if os.getenv('SEND_TEST_MESSAGE', 'false').lower() == 'true' or not os.path.exists(DATABASE_PATH):
        send_test_message()
    
    # Initialize database
    init_database()
    
    # Parse RSS feed
    print(f"Fetching RSS feed from {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)
    
    if feed.bozo:
        print(f"Error parsing feed: {feed.bozo_exception}")
        return
    
    print(f"Found {len(feed.entries)} entries in feed")
    
    # Track what we process
    active_incidents = 0
    new_incidents = 0
    
    # Process entries (newest first)
    for entry in feed.entries:
        incident = {
            'guid': entry.get('guid', entry.get('id', '')),
            'title': entry.get('title', 'No title'),
            'description': entry.get('summary', entry.get('description', '')),
            'link': entry.get('link', ''),
        }
        
        incident['status'] = extract_status(incident['description'] + ' ' + incident['title'])
        
        print(f"\nProcessing: {incident['title']} - Status: {incident['status']}")
        
        # Skip resolved incidents (unless testing)
        if incident['status'] == 'Resolved' and os.getenv('SHOW_RESOLVED', 'false').lower() != 'true':
            print(f"  → Skipping (resolved)")
            continue
        
        active_incidents += 1
        
        # Check if already posted
        if check_incident_exists(incident['guid']):
            print(f"  → Already posted")
            continue
        
        # Send to Telegram
        print(f"  → Posting to Telegram...")
        message = format_message(incident)
        message_id = send_telegram_message(message)
        
        if message_id:
            incident['telegram_message_id'] = message_id
            save_incident(incident)
            new_incidents += 1
            print(f"  → Success! Message ID: {message_id}")
        else:
            print(f"  → Failed to send message")
    
    print(f"\nSummary:")
    print(f"- Total entries: {len(feed.entries)}")
    print(f"- Active incidents: {active_incidents}")
    print(f"- New incidents posted: {new_incidents}")
    print("Monitor run completed successfully")

if __name__ == "__main__":
    # Check required environment variables
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("ERROR: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID")
        sys.exit(1)
    
    main()