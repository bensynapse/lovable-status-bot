#!/usr/bin/env python3
import sys
import os
# Add the virtual environment path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'venv/lib/python3.13/site-packages'))
import feedparser
import sqlite3
import logging
import time
import schedule
import sys
from datetime import datetime
from typing import Optional, Dict, List
import requests
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode
from config import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lovable_status_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
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
            logger.info("Database initialized")
    
    def get_incident(self, guid: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guid, title, status, description, link, telegram_message_id, last_updated
                FROM incidents WHERE guid = ?
            ''', (guid,))
            row = cursor.fetchone()
            if row:
                return {
                    'guid': row[0],
                    'title': row[1],
                    'status': row[2],
                    'description': row[3],
                    'link': row[4],
                    'telegram_message_id': row[5],
                    'last_updated': row[6]
                }
            return None
    
    def save_incident(self, incident: Dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO incidents 
                (guid, title, status, description, link, telegram_message_id, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                incident['guid'],
                incident['title'],
                incident.get('status', ''),
                incident.get('description', ''),
                incident.get('link', ''),
                incident.get('telegram_message_id'),
                incident.get('last_updated', datetime.now())
            ))
            conn.commit()


class StatusBot:
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.db = DatabaseManager(config.DATABASE_PATH)
        self.feed_url = config.RSS_FEED_URL
        
    def _extract_status_from_text(self, text: str) -> str:
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
    
    def _format_telegram_message(self, incident: Dict) -> str:
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
            message += f"📝 *Description:* {incident['description']}\n"
        
        if incident.get('link'):
            message += f"\n🔗 [View Details]({incident['link']})\n"
        
        timestamp = incident.get('last_updated', datetime.now())
        if isinstance(timestamp, str):
            # Handle RSS date format: "Fri, 18 Jul 2025 13:27:33 GMT"
            try:
                from email.utils import parsedate_to_datetime
                timestamp = parsedate_to_datetime(timestamp)
            except:
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
        
        message += f"\n⏰ _Updated: {timestamp.strftime('%Y-%m-%d %H:%M UTC')}_"
        
        return message
    
    def send_telegram_message(self, text: str, message_id: Optional[int] = None) -> Optional[int]:
        try:
            if message_id:
                result = self.bot.edit_message_text(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    message_id=message_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                logger.info(f"Updated message {message_id}")
                return message_id
            else:
                result = self.bot.send_message(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                logger.info(f"Sent new message {result.message_id}")
                return result.message_id
        except TelegramError as e:
            logger.error(f"Failed to send/update Telegram message: {e}")
            return None
    
    def fetch_and_process_feed(self):
        logger.info("Fetching RSS feed...")
        
        try:
            feed = feedparser.parse(self.feed_url)
            
            if feed.bozo:
                logger.error(f"Error parsing feed: {feed.bozo_exception}")
                return
            
            logger.info(f"Found {len(feed.entries)} entries in feed")
            
            for entry in feed.entries:
                incident = {
                    'guid': entry.get('guid', entry.get('id', '')),
                    'title': entry.get('title', 'No title'),
                    'description': entry.get('summary', entry.get('description', '')),
                    'link': entry.get('link', ''),
                    'last_updated': entry.get('published', entry.get('updated', str(datetime.now())))
                }
                
                incident['status'] = self._extract_status_from_text(
                    incident['description'] + ' ' + incident['title']
                )
                
                existing = self.db.get_incident(incident['guid'])
                
                if existing:
                    if existing['status'] != incident['status'] or existing['title'] != incident['title']:
                        logger.info(f"Status update for incident: {incident['title']}")
                        
                        message = self._format_telegram_message(incident)
                        message_id = self.send_telegram_message(
                            message, 
                            existing.get('telegram_message_id')
                        )
                        
                        if message_id:
                            incident['telegram_message_id'] = message_id
                            self.db.save_incident(incident)
                else:
                    logger.info(f"New incident found: {incident['title']}")
                    
                    message = self._format_telegram_message(incident)
                    message_id = self.send_telegram_message(message)
                    
                    if message_id:
                        incident['telegram_message_id'] = message_id
                        self.db.save_incident(incident)
                        
        except Exception as e:
            logger.error(f"Error processing feed: {e}", exc_info=True)
    
    def run(self):
        logger.info("Starting Lovable Status Bot...")
        
        try:
            config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        self.fetch_and_process_feed()
        
        schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(self.fetch_and_process_feed)
        
        logger.info(f"Bot started. Checking feed every {config.CHECK_INTERVAL_MINUTES} minutes...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                time.sleep(60)


if __name__ == "__main__":
    bot = StatusBot()
    bot.run()