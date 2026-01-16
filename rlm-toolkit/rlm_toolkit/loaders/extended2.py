"""
Extended Loaders Part 2
=======================

Additional document loaders for comprehensive coverage.
"""

from typing import Any, Dict, List, Optional
import os

from rlm_toolkit.loaders import BaseLoader, Document


# =============================================================================
# Email/Communication Loaders
# =============================================================================

class IMAPLoader(BaseLoader):
    """Load emails via IMAP."""
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        folder: str = "INBOX",
        limit: int = 100,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.folder = folder
        self.limit = limit
    
    def load(self) -> List[Document]:
        import imaplib
        import email
        from email.policy import default
        
        mail = imaplib.IMAP4_SSL(self.host)
        mail.login(self.username, self.password)
        mail.select(self.folder)
        
        _, message_numbers = mail.search(None, "ALL")
        messages = message_numbers[0].split()[-self.limit:]
        
        docs = []
        for num in messages:
            _, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1], policy=default)
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_content()
                        break
            else:
                body = msg.get_content()
            
            content = f"Subject: {msg['Subject']}\nFrom: {msg['From']}\n\n{body}"
            docs.append(Document(content, {
                "source": f"imap://{self.host}/{self.folder}/{num.decode()}",
                "subject": msg["Subject"],
            }))
        
        mail.close()
        mail.logout()
        return docs


