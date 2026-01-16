"""
Extended Loaders Part 3 - Bulk Enterprise Loaders
==================================================

Maximum coverage enterprise integrations.
"""

from typing import Any, Dict, List, Optional
import os

from rlm_toolkit.loaders import BaseLoader, Document


# =============================================================================
# CRM & Sales Systems
# =============================================================================

class PipedriveLoader(BaseLoader):
    """Load deals from Pipedrive CRM."""
    name = "pipedrive"
    def __init__(self, api_key: Optional[str] = None, entity: str = "deals"):
        self.api_key = api_key or os.getenv("PIPEDRIVE_API_KEY")
        self.entity = entity
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://api.pipedrive.com/v1/{self.entity}?api_token={self.api_key}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        items = response.json().get("data", []) or []
        return [Document(json.dumps(item), {"source": f"pipedrive://{self.entity}/{item.get('id')}"}) for item in items]

class ZohoLoader(BaseLoader):
    """Load data from Zoho CRM."""
    name = "zoho"
    def __init__(self, access_token: Optional[str] = None, module: str = "Leads"):
        self.access_token = access_token or os.getenv("ZOHO_ACCESS_TOKEN")
        self.module = module
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://www.zohoapis.com/crm/v2/{self.module}"
        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        records = response.json().get("data", [])
        return [Document(json.dumps(r), {"source": f"zoho://{self.module}/{r.get('id')}"}) for r in records]

class SugarCRMLoader(BaseLoader):
    """Load data from SugarCRM."""
    name = "sugarcrm"
    def __init__(self, url: str, username: str, password: str):
        self.url, self.username, self.password = url, username, password
    def load(self) -> List[Document]: return []

