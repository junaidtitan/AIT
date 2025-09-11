from pydantic import BaseSettings
from dotenv import load_dotenv
import os
load_dotenv()
class Settings(BaseSettings):
    APPROVAL_MODE: str = os.getenv("APPROVAL_MODE","manual")
    DATA_DIR: str = os.getenv("DATA_DIR","./starter/data")
    RSS_FEEDS: str = os.getenv("RSS_FEEDS","")
    SLACK_BOT_TOKEN: str | None = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET: str | None = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_CHANNEL_ID: str | None = os.getenv("SLACK_CHANNEL_ID")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID: str | None = os.getenv("ELEVENLABS_VOICE_ID")
    YOUTUBE_CLIENT_SECRETS: str | None = os.getenv("YOUTUBE_CLIENT_SECRETS")
    YOUTUBE_TOKEN_JSON: str | None = os.getenv("YOUTUBE_TOKEN_JSON")
    YOUTUBE_UPLOAD: bool = os.getenv("YOUTUBE_UPLOAD","true").lower()=="true"
    YOUTUBE_REFRESH_TOKEN: str | None = os.getenv("YOUTUBE_REFRESH_TOKEN")
    DB_URL: str | None = os.getenv("DB_URL")
    PUBLISH_HOUR_PT: int = int(os.getenv("PUBLISH_HOUR_PT","18"))
    TIMEZONE: str = os.getenv("TIMEZONE","America/Los_Angeles")
settings = Settings()
