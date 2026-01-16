"""
Extended Tools
==============

Additional tools for enhanced agent capabilities.
"""

from typing import Any, Dict, List, Optional
import os

from rlm_toolkit.tools import Tool


# =============================================================================
# Weather Tools
# =============================================================================

class OpenWeatherMapTool(Tool):
    """Get weather information."""
    
    name = "weather"
    description = "Get current weather for a location."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENWEATHERMAP_API_KEY")
    
    def run(self, location: str) -> str:
        try:
            import requests
            
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": location, "appid": self.api_key, "units": "metric"}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return (
                f"Weather in {location}: {data['weather'][0]['description']}, "
                f"Temperature: {data['main']['temp']}°C, "
                f"Humidity: {data['main']['humidity']}%"
            )
        except Exception as e:
            return f"Error: {e}"


# =============================================================================
# Translation Tools
# =============================================================================

class GoogleTranslateTool(Tool):
    """Translate text using Google Translate."""
    
    name = "translate"
    description = "Translate text to another language. Format: 'target_lang|text'"
    
    def run(self, input: str) -> str:
        try:
            from googletrans import Translator
            
            if "|" in input:
                target_lang, text = input.split("|", 1)
            else:
                target_lang, text = "en", input
            
            translator = Translator()
            result = translator.translate(text, dest=target_lang)
            
            return result.text
        except ImportError:
            raise ImportError("googletrans required")


class DeepLTool(Tool):
    """Translate using DeepL API."""
    
    name = "deepl_translate"
    description = "High-quality translation using DeepL."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPL_API_KEY")
    
    def run(self, input: str) -> str:
        try:
            import deepl
            
            if "|" in input:
                target_lang, text = input.split("|", 1)
            else:
                target_lang, text = "EN", input
            
            translator = deepl.Translator(self.api_key)
            result = translator.translate_text(text, target_lang=target_lang)
            
            return result.text
        except ImportError:
            raise ImportError("deepl required")


# =============================================================================
# Image Tools
# =============================================================================

class DallETool(Tool):
    """Generate images using DALL-E."""
    
    name = "dalle"
    description = "Generate an image from a text description."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def run(self, prompt: str) -> str:
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                n=1,
            )
            
            return f"Image URL: {response.data[0].url}"
        except ImportError:
            raise ImportError("openai required")


class StableDiffusionTool(Tool):
    """Generate images using Stable Diffusion via Replicate."""
    
    name = "stable_diffusion"
    description = "Generate images using Stable Diffusion."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("REPLICATE_API_TOKEN")
    
    def run(self, prompt: str) -> str:
        try:
            import replicate
            
            output = replicate.run(
                "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
                input={"prompt": prompt},
            )
            
            return f"Image URL: {output[0]}"
        except ImportError:
            raise ImportError("replicate required")


# =============================================================================
# Audio Tools
# =============================================================================

class WhisperTool(Tool):
    """Transcribe audio using Whisper."""
    
    name = "whisper"
    description = "Transcribe audio to text."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def run(self, audio_path: str) -> str:
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            with open(audio_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                )
            
            return transcription.text
        except ImportError:
            raise ImportError("openai required")


class TextToSpeechTool(Tool):
    """Convert text to speech."""
    
    name = "tts"
    description = "Convert text to speech audio."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def run(self, text: str) -> str:
        try:
            from openai import OpenAI
            from pathlib import Path
            
            client = OpenAI(api_key=self.api_key)
            
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )
            
            output_path = Path("output.mp3")
            response.stream_to_file(output_path)
            
            return f"Audio saved to: {output_path}"
        except ImportError:
            raise ImportError("openai required")


# =============================================================================
# Email Tools
# =============================================================================

class GmailTool(Tool):
    """Send emails via Gmail."""
    
    name = "gmail"
    description = "Send an email. Format: 'to|subject|body'"
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
    
    def run(self, input: str) -> str:
        parts = input.split("|", 2)
        if len(parts) < 3:
            return "Invalid format. Use: to|subject|body"
        
        to, subject, body = parts
        
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            import base64
            from email.mime.text import MIMEText
            
            creds = Credentials.from_authorized_user_file(self.credentials_path)
            service = build("gmail", "v1", credentials=creds)
            
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()
            
            return f"Email sent to {to}"
        except ImportError:
            raise ImportError("google-api-python-client required")


class SendGridTool(Tool):
    """Send emails via SendGrid."""
    
    name = "sendgrid"
    description = "Send an email via SendGrid. Format: 'to|subject|body'"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SENDGRID_API_KEY")
    
    def run(self, input: str) -> str:
        parts = input.split("|", 2)
        if len(parts) < 3:
            return "Invalid format. Use: to|subject|body"
        
        to, subject, body = parts
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email="noreply@example.com",
                to_emails=to,
                subject=subject,
                plain_text_content=body,
            )
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            return f"Email sent to {to}, status: {response.status_code}"
        except ImportError:
            raise ImportError("sendgrid required")


# =============================================================================
# Calendar Tools
# =============================================================================

