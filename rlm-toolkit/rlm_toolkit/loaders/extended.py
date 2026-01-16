"""
Extended Document Loaders
=========================

Additional document loaders for maximum compatibility.
"""

from typing import Any, Dict, List, Optional
import os

from rlm_toolkit.loaders import BaseLoader, Document


# =============================================================================
# CRM/Sales Loaders
# =============================================================================

class HubSpotLoader(BaseLoader):
    """Load data from HubSpot CRM."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        object_type: str = "contacts",
    ):
        self.api_key = api_key or os.getenv("HUBSPOT_API_KEY")
        self.object_type = object_type
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = f"https://api.hubapi.com/crm/v3/objects/{self.object_type}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            docs = []
            
            for item in data.get("results", []):
                import json
                content = json.dumps(item.get("properties", {}))
                docs.append(Document(content, {
                    "source": f"hubspot://{self.object_type}/{item.get('id')}",
                    "id": item.get("id"),
                }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")


class SalesforceLoader(BaseLoader):
    """Load data from Salesforce."""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        security_token: Optional[str] = None,
        query: str = "SELECT Id, Name FROM Account LIMIT 100",
    ):
        self.username = username or os.getenv("SALESFORCE_USERNAME")
        self.password = password or os.getenv("SALESFORCE_PASSWORD")
        self.security_token = security_token or os.getenv("SALESFORCE_SECURITY_TOKEN")
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            from simple_salesforce import Salesforce
            import json
            
            sf = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
            )
            
            results = sf.query(self.query)
            docs = []
            
            for record in results.get("records", []):
                content = json.dumps(record)
                docs.append(Document(content, {
                    "source": f"salesforce://{record.get('Id')}",
                }))
            
            return docs
        except ImportError:
            raise ImportError("simple-salesforce required")


# =============================================================================
# Project Management Loaders
# =============================================================================

class JiraLoader(BaseLoader):
    """Load issues from Jira."""
    
    def __init__(
        self,
        url: str,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        jql: str = "project = PROJ",
    ):
        self.url = url
        self.username = username or os.getenv("JIRA_USERNAME")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")
        self.jql = jql
    
    def load(self) -> List[Document]:
        try:
            from jira import JIRA
            
            jira = JIRA(
                server=self.url,
                basic_auth=(self.username, self.api_token),
            )
            
            issues = jira.search_issues(self.jql)
            docs = []
            
            for issue in issues:
                content = f"[{issue.key}] {issue.fields.summary}\n\n{issue.fields.description or ''}"
                docs.append(Document(content, {
                    "source": f"{self.url}/browse/{issue.key}",
                    "key": issue.key,
                    "status": str(issue.fields.status),
                }))
            
            return docs
        except ImportError:
            raise ImportError("jira required. pip install jira")


class AsanaLoader(BaseLoader):
    """Load tasks from Asana."""
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        project_gid: Optional[str] = None,
    ):
        self.api_token = api_token or os.getenv("ASANA_API_TOKEN")
        self.project_gid = project_gid
    
    def load(self) -> List[Document]:
        try:
            import asana
            
            client = asana.Client.access_token(self.api_token)
            tasks = client.tasks.get_tasks_for_project(self.project_gid)
            
            docs = []
            for task in tasks:
                task_detail = client.tasks.get_task(task["gid"])
                content = f"{task_detail['name']}\n\n{task_detail.get('notes', '')}"
                docs.append(Document(content, {
                    "source": f"asana://task/{task['gid']}",
                    "gid": task["gid"],
                }))
            
            return docs
        except ImportError:
            raise ImportError("asana required")


class TrelloLoader(BaseLoader):
    """Load cards from Trello."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_token: Optional[str] = None,
        board_id: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("TRELLO_API_KEY")
        self.api_token = api_token or os.getenv("TRELLO_API_TOKEN")
        self.board_id = board_id
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = f"https://api.trello.com/1/boards/{self.board_id}/cards"
            params = {"key": self.api_key, "token": self.api_token}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            cards = response.json()
            docs = []
            
            for card in cards:
                content = f"{card['name']}\n\n{card.get('desc', '')}"
                docs.append(Document(content, {
                    "source": card.get("url", f"trello://card/{card['id']}"),
                    "id": card["id"],
                }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")


class LinearLoader(BaseLoader):
    """Load issues from Linear."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        team_id: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        self.team_id = team_id
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = "https://api.linear.app/graphql"
            headers = {"Authorization": self.api_key}
            
            query = """
            query {
                issues(first: 100) {
                    nodes {
                        id
                        title
                        description
                        state { name }
                    }
                }
            }
            """
            
            response = requests.post(url, json={"query": query}, headers=headers, timeout=30)
            response.raise_for_status()
            
            issues = response.json().get("data", {}).get("issues", {}).get("nodes", [])
            docs = []
            
            for issue in issues:
                content = f"{issue['title']}\n\n{issue.get('description', '')}"
                docs.append(Document(content, {
                    "source": f"linear://issue/{issue['id']}",
                    "state": issue.get("state", {}).get("name", ""),
                }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")


# =============================================================================
# Knowledge Base Loaders
# =============================================================================

class AirtableLoader(BaseLoader):
    """Load records from Airtable."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_id: Optional[str] = None,
        table_name: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("AIRTABLE_API_KEY")
        self.base_id = base_id
        self.table_name = table_name
    
    def load(self) -> List[Document]:
        try:
            from pyairtable import Table
            import json
            
            table = Table(self.api_key, self.base_id, self.table_name)
            records = table.all()
            
            docs = []
            for record in records:
                content = json.dumps(record.get("fields", {}))
                docs.append(Document(content, {
                    "source": f"airtable://{self.base_id}/{self.table_name}/{record['id']}",
                    "id": record["id"],
                }))
            
            return docs
        except ImportError:
            raise ImportError("pyairtable required")


class GoogleDocsLoader(BaseLoader):
    """Load Google Docs."""
    
    def __init__(
        self,
        document_id: str,
        credentials_path: Optional[str] = None,
    ):
        self.document_id = document_id
        self.credentials_path = credentials_path
    
    def load(self) -> List[Document]:
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/documents.readonly"],
            )
            
            service = build("docs", "v1", credentials=credentials)
            doc = service.documents().get(documentId=self.document_id).execute()
            
            content_parts = []
            for element in doc.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for elem in element["paragraph"].get("elements", []):
                        if "textRun" in elem:
                            content_parts.append(elem["textRun"].get("content", ""))
            
            content = "".join(content_parts)
            return [Document(content, {"source": f"gdocs://{self.document_id}"})]
        except ImportError:
            raise ImportError("google-api-python-client required")


class GoogleSheetsLoader(BaseLoader):
    """Load Google Sheets."""
    
    def __init__(
        self,
        spreadsheet_id: str,
        range_name: str = "Sheet1",
        credentials_path: Optional[str] = None,
    ):
        self.spreadsheet_id = spreadsheet_id
        self.range_name = range_name
        self.credentials_path = credentials_path
    
    def load(self) -> List[Document]:
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            
            service = build("sheets", "v4", credentials=credentials)
            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=self.range_name,
            ).execute()
            
            values = result.get("values", [])
            if not values:
                return []
            
            headers = values[0]
            docs = []
            
            for i, row in enumerate(values[1:], 1):
                content = " | ".join([f"{h}: {v}" for h, v in zip(headers, row)])
                docs.append(Document(content, {
                    "source": f"gsheets://{self.spreadsheet_id}/{self.range_name}",
                    "row": i,
                }))
            
            return docs
        except ImportError:
            raise ImportError("google-api-python-client required")