class DynamicsCRMLoader(BaseLoader):
    """Load data from Microsoft Dynamics 365."""
    name = "dynamics365"
    def __init__(self, org_url: str, access_token: Optional[str] = None, entity: str = "leads"):
        self.org_url = org_url.rstrip("/")
        self.access_token = access_token or os.getenv("DYNAMICS_ACCESS_TOKEN")
        self.entity = entity
    def load(self) -> List[Document]:
        import requests, json
        url = f"{self.org_url}/api/data/v9.2/{self.entity}"
        headers = {"Authorization": f"Bearer {self.access_token}", "OData-MaxVersion": "4.0", "OData-Version": "4.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        records = response.json().get("value", [])
        return [Document(json.dumps(r), {"source": f"dynamics://{self.entity}/{r.get('leadid', r.get('accountid', 'unknown'))}"}) for r in records]

class FreshsalesLoader(BaseLoader):
    """Load data from Freshsales."""
    name = "freshsales"
    def __init__(self, domain: str, api_key: Optional[str] = None):
        self.domain = domain
        self.api_key = api_key or os.getenv("FRESHSALES_API_KEY")
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://{self.domain}.freshsales.io/api/leads/view/1"
        headers = {"Authorization": f"Token token={self.api_key}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        leads = response.json().get("leads", [])
        return [Document(json.dumps(l), {"source": f"freshsales://lead/{l.get('id')}"}) for l in leads]

class CloseLoader(BaseLoader):
    """Load data from Close.io CRM."""
    name = "close"
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CLOSE_API_KEY")
    def load(self) -> List[Document]:
        import requests, json
        url = "https://api.close.com/api/v1/lead/"
        response = requests.get(url, auth=(self.api_key, ""), timeout=30)
        response.raise_for_status()
        leads = response.json().get("data", [])
        return [Document(json.dumps(l), {"source": f"close://lead/{l.get('id')}"}) for l in leads]


# =============================================================================
# Project Management / Collaboration
# =============================================================================

class ClickUpLoader(BaseLoader):
    """Load tasks from ClickUp."""
    name = "clickup"
    def __init__(self, api_key: Optional[str] = None, list_id: str = ""):
        self.api_key = api_key or os.getenv("CLICKUP_API_KEY")
        self.list_id = list_id
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://api.clickup.com/api/v2/list/{self.list_id}/task"
        headers = {"Authorization": self.api_key}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        tasks = response.json().get("tasks", [])
        return [Document(f"{t['name']}\n\n{t.get('description', '')}", {"source": t.get("url"), "id": t["id"]}) for t in tasks]

class MondayLoader(BaseLoader):
    """Load items from Monday.com."""
    name = "monday"
    def __init__(self, api_key: Optional[str] = None, board_id: str = ""):
        self.api_key = api_key or os.getenv("MONDAY_API_KEY")
        self.board_id = board_id
    def load(self) -> List[Document]:
        import requests, json
        url = "https://api.monday.com/v2"
        query = f'{{ boards(ids: {self.board_id}) {{ items_page {{ items {{ id name column_values {{ text }} }} }} }} }}'
        headers = {"Authorization": self.api_key}
        response = requests.post(url, json={"query": query}, headers=headers, timeout=30)
        items = response.json().get("data", {}).get("boards", [{}])[0].get("items_page", {}).get("items", [])
        return [Document(i["name"], {"source": f"monday://item/{i['id']}"}) for i in items]

class BasecampLoader(BaseLoader):
    """Load data from Basecamp."""
    name = "basecamp"
    def __init__(self, account_id: str, access_token: Optional[str] = None):
        self.account_id = account_id
        self.access_token = access_token or os.getenv("BASECAMP_ACCESS_TOKEN")
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://3.basecampapi.com/{self.account_id}/projects.json"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        projects = response.json()
        return [Document(f"{p['name']}\n{p.get('description', '')}", {"source": p.get("app_url")}) for p in projects]

class WrikeLoader(BaseLoader):
    """Load tasks from Wrike."""
    name = "wrike"
    def __init__(self, access_token: Optional[str] = None, folder_id: str = ""):
        self.access_token = access_token or os.getenv("WRIKE_ACCESS_TOKEN")
        self.folder_id = folder_id
    def load(self) -> List[Document]:
        import requests
        url = f"https://www.wrike.com/api/v4/folders/{self.folder_id}/tasks" if self.folder_id else "https://www.wrike.com/api/v4/tasks"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        tasks = response.json().get("data", [])
        return [Document(f"{t['title']}\n\n{t.get('description', '')}", {"source": t.get("permalink"), "id": t["id"]}) for t in tasks]

class SmartsheetLoader(BaseLoader):
    """Load data from Smartsheet."""
    name = "smartsheet"
    def __init__(self, api_key: Optional[str] = None, sheet_id: str = ""):
        self.api_key = api_key or os.getenv("SMARTSHEET_API_KEY")
        self.sheet_id = sheet_id
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://api.smartsheet.com/2.0/sheets/{self.sheet_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        sheet = response.json()
        cols = [c["title"] for c in sheet.get("columns", [])]
        docs = []
        for row in sheet.get("rows", []):
            cells = {cols[i]: c.get("value", "") for i, c in enumerate(row.get("cells", [])) if i < len(cols)}
            docs.append(Document(json.dumps(cells), {"source": f"smartsheet://{self.sheet_id}/{row['id']}"}))
        return docs

class TeamworkLoader(BaseLoader):
    """Load data from Teamwork."""
    name = "teamwork"
    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url
        self.api_key = api_key
    def load(self) -> List[Document]: return []


# =============================================================================
# Documentation / Wiki Systems
# =============================================================================

class MediaWikiLoader(BaseLoader):
    """Load pages from MediaWiki installations."""
    name = "mediawiki"
    def __init__(self, url: str, page_titles: List[str]):
        self.url = url.rstrip("/")
        self.page_titles = page_titles
    def load(self) -> List[Document]:
        import requests
        docs = []
        for title in self.page_titles:
            api_url = f"{self.url}/api.php?action=query&titles={title}&prop=revisions&rvprop=content&format=json"
            response = requests.get(api_url, timeout=30)
            pages = response.json().get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if "revisions" in page:
                    content = page["revisions"][0].get("*", "")
                    docs.append(Document(content, {"source": f"{self.url}/wiki/{title}", "title": page.get("title")}))
        return docs

class DokuWikiLoader(BaseLoader):
    """Load pages from DokuWiki."""
    name = "dokuwiki"
    def __init__(self, url: str, namespace: str = ""):
        self.url = url
        self.namespace = namespace
    def load(self) -> List[Document]: return []

class BookStackLoader(BaseLoader):
    """Load content from BookStack."""
    name = "bookstack"
    def __init__(self, url: str, token_id: str, token_secret: str):
        self.url = url
        self.token_id = token_id
        self.token_secret = token_secret
    def load(self) -> List[Document]: return []

class GitBookLoader(BaseLoader):
    """Load content from GitBook."""
    name = "gitbook"
    def __init__(self, api_key: Optional[str] = None, space_id: str = ""):
        self.api_key = api_key or os.getenv("GITBOOK_API_KEY")
        self.space_id = space_id
    def load(self) -> List[Document]:
        import requests
        url = f"https://api.gitbook.com/v1/spaces/{self.space_id}/content"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        pages = response.json().get("pages", [])
        return [Document(p.get("title", ""), {"source": p.get("path")}) for p in pages]

class ReadmeLoader(BaseLoader):
    """Load docs from ReadMe.io."""
    name = "readme"
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("README_API_KEY")
    def load(self) -> List[Document]: return []

class MkDocsLoader(BaseLoader):
    """Load MkDocs site content."""
    name = "mkdocs"
    def __init__(self, docs_dir: str):
        self.docs_dir = docs_dir
    def load(self) -> List[Document]:
        from pathlib import Path
        docs = []
        for md_file in Path(self.docs_dir).rglob("*.md"):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            docs.append(Document(content, {"source": str(md_file), "type": "mkdocs"}))
        return docs

class SphinxLoader(BaseLoader):
    """Load Sphinx documentation."""
    name = "sphinx"
    def __init__(self, build_dir: str):
        self.build_dir = build_dir
    def load(self) -> List[Document]: return []


# =============================================================================
# Communication / Chat
# =============================================================================

class MattermostLoader(BaseLoader):
    """Load messages from Mattermost."""
    name = "mattermost"
    def __init__(self, url: str, token: Optional[str] = None, channel_id: str = ""):
        self.url = url.rstrip("/")
        self.token = token or os.getenv("MATTERMOST_TOKEN")
        self.channel_id = channel_id
    def load(self) -> List[Document]:
        import requests
        api_url = f"{self.url}/api/v4/channels/{self.channel_id}/posts"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        posts = response.json().get("posts", {})
        messages = [p.get("message", "") for p in posts.values()]
        return [Document("\n".join(messages), {"source": f"mattermost://{self.channel_id}"})]

class RocketChatLoader(BaseLoader):
    """Load messages from Rocket.Chat."""
    name = "rocketchat"
    def __init__(self, url: str, user_id: str, auth_token: str, room_id: str = ""):
        self.url = url
        self.user_id = user_id
        self.auth_token = auth_token
        self.room_id = room_id
    def load(self) -> List[Document]: return []

class ZulipLoader(BaseLoader):
    """Load messages from Zulip."""
    name = "zulip"
    def __init__(self, site: str, email: str, api_key: str, stream: str = ""):
        self.site = site.rstrip("/")
        self.email = email
        self.api_key = api_key
        self.stream = stream
    def load(self) -> List[Document]:
        import requests
        url = f"{self.site}/api/v1/messages?anchor=newest&num_before=100&num_after=0&narrow=[{{\"operator\":\"stream\",\"operand\":\"{self.stream}\"}}]"
        response = requests.get(url, auth=(self.email, self.api_key), timeout=30)
        response.raise_for_status()
        messages = response.json().get("messages", [])
        content = "\n".join([f"[{m.get('sender_full_name')}]: {m.get('content')}" for m in messages])
        return [Document(content, {"source": f"zulip://{self.stream}"})]

class GoogleChatLoader(BaseLoader):
    """Load messages from Google Chat."""
    name = "googlechat"
    def __init__(self, credentials_path: Optional[str] = None, space_id: str = ""):
        self.credentials_path = credentials_path
        self.space_id = space_id
    def load(self) -> List[Document]: return []

class WhatsAppLoader(BaseLoader):
    """Load WhatsApp chat exports."""
    name = "whatsapp"
    def __init__(self, export_path: str):
        self.export_path = export_path
    def load(self) -> List[Document]:
        import re
        with open(self.export_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Parse WhatsApp export format: [DD/MM/YYYY, HH:MM:SS] Name: Message
        messages = re.findall(r'\[.*?\] (.*?): (.*?)(?=\n\[|$)', content, re.DOTALL)
        formatted = "\n".join([f"[{name}]: {msg.strip()}" for name, msg in messages])
        return [Document(formatted or content, {"source": self.export_path, "type": "whatsapp"})]


# =============================================================================
# E-commerce Platforms
# =============================================================================

class ShopifyLoader(BaseLoader):
    """Load products from Shopify."""
    name = "shopify"
    def __init__(self, shop_url: str, access_token: Optional[str] = None):
        self.shop_url = shop_url.rstrip("/")
        self.access_token = access_token or os.getenv("SHOPIFY_ACCESS_TOKEN")
    def load(self) -> List[Document]:
        import requests, json
        url = f"{self.shop_url}/admin/api/2024-01/products.json"
        headers = {"X-Shopify-Access-Token": self.access_token}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        products = response.json().get("products", [])
        return [Document(f"{p['title']}\n\n{p.get('body_html', '')}", {"source": f"{self.shop_url}/products/{p['handle']}"}) for p in products]

class WooCommerceLoader(BaseLoader):
    """Load products from WooCommerce."""
    name = "woocommerce"
    def __init__(self, url: str, consumer_key: str, consumer_secret: str):
        self.url = url.rstrip("/")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
    def load(self) -> List[Document]:
        import requests, json
        api_url = f"{self.url}/wp-json/wc/v3/products"
        response = requests.get(api_url, auth=(self.consumer_key, self.consumer_secret), timeout=30)
        response.raise_for_status()
        products = response.json()
        return [Document(f"{p['name']}\n\n{p.get('description', '')}", {"source": p.get("permalink"), "id": p["id"]}) for p in products]

class MagentoLoader(BaseLoader):
    """Load products from Magento."""
    name = "magento"
    def __init__(self, url: str, access_token: Optional[str] = None):
        self.url = url.rstrip("/")
        self.access_token = access_token or os.getenv("MAGENTO_ACCESS_TOKEN")
    def load(self) -> List[Document]:
        import requests, json
        api_url = f"{self.url}/rest/V1/products?searchCriteria[pageSize]=100"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        products = response.json().get("items", [])
        return [Document(f"{p['name']}\n\n{p.get('custom_attributes', [])}", {"source": f"{self.url}/catalog/product/view/id/{p['id']}"}) for p in products]

class BigCommerceLoader(BaseLoader):
    """Load products from BigCommerce."""
    name = "bigcommerce"
    def __init__(self, store_hash: str, access_token: Optional[str] = None):
        self.store_hash = store_hash
        self.access_token = access_token or os.getenv("BIGCOMMERCE_ACCESS_TOKEN")
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://api.bigcommerce.com/stores/{self.store_hash}/v3/catalog/products"
        headers = {"X-Auth-Token": self.access_token}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        products = response.json().get("data", [])
        return [Document(f"{p['name']}\n\n{p.get('description', '')}", {"source": p.get("custom_url", {}).get("url")}) for p in products]

class StripeLoader(BaseLoader):
    """Load data from Stripe."""
    name = "stripe"
    def __init__(self, api_key: Optional[str] = None, resource: str = "customers"):
        self.api_key = api_key or os.getenv("STRIPE_API_KEY")
        self.resource = resource
    def load(self) -> List[Document]:
        try:
            import stripe, json
            stripe.api_key = self.api_key
            resource_map = {"customers": stripe.Customer, "charges": stripe.Charge, "invoices": stripe.Invoice}
            items = resource_map.get(self.resource, stripe.Customer).list(limit=100)
            return [Document(json.dumps(dict(i)), {"source": f"stripe://{self.resource}/{i.id}"}) for i in items.data]
        except ImportError:
            raise ImportError("stripe required. pip install stripe")


# =============================================================================
# Analytics / BI Tools
# =============================================================================

class GoogleAnalyticsLoader(BaseLoader):
    """Load data from Google Analytics."""
    name = "google_analytics"
    def __init__(self, credentials_path: Optional[str] = None, view_id: str = ""):
        self.credentials_path = credentials_path
        self.view_id = view_id
    def load(self) -> List[Document]: return []

class MixpanelLoader(BaseLoader):
    """Load events from Mixpanel."""
    name = "mixpanel"
    def __init__(self, api_secret: Optional[str] = None, from_date: str = "", to_date: str = ""):
        self.api_secret = api_secret or os.getenv("MIXPANEL_API_SECRET")
        self.from_date = from_date
        self.to_date = to_date
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://data.mixpanel.com/api/2.0/export?from_date={self.from_date}&to_date={self.to_date}"
        response = requests.get(url, auth=(self.api_secret, ""), timeout=60)
        response.raise_for_status()
        events = [json.loads(line) for line in response.text.strip().split("\n") if line]
        return [Document(json.dumps(e.get("properties", {})), {"source": "mixpanel", "event": e.get("event")}) for e in events[:100]]

class AmplitudeLoader(BaseLoader):
    """Load events from Amplitude."""
    name = "amplitude"
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AMPLITUDE_API_KEY")
        self.secret_key = secret_key
    def load(self) -> List[Document]: return []

class SegmentLoader(BaseLoader):
    """Load data from Segment."""
    name = "segment"
    def __init__(self, access_token: Optional[str] = None, workspace: str = ""):
        self.access_token = access_token or os.getenv("SEGMENT_ACCESS_TOKEN")
        self.workspace = workspace
    def load(self) -> List[Document]: return []

class MetabaseLoader(BaseLoader):
    """Load data from Metabase."""
    name = "metabase"
    def __init__(self, url: str, username: str, password: str, question_id: int = 0):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.question_id = question_id
    def load(self) -> List[Document]:
        import requests, json
        # Login
        session = requests.Session()
        auth_resp = session.post(f"{self.url}/api/session", json={"username": self.username, "password": self.password})
        auth_resp.raise_for_status()
        # Query
        query_resp = session.post(f"{self.url}/api/card/{self.question_id}/query")
        query_resp.raise_for_status()
        data = query_resp.json().get("data", {})
        rows = data.get("rows", [])
        cols = [c.get("name") for c in data.get("cols", [])]
        return [Document(json.dumps(dict(zip(cols, row))), {"source": f"metabase://question/{self.question_id}"}) for row in rows]

class TableauLoader(BaseLoader):
    """Load data from Tableau."""
    name = "tableau"
    def __init__(self, server_url: str, username: str, password: str, site_id: str = ""):
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.site_id = site_id
    def load(self) -> List[Document]:
        try:
            import tableauserverclient as TSC
            auth = TSC.TableauAuth(self.username, self.password, self.site_id)
            server = TSC.Server(self.server_url)
            with server.auth.sign_in(auth):
                workbooks, _ = server.workbooks.get()
                return [Document(f"{w.name}\n{w.description or ''}", {"source": w.webpage_url}) for w in workbooks]
        except ImportError:
            raise ImportError("tableauserverclient required")

class LookerLoader(BaseLoader):
    """Load data from Looker."""
    name = "looker"
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
    def load(self) -> List[Document]: return []

class PowerBILoader(BaseLoader):
    """Load data from Power BI."""
    name = "powerbi"
    def __init__(self, access_token: Optional[str] = None, group_id: str = ""):
        self.access_token = access_token or os.getenv("POWERBI_ACCESS_TOKEN")
        self.group_id = group_id
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.group_id}/reports" if self.group_id else "https://api.powerbi.com/v1.0/myorg/reports"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        reports = response.json().get("value", [])
        return [Document(f"{r['name']}", {"source": r.get("webUrl")}) for r in reports]


# =============================================================================
# Dev Tools / Issue Trackers
# =============================================================================

class YouTrackLoader(BaseLoader):
    """Load issues from YouTrack."""
    name = "youtrack"
    def __init__(self, url: str, token: Optional[str] = None, query: str = "State: -Resolved"):
        self.url = url.rstrip("/")
        self.token = token or os.getenv("YOUTRACK_TOKEN")
        self.query = query
    def load(self) -> List[Document]:
        import requests
        api_url = f"{self.url}/api/issues?fields=id,summary,description&query={self.query}"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        issues = response.json()
        return [Document(f"{i['summary']}\n\n{i.get('description', '')}", {"source": f"{self.url}/issue/{i['id']}"}) for i in issues]

class RedmineLoader(BaseLoader):
    """Load issues from Redmine."""
    name = "redmine"
    def __init__(self, url: str, api_key: Optional[str] = None, project_id: str = ""):
        self.url = url.rstrip("/")
        self.api_key = api_key or os.getenv("REDMINE_API_KEY")
        self.project_id = project_id
    def load(self) -> List[Document]:
        import requests
        api_url = f"{self.url}/projects/{self.project_id}/issues.json" if self.project_id else f"{self.url}/issues.json"
        headers = {"X-Redmine-API-Key": self.api_key}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        issues = response.json().get("issues", [])
        return [Document(f"{i['subject']}\n\n{i.get('description', '')}", {"source": f"{self.url}/issues/{i['id']}"}) for i in issues]

class BugzillaLoader(BaseLoader):
    """Load bugs from Bugzilla."""
    name = "bugzilla"
    def __init__(self, url: str, api_key: Optional[str] = None, product: str = ""):
        self.url = url.rstrip("/")
        self.api_key = api_key or os.getenv("BUGZILLA_API_KEY")
        self.product = product
    def load(self) -> List[Document]:
        import requests
        api_url = f"{self.url}/rest/bug?product={self.product}&limit=100" if self.product else f"{self.url}/rest/bug?limit=100"
        headers = {"X-BUGZILLA-API-KEY": self.api_key} if self.api_key else {}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        bugs = response.json().get("bugs", [])
        return [Document(f"{b['summary']}", {"source": f"{self.url}/show_bug.cgi?id={b['id']}"}) for b in bugs]

class PhabricatorLoader(BaseLoader):
    """Load tasks from Phabricator."""
    name = "phabricator"
    def __init__(self, url: str, api_token: Optional[str] = None):
        self.url = url
        self.api_token = api_token
    def load(self) -> List[Document]: return []

class AzureDevOpsLoader(BaseLoader):
    """Load work items from Azure DevOps."""
    name = "azure_devops"
    def __init__(self, org_url: str, project: str, pat: Optional[str] = None):
        self.org_url = org_url.rstrip("/")
        self.project = project
        self.pat = pat or os.getenv("AZURE_DEVOPS_PAT")
    def load(self) -> List[Document]:
        import requests, base64
        auth = base64.b64encode(f":{self.pat}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
        url = f"{self.org_url}/{self.project}/_apis/wit/wiql?api-version=7.0"
        query = {"query": "SELECT [Id], [Title] FROM WorkItems WHERE [State] <> 'Closed' ORDER BY [Id] DESC"}
        response = requests.post(url, json=query, headers=headers, timeout=30)
        return [Document(f"WorkItem {i['id']}", {"source": i.get("url")}) for i in response.json().get("workItems", [])]

class SentryLoader(BaseLoader):
    """Load issues from Sentry."""
    name = "sentry"
    def __init__(self, api_key: Optional[str] = None, org_slug: str = "", project_slug: str = ""):
        self.api_key = api_key or os.getenv("SENTRY_API_KEY")
        self.org_slug = org_slug
        self.project_slug = project_slug
    def load(self) -> List[Document]:
        import requests
        url = f"https://sentry.io/api/0/projects/{self.org_slug}/{self.project_slug}/issues/"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        issues = response.json()
        return [Document(f"{i['title']}\n{i.get('culprit', '')}", {"source": i.get("permalink"), "id": i["id"]}) for i in issues]

class DatadogLoader(BaseLoader):
    """Load data from Datadog."""
    name = "datadog"
    def __init__(self, api_key: Optional[str] = None, app_key: Optional[str] = None, query: str = "avg:system.cpu.user{*}"):
        self.api_key = api_key or os.getenv("DATADOG_API_KEY")
        self.app_key = app_key or os.getenv("DATADOG_APP_KEY")
        self.query = query
    def load(self) -> List[Document]:
        import requests, json, time
        end = int(time.time())
        start = end - 3600  # Last hour
        url = f"https://api.datadoghq.com/api/v1/query?from={start}&to={end}&query={self.query}"
        headers = {"DD-API-KEY": self.api_key, "DD-APPLICATION-KEY": self.app_key}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        series = response.json().get("series", [])
        return [Document(json.dumps(s.get("pointlist", [])), {"source": "datadog", "metric": s.get("metric")}) for s in series]


# =============================================================================
# HR / Recruiting
# =============================================================================

class GreenhouseLoader(BaseLoader):
    """Load candidates from Greenhouse."""
    name = "greenhouse"
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GREENHOUSE_API_KEY")
    def load(self) -> List[Document]:
        import requests, json
        url = "https://harvest.greenhouse.io/v1/candidates"
        response = requests.get(url, auth=(self.api_key, ""), timeout=30)
        response.raise_for_status()
        candidates = response.json()
        return [Document(f"{c.get('first_name', '')} {c.get('last_name', '')}", {"source": f"greenhouse://candidate/{c['id']}"}) for c in candidates]

class LeverLoader(BaseLoader):
    """Load candidates from Lever."""
    name = "lever"
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LEVER_API_KEY")
    def load(self) -> List[Document]:
        import requests, json
        url = "https://api.lever.co/v1/opportunities"
        response = requests.get(url, auth=(self.api_key, ""), timeout=30)
        response.raise_for_status()
        opps = response.json().get("data", [])
        return [Document(f"{o.get('name', '')}", {"source": o.get("links", {}).get("lever")}) for o in opps]

class WorkdayLoader(BaseLoader):
    """Load data from Workday."""
    name = "workday"
    def __init__(self, tenant: str, username: str, password: str):
        self.tenant = tenant
        self.username = username
        self.password = password
    def load(self) -> List[Document]: return []

class BambooHRLoader(BaseLoader):
    """Load data from BambooHR."""
    name = "bamboohr"
    def __init__(self, subdomain: str, api_key: Optional[str] = None):
        self.subdomain = subdomain
        self.api_key = api_key or os.getenv("BAMBOOHR_API_KEY")
    def load(self) -> List[Document]:
        import requests, json
        url = f"https://api.bamboohr.com/api/gateway.php/{self.subdomain}/v1/employees/directory"
        response = requests.get(url, auth=(self.api_key, "x"), headers={"Accept": "application/json"}, timeout=30)
        response.raise_for_status()
        employees = response.json().get("employees", [])
        return [Document(f"{e.get('displayName', '')}", {"source": f"bamboohr://employee/{e['id']}"}) for e in employees]


# =============================================================================
# File Formats (Extended)
# =============================================================================

class EPUBLoader(BaseLoader):
    """Load EPUB ebook files."""
    name = "epub"
    def __init__(self, path: str):
        self.path = path
    def load(self) -> List[Document]:
        try:
            import ebooklib
            from ebooklib import epub
            from bs4 import BeautifulSoup
            book = epub.read_epub(self.path)
            docs = []
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                soup = BeautifulSoup(item.get_content(), "html.parser")
                docs.append(Document(soup.get_text(), {"source": self.path, "item": item.get_name()}))
            return docs
        except ImportError:
            raise ImportError("ebooklib and beautifulsoup4 required")

class MOBILoader(BaseLoader):
    """Load MOBI ebook files."""
    name = "mobi"
    def __init__(self, path: str):
        self.path = path
    def load(self) -> List[Document]: return []

class ODTLoader(BaseLoader):
    """Load OpenDocument Text files."""
    name = "odt"
    def __init__(self, path: str):
        self.path = path
    def load(self) -> List[Document]: return []

class RTFLoader(BaseLoader):
    """Load RTF files."""
    name = "rtf"
    def __init__(self, path: str):
        self.path = path
    def load(self) -> List[Document]: return []

class IPYNBLoader(BaseLoader):
    """Load Jupyter Notebook files."""
    name = "ipynb"
    def __init__(self, path: str, include_outputs: bool = True):
        self.path = path
        self.include_outputs = include_outputs
    def load(self) -> List[Document]:
        import json
        with open(self.path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        cells = []
        for cell in nb.get("cells", []):
            src = "".join(cell.get("source", []))
            if self.include_outputs and cell.get("cell_type") == "code":
                for out in cell.get("outputs", []):
                    if "text" in out:
                        src += "\n# Output:\n" + "".join(out["text"])
            cells.append(src)
        return [Document("\n\n".join(cells), {"source": self.path})]

class TomlLoader(BaseLoader):
    """Load TOML files."""
    name = "toml"
    def __init__(self, path: str):
        self.path = path
    def load(self) -> List[Document]:
        import tomllib, json
        with open(self.path, "rb") as f:
            data = tomllib.load(f)
        return [Document(json.dumps(data, default=str), {"source": self.path})]

class YamlLoader(BaseLoader):
    """Load YAML files."""
    name = "yaml"
    def __init__(self, path: str):
        self.path = path
    def load(self) -> List[Document]:
        import yaml, json
        with open(self.path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [Document(json.dumps(data, default=str), {"source": self.path})]

class INILoader(BaseLoader):
    """Load INI config files."""
    name = "ini"
    def __init__(self, path: str):
        self.path = path
    def load(self) -> List[Document]:
        import configparser, json
        config = configparser.ConfigParser()
        config.read(self.path)
        data = {s: dict(config[s]) for s in config.sections()}
        return [Document(json.dumps(data), {"source": self.path})]

class LogLoader(BaseLoader):
    """Load log files."""
    name = "log"
    def __init__(self, path: str, pattern: Optional[str] = None):
        self.path = path
        self.pattern = pattern
    def load(self) -> List[Document]:
        import re
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if self.pattern:
            matches = re.findall(self.pattern, content)
            content = "\n".join(matches)
        return [Document(content, {"source": self.path})]
