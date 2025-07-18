#!/usr/bin/env python3
import sys
import os
# Add the virtual environment path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'venv/lib/python3.13/site-packages'))
import feedparser
import sqlite3
import logging
import asyncio
import re
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
    
    def _extract_components(self, html_text: str) -> List[str]:
        """Extract affected components from HTML"""
        components = []
        if not html_text:
            return components
        
        # Look for list items within the affected components section
        component_pattern = r'<li>([^<]+)\s*\([^)]+\)</li>'
        matches = re.findall(component_pattern, html_text)
        
        return [match.strip() for match in matches]
    
    def _clean_html(self, html_text: str) -> str:
        """Convert HTML to clean text for Telegram"""
        if not html_text:
            return ""
        
        # First extract components before cleaning
        components = self._extract_components(html_text)
        
        # Remove the affected components section entirely
        text = re.sub(r'<b>Affected components</b>.*?</ul>', '', html_text, flags=re.DOTALL)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Replace HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove redundant status prefix if it exists
        status_pattern = r'^Status:\s*(Resolved|Identified|Monitoring|Investigating)\s*'
        text = re.sub(status_pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip(), components
    
    def _format_telegram_message(self, incident: Dict) -> str:
        status_emoji = {
            'Resolved': '✅',
            'Identified': '🔍',
            'Monitoring': '👀',
            'Investigating': '🔎',
            'Unknown': '❓'
        }
        
        emoji = status_emoji.get(incident['status'], '❓')
        
        # Determine severity based on title/description
        severity = "🔴 High"
        if "intermittent" in incident['title'].lower() or "some" in incident['title'].lower():
            severity = "🟡 Medium"
        elif incident['status'] == 'Resolved':
            severity = "🟢 Resolved"
        
        message = f"🚨 *INCIDENT: {incident['title']}*\n\n"
        message += f"{emoji} *Status:* {incident['status']}\n"
        if incident['status'] != 'Resolved':
            message += f"⚠️ *Impact:* {severity}\n"
        
        if incident.get('description'):
            clean_description, components = self._clean_html(incident['description'])
            if clean_description:
                message += f"📝 *Description:* {clean_description}\n"
            
            if components:
                message += f"\n🛠️ *Affected Components:*\n"
                for component in components:
                    message += f"  • {component}\n"
        
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
    
    async def send_telegram_message(self, text: str, message_id: Optional[int] = None) -> Optional[int]:
        try:
            if message_id:
                result = await self.bot.edit_message_text(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    message_id=message_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                logger.info(f"Updated message {message_id}")
                return message_id
            else:
                result = await self.bot.send_message(
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
    
    async def fetch_and_process_feed(self):
        logger.info("Fetching RSS feed...")
        
        try:
            feed = feedparser.parse(self.feed_url)
            
            if feed.bozo:
                logger.error(f"Error parsing feed: {feed.bozo_exception}")
                return
            
            logger.info(f"Found {len(feed.entries)} entries in feed")
            
            # Sort entries by date (newest first) to process in correct order
            entries = sorted(feed.entries, key=lambda x: x.get('published', ''), reverse=True)
            
            for entry in entries:
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
                        message_id = await self.send_telegram_message(
                            message, 
                            existing.get('telegram_message_id')
                        )
                        
                        if message_id:
                            incident['telegram_message_id'] = message_id
                            self.db.save_incident(incident)
                else:
                    # Skip resolved incidents if configured
                    if config.ONLY_ACTIVE_INCIDENTS and incident['status'] == 'Resolved':
                        logger.info(f"Skipping resolved incident: {incident['title']}")
                        continue
                    
                    # Skip old incidents on initial load
                    if config.INITIAL_LOAD_DAYS > 0:
                        try:
                            from email.utils import parsedate_to_datetime
                            incident_date = parsedate_to_datetime(incident['last_updated'])
                            days_old = (datetime.now(incident_date.tzinfo) - incident_date).days
                            if days_old > config.INITIAL_LOAD_DAYS:
                                logger.info(f"Skipping old incident ({days_old} days): {incident['title']}")
                                continue
                        except:
                            pass
                    
                    logger.info(f"New incident found: {incident['title']} - Status: {incident['status']}")
                    
                    message = self._format_telegram_message(incident)
                    message_id = await self.send_telegram_message(message)
                    
                    if message_id:
                        incident['telegram_message_id'] = message_id
                        self.db.save_incident(incident)
                        
        except Exception as e:
            logger.error(f"Error processing feed: {e}", exc_info=True)
    
    async def run_once(self):
        """Run the bot once for testing"""
        await self.fetch_and_process_feed()
    
    async def run_forever(self):
        """Run the bot continuously"""
        logger.info("Starting Lovable Status Bot...")
        
        try:
            config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return
        
        # Initial run
        await self.fetch_and_process_feed()
        
        logger.info(f"Bot started. Checking feed every {config.CHECK_INTERVAL_MINUTES} minutes...")
        
        # Run periodically
        while True:
            await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)
            await self.fetch_and_process_feed()


async def main():
    bot = StatusBot()
    try:
        await bot.run_forever()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())