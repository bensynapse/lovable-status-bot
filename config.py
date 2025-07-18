import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
    RSS_FEED_URL = os.getenv('RSS_FEED_URL', 'https://status.lovable.dev/feed.rss')
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '5'))
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'lovable_status.db')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ONLY_ACTIVE_INCIDENTS = os.getenv('ONLY_ACTIVE_INCIDENTS', 'true').lower() == 'true'
    INITIAL_LOAD_DAYS = int(os.getenv('INITIAL_LOAD_DAYS', '7'))
    
    @classmethod
    def validate(cls):
        required_fields = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHANNEL_ID']
        missing = []
        
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True

config = Config()