class OutlookLoader(BaseLoader):
    """Load emails from Outlook via Microsoft Graph."""
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        folder: str = "inbox",
        limit: int = 100,
    ):
        self.access_token = access_token or os.getenv("MS_GRAPH_ACCESS_TOKEN")
        self.folder = folder
        self.limit = limit
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{self.folder}/messages"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            params = {"$top": self.limit}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            messages = response.json().get("value", [])
            docs = []
            
            for msg in messages:
                content = f"Subject: {msg.get('subject', '')}\n\n{msg.get('body', {}).get('content', '')}"
                docs.append(Document(content, {
                    "source": f"outlook://{msg.get('id')}",
                    "subject": msg.get("subject"),
                }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")


# =============================================================================
# Media Loaders
# =============================================================================

class ImageLoader(BaseLoader):
    """Load and describe images using OCR or vision models."""
    
    def __init__(self, path: str, use_ocr: bool = True):
        self.path = path
        self.use_ocr = use_ocr
    
    def load(self) -> List[Document]:
        if self.use_ocr:
            try:
                import pytesseract
                from PIL import Image
                
                img = Image.open(self.path)
                text = pytesseract.image_to_string(img)
                
                return [Document(text, {"source": self.path, "type": "image"})]
            except ImportError:
                raise ImportError("pytesseract and pillow required")
        else:
            return [Document(f"[Image: {self.path}]", {"source": self.path})]


class AudioLoader(BaseLoader):
    """Load and transcribe audio files."""
    
    def __init__(
        self,
        path: str,
        api_key: Optional[str] = None,
    ):
        self.path = path
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def load(self) -> List[Document]:
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            with open(self.path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                )
            
            return [Document(transcription.text, {"source": self.path, "type": "audio"})]
        except ImportError:
            raise ImportError("openai required")


class VideoLoader(BaseLoader):
    """Extract audio from video and transcribe."""
    
    def __init__(
        self,
        path: str,
        api_key: Optional[str] = None,
    ):
        self.path = path
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def load(self) -> List[Document]:
        try:
            from moviepy.editor import VideoFileClip
            import tempfile
            
            # Extract audio
            video = VideoFileClip(self.path)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                audio_path = f.name
                video.audio.write_audiofile(audio_path)
            
            # Transcribe
            loader = AudioLoader(audio_path, self.api_key)
            docs = loader.load()
            
            for doc in docs:
                doc.metadata["source"] = self.path
                doc.metadata["type"] = "video"
            
            return docs
        except ImportError:
            raise ImportError("moviepy required")


class SubtitleLoader(BaseLoader):
    """Load SRT/VTT subtitle files."""
    
    def __init__(self, path: str):
        self.path = path
    
    def load(self) -> List[Document]:
        import re
        
        with open(self.path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Simple SRT parsing
        lines = []
        for block in content.split("\n\n"):
            text_lines = block.strip().split("\n")
            if len(text_lines) >= 3:
                # Skip index and timestamp
                lines.append(" ".join(text_lines[2:]))
        
        return [Document("\n".join(lines), {"source": self.path, "type": "subtitle"})]


# =============================================================================
# Database Loaders
# =============================================================================

class PostgreSQLLoader(BaseLoader):
    """Load data from PostgreSQL."""
    
    def __init__(
        self,
        connection_string: str,
        query: str,
    ):
        self.connection_string = connection_string
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            import psycopg2
            import json
            
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute(self.query)
            
            columns = [col[0] for col in cursor.description]
            docs = []
            
            for row in cursor:
                content = json.dumps(dict(zip(columns, row)), default=str)
                docs.append(Document(content, {"source": "postgresql"}))
            
            conn.close()
            return docs
        except ImportError:
            raise ImportError("psycopg2 required")


class MySQLLoader(BaseLoader):
    """Load data from MySQL."""
    
    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        query: str,
    ):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            import mysql.connector
            import json
            
            conn = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            cursor = conn.cursor()
            cursor.execute(self.query)
            
            columns = [col[0] for col in cursor.description]
            docs = []
            
            for row in cursor:
                content = json.dumps(dict(zip(columns, row)), default=str)
                docs.append(Document(content, {"source": "mysql"}))
            
            conn.close()
            return docs
        except ImportError:
            raise ImportError("mysql-connector-python required")


class SQLiteLoader(BaseLoader):
    """Load data from SQLite."""
    
    def __init__(self, path: str, query: str):
        self.path = path
        self.query = query
    
    def load(self) -> List[Document]:
        import sqlite3
        import json
        
        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()
        cursor.execute(self.query)
        
        columns = [col[0] for col in cursor.description]
        docs = []
        
        for row in cursor:
            content = json.dumps(dict(zip(columns, row)), default=str)
            docs.append(Document(content, {"source": f"sqlite://{self.path}"}))
        
        conn.close()
        return docs


class CassandraLoader(BaseLoader):
    """Load data from Apache Cassandra."""
    
    def __init__(
        self,
        hosts: List[str],
        keyspace: str,
        query: str,
    ):
        self.hosts = hosts
        self.keyspace = keyspace
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            from cassandra.cluster import Cluster
            import json
            
            cluster = Cluster(self.hosts)
            session = cluster.connect(self.keyspace)
            
            rows = session.execute(self.query)
            docs = []
            
            for row in rows:
                content = json.dumps(row._asdict(), default=str)
                docs.append(Document(content, {"source": "cassandra"}))
            
            cluster.shutdown()
            return docs
        except ImportError:
            raise ImportError("cassandra-driver required")


class Neo4jLoader(BaseLoader):
    """Load data from Neo4j graph database."""
    
    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        query: str,
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            from neo4j import GraphDatabase
            import json
            
            driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            
            with driver.session() as session:
                result = session.run(self.query)
                docs = []
                
                for record in result:
                    content = json.dumps(dict(record), default=str)
                    docs.append(Document(content, {"source": "neo4j"}))
            
            driver.close()
            return docs
        except ImportError:
            raise ImportError("neo4j required")


class ClickHouseLoader(BaseLoader):
    """Load data from ClickHouse."""
    
    def __init__(
        self,
        host: str,
        database: str,
        query: str,
        user: str = "default",
        password: str = "",
    ):
        self.host = host
        self.database = database
        self.query = query
        self.user = user
        self.password = password
    
    def load(self) -> List[Document]:
        try:
            from clickhouse_driver import Client
            import json
            
            client = Client(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            
            result = client.execute(self.query, with_column_types=True)
            rows, columns = result
            column_names = [c[0] for c in columns]
            
            docs = []
            for row in rows:
                content = json.dumps(dict(zip(column_names, row)), default=str)
                docs.append(Document(content, {"source": "clickhouse"}))
            
            return docs
        except ImportError:
            raise ImportError("clickhouse-driver required")


class DynamoDBLoader(BaseLoader):
    """Load data from AWS DynamoDB."""
    
    def __init__(
        self,
        table_name: str,
        region: str = "us-east-1",
        filter_expression: Optional[str] = None,
    ):
        self.table_name = table_name
        self.region = region
        self.filter_expression = filter_expression
    
    def load(self) -> List[Document]:
        try:
            import boto3
            import json
            
            dynamodb = boto3.resource("dynamodb", region_name=self.region)
            table = dynamodb.Table(self.table_name)
            
            if self.filter_expression:
                response = table.scan(FilterExpression=self.filter_expression)
            else:
                response = table.scan()
            
            docs = []
            for item in response.get("Items", []):
                content = json.dumps(item, default=str)
                docs.append(Document(content, {"source": f"dynamodb://{self.table_name}"}))
            
            return docs
        except ImportError:
            raise ImportError("boto3 required")


class FirestoreLoader(BaseLoader):
    """Load data from Google Firestore."""
    
    def __init__(
        self,
        collection: str,
        project: Optional[str] = None,
    ):
        self.collection = collection
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
    
    def load(self) -> List[Document]:
        try:
            from google.cloud import firestore
            import json
            
            db = firestore.Client(project=self.project)
            collection_ref = db.collection(self.collection)
            
            docs = []
            for doc in collection_ref.stream():
                content = json.dumps(doc.to_dict(), default=str)
                docs.append(Document(content, {
                    "source": f"firestore://{self.collection}/{doc.id}",
                    "id": doc.id,
                }))
            
            return docs
        except ImportError:
            raise ImportError("google-cloud-firestore required")


# =============================================================================
# API Loaders
# =============================================================================

class RESTAPILoader(BaseLoader):
    """Load data from REST APIs."""
    
    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        json_path: Optional[str] = None,
    ):
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.params = params or {}
        self.json_path = json_path
    
    def load(self) -> List[Document]:
        import requests
        import json
        
        response = requests.request(
            self.method,
            self.url,
            headers=self.headers,
            params=self.params,
            timeout=30,
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract from JSON path if specified
        if self.json_path:
            for key in self.json_path.split("."):
                data = data.get(key, data)
        
        if isinstance(data, list):
            docs = []
            for item in data:
                content = json.dumps(item) if isinstance(item, dict) else str(item)
                docs.append(Document(content, {"source": self.url}))
            return docs
        else:
            content = json.dumps(data) if isinstance(data, dict) else str(data)
            return [Document(content, {"source": self.url})]


class GraphQLLoader(BaseLoader):
    """Load data from GraphQL APIs."""
    
    def __init__(
        self,
        url: str,
        query: str,
        variables: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ):
        self.url = url
        self.query = query
        self.variables = variables or {}
        self.headers = headers or {}
    
    def load(self) -> List[Document]:
        import requests
        import json
        
        response = requests.post(
            self.url,
            json={"query": self.query, "variables": self.variables},
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        
        data = response.json().get("data", {})
        content = json.dumps(data)
        
        return [Document(content, {"source": self.url})]


class RSSLoader(BaseLoader):
    """Load articles from RSS feeds."""
    
    def __init__(self, url: str, limit: int = 10):
        self.url = url
        self.limit = limit
    
    def load(self) -> List[Document]:
        try:
            import feedparser
            
            feed = feedparser.parse(self.url)
            docs = []
            
            for entry in feed.entries[:self.limit]:
                content = f"{entry.get('title', '')}\n\n{entry.get('summary', '')}"
                docs.append(Document(content, {
                    "source": entry.get("link", self.url),
                    "title": entry.get("title"),
                    "published": entry.get("published"),
                }))
            
            return docs
        except ImportError:
            raise ImportError("feedparser required")


class ODataLoader(BaseLoader):
    """Load data from OData APIs."""
    
    def __init__(
        self,
        url: str,
        entity: str,
        headers: Optional[Dict] = None,
    ):
        self.url = url
        self.entity = entity
        self.headers = headers or {}
    
    def load(self) -> List[Document]:
        import requests
        import json
        
        full_url = f"{self.url}/{self.entity}"
        response = requests.get(full_url, headers=self.headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("value", [])
        
        docs = []
        for item in items:
            content = json.dumps(item)
            docs.append(Document(content, {"source": full_url}))
        
        return docs


# =============================================================================
# Document Management Loaders
# =============================================================================

class SharePointLoader(BaseLoader):
    """Load documents from SharePoint."""
    
    def __init__(
        self,
        site_url: str,
        library: str,
        access_token: Optional[str] = None,
    ):
        self.site_url = site_url
        self.library = library
        self.access_token = access_token or os.getenv("MS_GRAPH_ACCESS_TOKEN")
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            # Get site ID
            graph_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_url}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            site_response = requests.get(graph_url, headers=headers, timeout=30)
            site_id = site_response.json().get("id")
            
            # Get files in library
            files_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{self.library}:/children"
            files_response = requests.get(files_url, headers=headers, timeout=30)
            
            docs = []
            for item in files_response.json().get("value", []):
                if "file" in item:
                    # Download file content
                    download_url = item.get("@microsoft.graph.downloadUrl")
                    if download_url:
                        content_response = requests.get(download_url, timeout=30)
                        docs.append(Document(content_response.text, {
                            "source": f"sharepoint://{self.site_url}/{self.library}/{item['name']}",
                            "name": item["name"],
                        }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")


class ZendeskLoader(BaseLoader):
    """Load articles from Zendesk Help Center."""
    
    def __init__(
        self,
        subdomain: str,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.subdomain = subdomain
        self.email = email or os.getenv("ZENDESK_EMAIL")
        self.api_token = api_token or os.getenv("ZENDESK_API_TOKEN")
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = f"https://{self.subdomain}.zendesk.com/api/v2/help_center/articles.json"
            auth = (f"{self.email}/token", self.api_token)
            
            response = requests.get(url, auth=auth, timeout=30)
            response.raise_for_status()
            
            articles = response.json().get("articles", [])
            docs = []
            
            for article in articles:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(article.get("body", ""), "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                
                docs.append(Document(text, {
                    "source": article.get("html_url"),
                    "title": article.get("title"),
                }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")


class IntercomLoader(BaseLoader):
    """Load articles from Intercom Help Center."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("INTERCOM_API_KEY")
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = "https://api.intercom.io/articles"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            articles = response.json().get("data", [])
            docs = []
            
            for article in articles:
                content = f"{article.get('title', '')}\n\n{article.get('body', '')}"
                docs.append(Document(content, {
                    "source": article.get("url"),
                    "title": article.get("title"),
                }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")


class FreshdeskLoader(BaseLoader):
    """Load articles from Freshdesk."""
    
    def __init__(
        self,
        domain: str,
        api_key: Optional[str] = None,
    ):
        self.domain = domain
        self.api_key = api_key or os.getenv("FRESHDESK_API_KEY")
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = f"https://{self.domain}.freshdesk.com/api/v2/solutions/articles"
            auth = (self.api_key, "X")
            
            response = requests.get(url, auth=auth, timeout=30)
            response.raise_for_status()
            
            articles = response.json()
            docs = []
            
            for article in articles:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(article.get("description", ""), "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                
                docs.append(Document(text, {
                    "source": f"freshdesk://{article.get('id')}",
                    "title": article.get("title"),
                }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")