class GoogleCalendarTool(Tool):
    """Interact with Google Calendar."""
    
    name = "calendar"
    description = "Get upcoming calendar events."
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
    
    def run(self, input: str) -> str:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            import datetime
            
            creds = Credentials.from_authorized_user_file(self.credentials_path)
            service = build("calendar", "v3", credentials=creds)
            
            now = datetime.datetime.utcnow().isoformat() + "Z"
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            events = events_result.get("items", [])
            
            if not events:
                return "No upcoming events found."
            
            output = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                output.append(f"- {start}: {event['summary']}")
            
            return "\n".join(output)
        except ImportError:
            raise ImportError("google-api-python-client required")


# =============================================================================
# News Tools
# =============================================================================

class NewsAPITool(Tool):
    """Get news articles."""
    
    name = "news"
    description = "Get latest news on a topic."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
    
    def run(self, query: str) -> str:
        try:
            from newsapi import NewsApiClient
            
            newsapi = NewsApiClient(api_key=self.api_key)
            articles = newsapi.get_everything(q=query, language="en", page_size=5)
            
            output = []
            for article in articles.get("articles", []):
                output.append(f"- {article['title']}: {article['description'][:100]}...")
            
            return "\n".join(output) if output else "No news found."
        except ImportError:
            raise ImportError("newsapi-python required")


# =============================================================================
# Social Media Tools
# =============================================================================

class TwitterSearchTool(Tool):
    """Search Twitter/X."""
    
    name = "twitter_search"
    description = "Search for tweets on a topic."
    
    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
    
    def run(self, query: str) -> str:
        try:
            import tweepy
            
            client = tweepy.Client(bearer_token=self.bearer_token)
            tweets = client.search_recent_tweets(query=query, max_results=5)
            
            output = []
            for tweet in tweets.data or []:
                output.append(f"- {tweet.text[:100]}...")
            
            return "\n".join(output) if output else "No tweets found."
        except ImportError:
            raise ImportError("tweepy required")


# =============================================================================
# Finance Tools
# =============================================================================

class YahooFinanceTool(Tool):
    """Get stock information."""
    
    name = "stock"
    description = "Get stock price and info for a ticker symbol."
    
    def run(self, ticker: str) -> str:
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return (
                f"{info.get('shortName', ticker)}: "
                f"Price: ${info.get('currentPrice', 'N/A')}, "
                f"Market Cap: ${info.get('marketCap', 'N/A'):,}, "
                f"52w Range: ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}"
            )
        except ImportError:
            raise ImportError("yfinance required")


class CryptoTool(Tool):
    """Get cryptocurrency prices."""
    
    name = "crypto"
    description = "Get cryptocurrency price."
    
    def run(self, symbol: str) -> str:
        try:
            import requests
            
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": symbol.lower(), "vs_currencies": "usd", "include_24hr_change": "true"}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if symbol.lower() in data:
                info = data[symbol.lower()]
                return f"{symbol.upper()}: ${info['usd']}, 24h change: {info.get('usd_24h_change', 0):.2f}%"
            
            return f"Cryptocurrency {symbol} not found."
        except Exception as e:
            return f"Error: {e}"


# =============================================================================
# Utility Tools
# =============================================================================

class DateTimeTool(Tool):
    """Get current date and time."""
    
    name = "datetime"
    description = "Get current date, time, or timezone info."
    
    def run(self, input: str) -> str:
        from datetime import datetime
        import pytz
        
        if input.strip():
            try:
                tz = pytz.timezone(input)
                now = datetime.now(tz)
                return f"Current time in {input}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            except Exception:
                return f"Invalid timezone: {input}"
        
        now = datetime.now()
        return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


class UUIDTool(Tool):
    """Generate UUIDs."""
    
    name = "uuid"
    description = "Generate a unique identifier."
    
    def run(self, input: str) -> str:
        import uuid
        return str(uuid.uuid4())


class HashTool(Tool):
    """Generate hashes."""
    
    name = "hash"
    description = "Generate hash of text. Format: 'algorithm|text' (md5, sha256, etc.)"
    
    def run(self, input: str) -> str:
        import hashlib
        
        if "|" in input:
            algo, text = input.split("|", 1)
        else:
            algo, text = "sha256", input
        
        try:
            h = hashlib.new(algo)
            h.update(text.encode())
            return h.hexdigest()
        except ValueError:
            return f"Unknown algorithm: {algo}"


class Base64Tool(Tool):
    """Encode/decode base64."""
    
    name = "base64"
    description = "Encode or decode base64. Format: 'encode|text' or 'decode|text'"
    
    def run(self, input: str) -> str:
        import base64
        
        if "|" in input:
            action, text = input.split("|", 1)
        else:
            action, text = "encode", input
        
        if action == "encode":
            return base64.b64encode(text.encode()).decode()
        elif action == "decode":
            return base64.b64decode(text).decode()
        else:
            return f"Unknown action: {action}. Use 'encode' or 'decode'."


class JSONTool(Tool):
    """Parse and format JSON."""
    
    name = "json"
    description = "Parse, validate, or format JSON."
    
    def run(self, input: str) -> str:
        import json
        
        try:
            data = json.loads(input)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"
