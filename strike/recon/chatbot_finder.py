#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Chatbot Endpoint Discovery

Automatically discovers hidden chatbot endpoints through:
1. Common path enumeration (/chat, /api/chat, /support, etc.)
2. Chat widget detection (Intercom, Zendesk, Drift, Crisp, etc.)
3. WebSocket endpoint detection
4. JavaScript analysis for chat initialization
5. robots.txt and sitemap scanning
6. Third-party chat service fingerprinting
"""

import re
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChatbotEndpoint:
    """Discovered chatbot endpoint."""

    url: str
    type: str  # api, websocket, widget, iframe
    provider: Optional[str] = None  # Intercom, Zendesk, etc.
    confidence: float = 0.0
    details: Optional[Dict] = None


class ChatbotFinder:
    """
    Automated chatbot endpoint discovery.

    Finds hidden chat interfaces that may not be obvious from main page.
    """

    # Common chatbot API paths
    # Sources: SecLists, Assetnote Wordlists, Bug Bounty findings
    COMMON_PATHS = [
        # === CHAT ENDPOINTS ===
        "/chat",
        "/api/chat",
        "/v1/chat",
        "/api/v1/chat",
        "/v2/chat",
        "/api/v2/chat",
        "/chat/api",
        "/chatbot",
        "/bot",
        "/assistant",
        "/api/assistant",
        "/api/bot",
        "/ai",
        "/api/ai",
        "/ai/chat",
        "/api/ai/chat",
        "/virtual-assistant",
        "/va",
        "/agent",
        "/api/agent",
        # === SUPPORT/HELP ===
        "/support",
        "/help",
        "/support/chat",
        "/help/chat",
        "/api/support",
        "/contact",
        "/feedback",
        "/helpdesk",
        "/support-chat",
        "/live-support",
        "/customer-support",
        "/support/ticket",
        "/support/api",
        "/help-center",
        # === MESSAGING ===
        "/message",
        "/messages",
        "/api/message",
        "/api/messages",
        "/conversation",
        "/api/conversation",
        "/conversations",
        "/send",
        "/send-message",
        "/api/send",
        "/inbox",
        "/thread",
        "/threads",
        "/api/thread",
        "/dialog",
        # === OPENAI-STYLE COMPLETIONS ===
        "/completions",
        "/api/completions",
        "/v1/completions",
        "/chat/completions",
        "/api/chat/completions",
        "/v1/chat/completions",
        "/api/v1/chat/completions",
        "/generate",
        "/api/generate",
        "/inference",
        "/predict",
        "/api/inference",
        "/api/predict",
        "/completion",
        # === WEBSOCKET PATHS ===
        "/ws",
        "/ws/chat",
        "/websocket",
        "/socket.io",
        "/cable",
        "/realtime",
        "/live",
        "/stream",
        "/wss",
        "/ws/v1",
        "/ws/v2",
        "/socket",
        "/sockjs",
        "/signalr",
        "/hub",
        "/hubs/chat",
        "/events",
        "/sse",
        "/api/stream",
        "/api/sse",
        "/push",
        # === WIDGET ENDPOINTS ===
        "/widget",
        "/chat-widget",
        "/embed/chat",
        "/widget/chat",
        "/chatwidget",
        "/embed",
        "/widget.js",
        "/chat.js",
        "/loader",
        # === LLM/AI SPECIFIC (from ArXiv research) ===
        "/llm",
        "/api/llm",
        "/gpt",
        "/api/gpt",
        "/claude",
        "/api/claude",
        "/gemini",
        "/api/gemini",
        "/openai",
        "/api/openai",
        "/anthropic",
        "/model",
        "/models",
        "/api/models",
        "/prompt",
        "/prompts",
        "/api/prompt",
        "/v1/engines",
        "/v1/models",
        "/v1/embeddings",
        # === INTERNAL/DEBUG ===
        "/internal/chat",
        "/debug/chat",
        "/_chat",
        "/api/internal/assistant",
        "/admin/chat",
        "/dev/chat",
        "/test/chat",
        "/staging/chat",
        "/.well-known/ai-plugin.json",  # OpenAI Plugin manifest
        "/openapi.json",
        "/swagger.json",
        "/api-docs",
        # === SECLIST COMMON API PATHS ===
        "/api",
        "/api/v1",
        "/api/v2",
        "/api/v3",
        "/rest",
        "/rest/api",
        "/graphql",
        "/gql",
        "/query",
        "/search",
        "/api/search",
        "/ask",
        "/answer",
        "/qa",
        "/api/qa",
        # === VENDOR SPECIFIC ===
        "/intercom",
        "/.intercom",
        "/zendesk",
        "/zopim",
        "/livechat",
        "/drift",
        "/.drift",
        "/hubspot",
        "/hs",
        "/conversations",
        "/freshchat",
        "/freshdesk",
        "/liveagent",
        "/chatbutton",  # Salesforce
        "/directline",
        "/botframework",  # Microsoft
        # === MCP/A2A PROTOCOL (ArXiv 2025) ===
        "/mcp",
        "/api/mcp",
        "/a2a",
        "/api/a2a",
        "/agent-to-agent",
        "/tools",
        "/api/tools",
        "/functions",
        "/api/functions",
        # === CMS CHAT PLUGINS ===
        "/wp-json/chat",
        "/wp-content/plugins/chat",
        "/modules/chat",
        "/extensions/chat",
    ]

    # Chat widget signatures in HTML/JS
    WIDGET_SIGNATURES = {
        "intercom": [
            r"intercom\.io",
            r"widget\.intercom\.io",
            r"Intercom\s*\(",
            r"intercomSettings",
            r"ic-app",
        ],
        "zendesk": [
            r"zdassets\.com",
            r"zendesk\.com/embeddable",
            r"zE\s*\(",
            r"zESettings",
            r"#launcher",
        ],
        "drift": [
            r"drift\.com",
            r"js\.driftt\.com",
            r"drift\s*\(",
            r"driftConfig",
        ],
        "crisp": [
            r"crisp\.chat",
            r"client\.crisp\.chat",
            r"\$crisp",
            r"CRISP_WEBSITE_ID",
        ],
        "tawk": [
            r"tawk\.to",
            r"embed\.tawk\.to",
            r"Tawk_API",
            r"tawk\d+",
        ],
        "livechat": [
            r"livechatinc\.com",
            r"cdn\.livechatinc\.com",
            r"LiveChatWidget",
            r"__lc\s*=",
        ],
        "freshchat": [
            r"freshchat\.com",
            r"wchat\.freshchat\.com",
            r"Freshchat\s*\(",
        ],
        "hubspot": [
            r"hs-scripts\.com",
            r"js\.hubspot\.com",
            r"HubSpotConversations",
            r"hsConversationsSettings",
        ],
        "facebook_messenger": [
            r"connect\.facebook\.net",
            r"fb-customerchat",
            r"MessengerExtensions",
        ],
        "whatsapp": [
            r"whatsapp\.com/send",
            r"wa\.me/",
            r"whatsapp-widget",
        ],
        "telegram": [
            r"t\.me/",
            r"telegram-widget",
            r"tg://resolve",
        ],
        "chatra": [
            r"chatra\.io",
            r"call\.chatra\.io",
            r"ChatraID",
        ],
        "olark": [
            r"olark\.com",
            r"static\.olark\.com",
            r"olark\s*\(",
        ],
        "userlike": [
            r"userlike\.com",
            r"userlike-cmp",
        ],
        # AI-specific chatbots
        "openai_chatgpt": [
            r"chat\.openai\.com",
            r"chatgpt",
            r"gpt-4",
            r"openai-widget",
        ],
        "anthropic_claude": [
            r"claude\.ai",
            r"anthropic",
        ],
        "custom_llm": [
            r"/api/v1/chat/completions",
            r"llm\.",
            r"ai-chat",
            r"neural",
        ],
    }

    # WebSocket indicators
    WEBSOCKET_PATTERNS = [
        r'new\s+WebSocket\s*\([\'"]([^\'"]+)[\'"]\)',
        r'wss?://[^\s\'"]+/(?:chat|ws|socket|realtime)',
        r"socket\.io",
        r"sockjs",
        r"ActionCable",
        r"Phoenix\.Socket",
    ]

    # Chat SDK signatures for accurate platform detection
    CHAT_SDKS = {
        "intercom": [
            r"intercomSettings",
            r"Intercom\s*\(",
            r"window\.intercomSettings",
            r"intercom\.com/widget",
        ],
        "drift": [
            r"drift\.api",
            r"driftChat",
            r"drift\s*\(",
            r"js\.driftt\.com",
        ],
        "crisp": [
            r"CRISP_WEBSITE_ID",
            r"\$crisp",
            r"crisp\.chat",
            r"client\.crisp\.chat",
        ],
        "zendesk": [
            r'zE\s*\(\s*[\'"]webWidget',
            r"zendeskHost",
            r"web_widget",
            r"static\.zdassets\.com",
        ],
        "tidio": [
            r"tidioChatCode",
            r"tidio_chat",
            r"code\.tidio\.co",
        ],
        "livechat": [
            r"__lc\.license",
            r"livechatinc\.com",
            r"LiveChatWidget",
        ],
        "hubspot": [
            r"hs-script-loader",
            r"HubSpotConversations",
            r"js\.hs-scripts\.com",
        ],
        "freshchat": [
            r"fcWidget",
            r"freshchat\.com",
            r"wchat\.freshchat\.com",
        ],
        "tawk": [
            r"Tawk_API",
            r"tawk\.to",
            r"embed\.tawk\.to",
        ],
        "olark": [
            r"olark\.identify",
            r"olarkChat",
            r"static\.olark\.com",
        ],
        "chatra": [
            r"ChatraID",
            r"Chatra\s*\(",
            r"call\.chatra\.io",
        ],
        "jivochat": [
            r"jivo_api",
            r"jivosite\.com",
            r"JivoChat",
        ],
    }

    def __init__(
        self, timeout: int = 10, max_concurrent: int = 10, proxy_url: str = None
    ):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.found_endpoints: List[ChatbotEndpoint] = []
        self.proxy_url = proxy_url
        self.js_contents: Dict[str, str] = {}  # Cache for parsed JS files
        self.crawled_urls: set = set()  # Track crawled URLs to avoid loops

    async def discover(self, base_url: str) -> List[ChatbotEndpoint]:
        """
        Discover all chatbot endpoints for a given URL.

        Returns list of found endpoints sorted by confidence.
        """
        self.found_endpoints = []
        self.js_contents = {}
        self.crawled_urls = set()

        # Log proxy usage
        if self.proxy_url:
            logger.info("🏠 Using proxy for requests")

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        ) as session:
            # 1. Fetch main page and analyze
            main_page = await self._fetch_page(session, base_url)
            if main_page:
                await self._analyze_html(base_url, main_page)

            # 2. Parse and analyze JavaScript files
            await self._parse_javascript(session, base_url, main_page)

            # 3. Detect chat SDKs
            self._detect_chat_sdks(main_page)

            # 4. Scan common paths
            await self._scan_common_paths(session, base_url)

            # 5. Check robots.txt and sitemap
            await self._check_robots_sitemap(session, base_url)

            # 6. Look for subdomains
            await self._check_common_subdomains(session, base_url)

            # 7. Deep crawl found paths for more endpoints
            await self._deep_crawl(session, base_url)

        # Sort by confidence
        self.found_endpoints.sort(key=lambda x: x.confidence, reverse=True)

        # Deduplicate by URL
        seen_urls = set()
        unique_endpoints = []
        for ep in self.found_endpoints:
            if ep.url not in seen_urls:
                seen_urls.add(ep.url)
                unique_endpoints.append(ep)
        self.found_endpoints = unique_endpoints

        return self.found_endpoints

    async def _fetch_page(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """Fetch page content, optionally through proxy."""
        try:
            async with session.get(url, proxy=self.proxy_url) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
        return None

    async def _analyze_html(self, base_url: str, html: str):
        """Analyze HTML for chat widget signatures."""

        # Check each widget provider
        for provider, patterns in self.WIDGET_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    self.found_endpoints.append(
                        ChatbotEndpoint(
                            url=base_url,
                            type="widget",
                            provider=provider,
                            confidence=0.9,
                            details={"pattern": pattern},
                        )
                    )
                    logger.info(f"🎯 Found {provider} widget on {base_url}")
                    break  # One match per provider is enough

        # Check for WebSocket endpoints
        for pattern in self.WEBSOCKET_PATTERNS:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and match.startswith(("ws://", "wss://")):
                    self.found_endpoints.append(
                        ChatbotEndpoint(
                            url=match,
                            type="websocket",
                            confidence=0.85,
                            details={"source": "js_analysis"},
                        )
                    )
                    logger.info(f"🔌 Found WebSocket: {match}")

        # Look for chat iframes
        iframe_pattern = (
            r'<iframe[^>]+src=[\'"]([^\'"]*(?:chat|support|help|widget)[^\'"]*)[\'"]'
        )
        iframes = re.findall(iframe_pattern, html, re.IGNORECASE)
        for iframe_url in iframes:
            full_url = urljoin(base_url, iframe_url)
            self.found_endpoints.append(
                ChatbotEndpoint(
                    url=full_url,
                    type="iframe",
                    confidence=0.8,
                    details={"source": "iframe"},
                )
            )
            logger.info(f"📺 Found chat iframe: {full_url}")

        # Look for API endpoints in JavaScript
        api_pattern = r'[\'"]([^\'"]*(?:api|v1|v2)[^\'"]*(?:chat|message|conversation|assistant)[^\'"]*)[\'"]'
        apis = re.findall(api_pattern, html, re.IGNORECASE)
        for api_path in apis[:10]:  # Limit to first 10
            if api_path.startswith("/") or api_path.startswith("http"):
                full_url = urljoin(base_url, api_path)
                self.found_endpoints.append(
                    ChatbotEndpoint(
                        url=full_url,
                        type="api",
                        confidence=0.7,
                        details={"source": "js_analysis"},
                    )
                )

    async def _parse_javascript(
        self, session: aiohttp.ClientSession, base_url: str, html: str
    ):
        """Extract and analyze JavaScript files for hidden endpoints."""
        if not html:
            return

        # Find all script sources
        script_pattern = r'<script[^>]+src=["\']([^"\']+)["\']'
        scripts = re.findall(script_pattern, html, re.IGNORECASE)

        # Also look for inline scripts with API calls
        inline_pattern = r"<script[^>]*>(.*?)</script>"
        inline_scripts = re.findall(inline_pattern, html, re.DOTALL | re.IGNORECASE)

        # Analyze inline scripts
        for script in inline_scripts[:20]:  # Limit to first 20
            self._extract_endpoints_from_js(base_url, script)

        # Fetch and analyze external scripts (limit to 10)
        for script_url in scripts[:10]:
            if not script_url.startswith(("http", "//")):
                if script_url.startswith("/"):
                    script_url = urljoin(base_url, script_url)
                else:
                    continue
            elif script_url.startswith("//"):
                script_url = "https:" + script_url

            # Skip common CDN scripts that won't have our endpoints
            skip_domains = [
                "google",
                "facebook",
                "twitter",
                "analytics",
                "jquery",
                "bootstrap",
                "cloudflare",
                "gstatic",
            ]
            if any(d in script_url.lower() for d in skip_domains):
                continue

            try:
                js_content = await self._fetch_page(session, script_url)
                if js_content:
                    self.js_contents[script_url] = js_content
                    self._extract_endpoints_from_js(base_url, js_content)
            except Exception as e:
                logger.debug(f"Failed to fetch JS {script_url}: {e}")

    def _extract_endpoints_from_js(self, base_url: str, js_content: str):
        """Extract API endpoints and WebSocket URLs from JS content."""

        # API endpoint patterns
        api_patterns = [
            r'["\'](/api/[^"\']+)["\']',
            r'["\'](/v[12]/[^"\']+)["\']',
            r'endpoint["\s:]+["\']([^"\']+)["\']',
            r'url["\s:]+["\'](/[^"\']+chat[^"\']*)["\']',
            r'baseURL["\s:]+["\']([^"\']+)["\']',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, js_content, re.IGNORECASE)
            for match in matches[:5]:  # Limit matches
                if any(
                    kw in match.lower()
                    for kw in [
                        "chat",
                        "message",
                        "bot",
                        "ai",
                        "assistant",
                        "conversation",
                    ]
                ):
                    full_url = urljoin(base_url, match)
                    if full_url not in [ep.url for ep in self.found_endpoints]:
                        self.found_endpoints.append(
                            ChatbotEndpoint(
                                url=full_url,
                                type="api",
                                confidence=0.75,
                                details={"source": "js_deep_parse"},
                            )
                        )
                        logger.info(f"🔍 Found API in JS: {full_url}")

        # WebSocket patterns
        ws_patterns = [
            r'new\s+WebSocket\s*\(["\']([^"\']+)["\']',
            r'["\']wss?://[^"\']+["\']',
            r'socket\.connect\s*\(["\']([^"\']+)["\']',
        ]

        for pattern in ws_patterns:
            matches = re.findall(pattern, js_content, re.IGNORECASE)
            for match in matches:
                if match.startswith(("ws://", "wss://")):
                    if match not in [ep.url for ep in self.found_endpoints]:
                        self.found_endpoints.append(
                            ChatbotEndpoint(
                                url=match,
                                type="websocket",
                                confidence=0.85,
                                details={"source": "js_deep_parse"},
                            )
                        )
                        logger.info(f"🔌 Found WebSocket in JS: {match}")

    def _detect_chat_sdks(self, html: str):
        """Detect known chat SDK integrations with high confidence."""
        if not html:
            return

        # Also include cached JS content
        all_content = html
        for js in self.js_contents.values():
            all_content += "\n" + js

        for sdk_name, patterns in self.CHAT_SDKS.items():
            for pattern in patterns:
                if re.search(pattern, all_content, re.IGNORECASE):
                    # Found SDK - add with high confidence
                    self.found_endpoints.append(
                        ChatbotEndpoint(
                            url=f"SDK:{sdk_name}",
                            type="sdk",
                            provider=sdk_name,
                            confidence=0.95,
                            details={"pattern": pattern, "source": "sdk_detection"},
                        )
                    )
                    logger.info(f"🎯 Detected {sdk_name.upper()} SDK")
                    break  # One match per SDK

    async def _deep_crawl(
        self, session: aiohttp.ClientSession, base_url: str, max_depth: int = 2
    ):
        """Recursively crawl chat-related paths for more endpoints."""

        # Collect paths to crawl from found endpoints
        paths_to_crawl = set()

        for ep in self.found_endpoints:
            if ep.type in ["path", "api"] and ep.url.startswith(base_url):
                paths_to_crawl.add(ep.url)

        # Also add common deep paths
        deep_paths = [
            "/help/chat",
            "/support/chat",
            "/contact/chat",
            "/api/chat/config",
            "/chat/widget",
            "/widget/chat",
        ]
        for path in deep_paths:
            paths_to_crawl.add(urljoin(base_url, path))

        # Crawl each path (limit to avoid overwhelming)
        crawled = 0
        for url in list(paths_to_crawl)[:15]:
            if url in self.crawled_urls or crawled >= 10:
                continue

            self.crawled_urls.add(url)
            crawled += 1

            try:
                content = await self._fetch_page(session, url)
                if content:
                    # Analyze the page for chat indicators
                    await self._analyze_html(url, content)

                    # Look for links to more chat pages
                    link_pattern = (
                        r'href=["\']([^"\']*(?:chat|support|help|bot)[^"\']*)["\']'
                    )
                    links = re.findall(link_pattern, content, re.IGNORECASE)

                    for link in links[:5]:
                        full_link = urljoin(url, link)
                        if (
                            full_link.startswith(base_url)
                            and full_link not in self.crawled_urls
                        ):
                            self.found_endpoints.append(
                                ChatbotEndpoint(
                                    url=full_link,
                                    type="crawled_link",
                                    confidence=0.6,
                                    details={"source": "deep_crawl"},
                                )
                            )
            except Exception as e:
                logger.debug(f"Deep crawl failed for {url}: {e}")

    async def _scan_common_paths(self, session: aiohttp.ClientSession, base_url: str):
        """Scan common chatbot paths."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def check_path(path: str):
            async with semaphore:
                url = urljoin(base_url, path)
                try:
                    async with session.get(url, proxy=self.proxy_url) as response:
                        if response.status in [200, 201, 401, 403]:
                            # Even 401/403 means endpoint exists
                            content_type = response.headers.get("Content-Type", "")

                            confidence = 0.6
                            endpoint_type = "api"

                            if response.status == 200:
                                confidence = 0.8
                                body = await response.text()
                                if "chat" in body.lower() or "message" in body.lower():
                                    confidence = 0.9

                            if "websocket" in path or "ws" in path:
                                endpoint_type = "websocket"

                            if "json" in content_type:
                                endpoint_type = "api"
                                confidence += 0.1

                            self.found_endpoints.append(
                                ChatbotEndpoint(
                                    url=url,
                                    type=endpoint_type,
                                    confidence=min(confidence, 1.0),
                                    details={
                                        "status": response.status,
                                        "content_type": content_type,
                                    },
                                )
                            )
                            logger.info(
                                f"✅ Found endpoint: {url} (status: {response.status})"
                            )

                except Exception:
                    pass  # Path doesn't exist or error

        tasks = [check_path(path) for path in self.COMMON_PATHS]
        await asyncio.gather(*tasks)

    async def _check_robots_sitemap(
        self, session: aiohttp.ClientSession, base_url: str
    ):
        """Check robots.txt and sitemap for chat-related paths."""

        # Check robots.txt
        robots_url = urljoin(base_url, "/robots.txt")
        robots_content = await self._fetch_page(session, robots_url)

        if robots_content:
            # Look for disallowed chat paths (often hidden gems!)
            for line in robots_content.split("\n"):
                if "Disallow:" in line:
                    path = line.split(":", 1)[-1].strip()
                    if any(
                        kw in path.lower()
                        for kw in ["chat", "bot", "assistant", "support", "help"]
                    ):
                        full_url = urljoin(base_url, path)
                        self.found_endpoints.append(
                            ChatbotEndpoint(
                                url=full_url,
                                type="api",
                                confidence=0.7,
                                details={"source": "robots.txt"},
                            )
                        )
                        logger.info(f"🤖 Found in robots.txt: {full_url}")

    async def _check_common_subdomains(
        self, session: aiohttp.ClientSession, base_url: str
    ):
        """Check common chat-related subdomains."""
        parsed = urlparse(base_url)
        domain = parsed.netloc

        # Remove www if present
        if domain.startswith("www."):
            domain = domain[4:]

        subdomains = [
            f"chat.{domain}",
            f"support.{domain}",
            f"help.{domain}",
            f"bot.{domain}",
            f"assistant.{domain}",
            f"api.{domain}",
        ]

        for subdomain in subdomains:
            url = f"{parsed.scheme}://{subdomain}"
            try:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status in [200, 301, 302]:
                        self.found_endpoints.append(
                            ChatbotEndpoint(
                                url=url,
                                type="subdomain",
                                confidence=0.85,
                                details={"status": response.status},
                            )
                        )
                        logger.info(f"🌐 Found subdomain: {url}")
            except Exception:
                pass

    def get_summary(self) -> Dict:
        """Get discovery summary."""
        providers = set()
        types = {}

        for ep in self.found_endpoints:
            if ep.provider:
                providers.add(ep.provider)
            types[ep.type] = types.get(ep.type, 0) + 1

        return {
            "total_found": len(self.found_endpoints),
            "providers": list(providers),
            "types": types,
            "top_endpoints": [
                {
                    "url": ep.url,
                    "type": ep.type,
                    "provider": ep.provider,
                    "confidence": ep.confidence,
                }
                for ep in self.found_endpoints[:5]
            ],
        }


async def discover_chatbots(url: str) -> List[ChatbotEndpoint]:
    """
    Convenience function to discover chatbot endpoints.

    Args:
        url: Target URL to scan

    Returns:
        List of discovered ChatbotEndpoint objects
    """
    finder = ChatbotFinder()
    endpoints = await finder.discover(url)

    print(f"\n{'='*60}")
    print(f"🔍 Chatbot Discovery Results for {url}")
    print(f"{'='*60}")

    if endpoints:
        for i, ep in enumerate(endpoints[:10], 1):
            provider = f" ({ep.provider})" if ep.provider else ""
            print(f"  {i}. [{ep.confidence:.0%}] {ep.type.upper()}{provider}")
            print(f"     {ep.url}")
    else:
        print("  No chatbot endpoints found")

    summary = finder.get_summary()
    print(
        f"\n📊 Summary: {summary['total_found']} endpoints, providers: {summary['providers']}"
    )

    return endpoints


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chatbot_finder.py <url>")
        sys.exit(1)

    target = sys.argv[1]
    asyncio.run(discover_chatbots(target))