class DropboxLoader(BaseLoader):
    """Load files from Dropbox."""
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        folder_path: str = "",
    ):
        self.access_token = access_token or os.getenv("DROPBOX_ACCESS_TOKEN")
        self.folder_path = folder_path
    
    def load(self) -> List[Document]:
        try:
            import dropbox
            
            dbx = dropbox.Dropbox(self.access_token)
            result = dbx.files_list_folder(self.folder_path)
            
            docs = []
            for entry in result.entries:
                if hasattr(entry, "path_lower") and entry.path_lower.endswith(".txt"):
                    _, response = dbx.files_download(entry.path_lower)
                    content = response.content.decode("utf-8")
                    docs.append(Document(content, {
                        "source": f"dropbox://{entry.path_lower}",
                        "name": entry.name,
                    }))
            
            return docs
        except ImportError:
            raise ImportError("dropbox required")


class OneDriveLoader(BaseLoader):
    """Load files from OneDrive."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        folder_path: str = "/",
    ):
        self.client_id = client_id or os.getenv("ONEDRIVE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ONEDRIVE_CLIENT_SECRET")
        self.folder_path = folder_path
    
    def load(self) -> List[Document]:
        # Simplified implementation - would need full OAuth flow
        raise NotImplementedError("OneDrive requires OAuth authentication flow")


class BoxLoader(BaseLoader):
    """Load files from Box."""
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        folder_id: str = "0",
    ):
        self.access_token = access_token or os.getenv("BOX_ACCESS_TOKEN")
        self.folder_id = folder_id
    
    def load(self) -> List[Document]:
        try:
            from boxsdk import OAuth2, Client
            
            oauth = OAuth2(
                client_id="",
                client_secret="",
                access_token=self.access_token,
            )
            client = Client(oauth)
            
            folder = client.folder(self.folder_id)
            items = folder.get_items()
            
            docs = []
            for item in items:
                if item.type == "file" and item.name.endswith(".txt"):
                    content = item.content().decode("utf-8")
                    docs.append(Document(content, {
                        "source": f"box://file/{item.id}",
                        "name": item.name,
                    }))
            
            return docs
        except ImportError:
            raise ImportError("boxsdk required")


# =============================================================================
# Communication Loaders
# =============================================================================

class DiscordLoader(BaseLoader):
    """Load messages from Discord channel."""
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None,
        limit: int = 100,
    ):
        self.bot_token = bot_token or os.getenv("DISCORD_BOT_TOKEN")
        self.channel_id = channel_id
        self.limit = limit
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
            headers = {"Authorization": f"Bot {self.bot_token}"}
            params = {"limit": self.limit}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            messages = response.json()
            content = "\n".join([
                f"[{m.get('author', {}).get('username', 'Unknown')}]: {m.get('content', '')}"
                for m in messages
            ])
            
            return [Document(content, {"source": f"discord://channel/{self.channel_id}"})]
        except ImportError:
            raise ImportError("requests required")


class TelegramLoader(BaseLoader):
    """Load messages from Telegram channel."""
    
    def __init__(
        self,
        api_id: Optional[str] = None,
        api_hash: Optional[str] = None,
        channel_username: Optional[str] = None,
        limit: int = 100,
    ):
        self.api_id = api_id or os.getenv("TELEGRAM_API_ID")
        self.api_hash = api_hash or os.getenv("TELEGRAM_API_HASH")
        self.channel_username = channel_username
        self.limit = limit
    
    def load(self) -> List[Document]:
        try:
            from telethon.sync import TelegramClient
            
            with TelegramClient("session", self.api_id, self.api_hash) as client:
                messages = client.get_messages(self.channel_username, limit=self.limit)
                content = "\n".join([m.text or "" for m in messages if m.text])
            
            return [Document(content, {"source": f"telegram://{self.channel_username}"})]
        except ImportError:
            raise ImportError("telethon required")


class TeamsLoader(BaseLoader):
    """Load messages from Microsoft Teams."""
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        team_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ):
        self.access_token = access_token or os.getenv("TEAMS_ACCESS_TOKEN")
        self.team_id = team_id
        self.channel_id = channel_id
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            url = f"https://graph.microsoft.com/v1.0/teams/{self.team_id}/channels/{self.channel_id}/messages"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            messages = response.json().get("value", [])
            content = "\n".join([m.get("body", {}).get("content", "") for m in messages])
            
            return [Document(content, {"source": f"teams://{self.team_id}/{self.channel_id}"})]
        except ImportError:
            raise ImportError("requests required")


# =============================================================================
# Data/Analytics Loaders
# =============================================================================

class BigQueryLoader(BaseLoader):
    """Load data from Google BigQuery."""
    
    def __init__(
        self,
        project: Optional[str] = None,
        query: Optional[str] = None,
    ):
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            from google.cloud import bigquery
            import json
            
            client = bigquery.Client(project=self.project)
            results = client.query(self.query).result()
            
            docs = []
            for row in results:
                content = json.dumps(dict(row))
                docs.append(Document(content, {"source": "bigquery"}))
            
            return docs
        except ImportError:
            raise ImportError("google-cloud-bigquery required")


class SnowflakeLoader(BaseLoader):
    """Load data from Snowflake."""
    
    def __init__(
        self,
        account: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        query: Optional[str] = None,
    ):
        self.account = account or os.getenv("SNOWFLAKE_ACCOUNT")
        self.user = user or os.getenv("SNOWFLAKE_USER")
        self.password = password or os.getenv("SNOWFLAKE_PASSWORD")
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            import snowflake.connector
            import json
            
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
            )
            
            cursor = conn.cursor()
            cursor.execute(self.query)
            
            columns = [col[0] for col in cursor.description]
            docs = []
            
            for row in cursor:
                content = json.dumps(dict(zip(columns, row)))
                docs.append(Document(content, {"source": "snowflake"}))
            
            return docs
        except ImportError:
            raise ImportError("snowflake-connector-python required")


class RedshiftLoader(BaseLoader):
    """Load data from AWS Redshift."""
    
    def __init__(
        self,
        host: Optional[str] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        query: Optional[str] = None,
    ):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.query = query
    
    def load(self) -> List[Document]:
        try:
            import psycopg2
            import json
            
            conn = psycopg2.connect(
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
                content = json.dumps(dict(zip(columns, row)))
                docs.append(Document(content, {"source": "redshift"}))
            
            return docs
        except ImportError:
            raise ImportError("psycopg2 required")


# =============================================================================
# Research/Academic Loaders
# =============================================================================

class ArxivLoader(BaseLoader):
    """Load papers from arXiv."""
    
    def __init__(
        self,
        query: str,
        max_results: int = 10,
    ):
        self.query = query
        self.max_results = max_results
    
    def load(self) -> List[Document]:
        try:
            import arxiv
            
            search = arxiv.Search(
                query=self.query,
                max_results=self.max_results,
            )
            
            docs = []
            for result in search.results():
                content = f"{result.title}\n\n{result.summary}"
                docs.append(Document(content, {
                    "source": result.entry_id,
                    "title": result.title,
                    "authors": [a.name for a in result.authors],
                    "published": str(result.published),
                }))
            
            return docs
        except ImportError:
            raise ImportError("arxiv required. pip install arxiv")


class PubMedLoader(BaseLoader):
    """Load papers from PubMed."""
    
    def __init__(
        self,
        query: str,
        max_results: int = 10,
    ):
        self.query = query
        self.max_results = max_results
    
    def load(self) -> List[Document]:
        try:
            from Bio import Entrez
            
            Entrez.email = os.getenv("PUBMED_EMAIL", "user@example.com")
            
            handle = Entrez.esearch(db="pubmed", term=self.query, retmax=self.max_results)
            record = Entrez.read(handle)
            
            ids = record.get("IdList", [])
            
            docs = []
            for pmid in ids:
                handle = Entrez.efetch(db="pubmed", id=pmid, rettype="abstract", retmode="text")
                abstract = handle.read()
                docs.append(Document(abstract, {"source": f"pubmed://{pmid}"}))
            
            return docs
        except ImportError:
            raise ImportError("biopython required")


class WikipediaLoader(BaseLoader):
    """Load pages from Wikipedia."""
    
    def __init__(
        self,
        query: str,
        lang: str = "en",
    ):
        self.query = query
        self.lang = lang
    
    def load(self) -> List[Document]:
        try:
            import wikipedia
            
            wikipedia.set_lang(self.lang)
            
            try:
                page = wikipedia.page(self.query)
                return [Document(page.content, {
                    "source": page.url,
                    "title": page.title,
                })]
            except wikipedia.exceptions.DisambiguationError as e:
                # Return first option
                page = wikipedia.page(e.options[0])
                return [Document(page.content, {
                    "source": page.url,
                    "title": page.title,
                })]
        except ImportError:
            raise ImportError("wikipedia required. pip install wikipedia")


# =============================================================================
# Git/Code Loaders
# =============================================================================

class GitLoader(BaseLoader):
    """Load files from a Git repository."""
    
    def __init__(
        self,
        repo_path: str,
        branch: str = "main",
        file_filter: Optional[str] = None,
    ):
        self.repo_path = repo_path
        self.branch = branch
        self.file_filter = file_filter
    
    def load(self) -> List[Document]:
        try:
            import git
            from pathlib import Path
            
            repo = git.Repo(self.repo_path)
            repo.git.checkout(self.branch)
            
            docs = []
            for file_path in Path(self.repo_path).rglob("*"):
                if file_path.is_file():
                    if self.file_filter and not str(file_path).endswith(self.file_filter):
                        continue
                    
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        docs.append(Document(content, {
                            "source": str(file_path),
                            "branch": self.branch,
                        }))
                    except Exception:
                        pass
            
            return docs
        except ImportError:
            raise ImportError("gitpython required")


class GitLabLoader(BaseLoader):
    """Load files from GitLab repository."""
    
    def __init__(
        self,
        url: str,
        project_id: str,
        private_token: Optional[str] = None,
        branch: str = "main",
    ):
        self.url = url
        self.project_id = project_id
        self.private_token = private_token or os.getenv("GITLAB_PRIVATE_TOKEN")
        self.branch = branch
    
    def load(self) -> List[Document]:
        try:
            import gitlab
            
            gl = gitlab.Gitlab(self.url, private_token=self.private_token)
            project = gl.projects.get(self.project_id)
            
            docs = []
            items = project.repository_tree(ref=self.branch, recursive=True)
            
            for item in items:
                if item["type"] == "blob":
                    try:
                        file_content = project.files.get(
                            file_path=item["path"],
                            ref=self.branch,
                        )
                        content = file_content.decode().decode("utf-8")
                        docs.append(Document(content, {
                            "source": f"{self.url}/{self.project_id}/-/blob/{self.branch}/{item['path']}",
                            "path": item["path"],
                        }))
                    except Exception:
                        pass
            
            return docs
        except ImportError:
            raise ImportError("python-gitlab required")


class BitbucketLoader(BaseLoader):
    """Load files from Bitbucket repository."""
    
    def __init__(
        self,
        workspace: str,
        repo_slug: str,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
        branch: str = "main",
    ):
        self.workspace = workspace
        self.repo_slug = repo_slug
        self.username = username or os.getenv("BITBUCKET_USERNAME")
        self.app_password = app_password or os.getenv("BITBUCKET_APP_PASSWORD")
        self.branch = branch
    
    def load(self) -> List[Document]:
        try:
            import requests
            
            base_url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{self.repo_slug}"
            auth = (self.username, self.app_password)
            
            # Get file list
            response = requests.get(
                f"{base_url}/src/{self.branch}/",
                auth=auth,
                timeout=30,
            )
            response.raise_for_status()
            
            # Simplified - would need recursive directory traversal
            docs = []
            for item in response.json().get("values", []):
                if item["type"] == "commit_file":
                    file_response = requests.get(
                        item["links"]["self"]["href"],
                        auth=auth,
                        timeout=30,
                    )
                    docs.append(Document(file_response.text, {
                        "source": item["links"]["html"]["href"],
                        "path": item["path"],
                    }))
            
            return docs
        except ImportError:
            raise ImportError("requests required")
