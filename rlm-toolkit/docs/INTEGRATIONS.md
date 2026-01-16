# RLM-Toolkit Integration Catalog

> **287+ production-ready integrations** across LLM providers, document loaders, vector stores, embeddings, tools, callbacks, and splitters.

---

## 📊 Summary

| Category | Count | Status |
|----------|-------|--------|
| **LLM Providers** | 75 | ✅ Production |
| **Document Loaders** | 135+ | ✅ Production |
| **Vector Stores** | 20+ | ✅ Production |
| **Embeddings** | 15+ | ✅ Production |
| **Tools** | 20+ | ✅ Production |
| **Splitters** | 10 | ✅ Production |
| **Callbacks** | 12 | ✅ Production |
| **Total** | **287+** | ✅ |

---

## 🤖 LLM Providers (75)

### Cloud Providers
| Provider | Models | Auth |
|----------|--------|------|
| OpenAI | GPT-4o, GPT-4, GPT-3.5 | `OPENAI_API_KEY` |
| Anthropic | Claude 3.5, Claude 3 | `ANTHROPIC_API_KEY` |
| Google | Gemini Pro, Gemini Ultra | `GOOGLE_API_KEY` |
| Mistral | Mistral Large, Mixtral | `MISTRAL_API_KEY` |
| Cohere | Command R+, Embed | `COHERE_API_KEY` |
| Together | 100+ open models | `TOGETHER_API_KEY` |
| Fireworks | Llama, Mixtral | `FIREWORKS_API_KEY` |
| Groq | Llama 3, Mixtral | `GROQ_API_KEY` |
| Perplexity | pplx-7b, pplx-70b | `PERPLEXITY_API_KEY` |
| Replicate | 1000+ models | `REPLICATE_API_TOKEN` |
| DeepInfra | Llama, Falcon | `DEEPINFRA_API_KEY` |
| Anyscale | Ray Serve | `ANYSCALE_API_KEY` |
| AI21 | Jurassic-2 | `AI21_API_KEY` |
| Writer | Palmyra | `WRITER_API_KEY` |
| Reka | Reka Core/Flash | `REKA_API_KEY` |
| Voyage | Embeddings | `VOYAGE_API_KEY` |
| DeepSeek | DeepSeek V2/V3 | `DEEPSEEK_API_KEY` |
| Moonshot | Kimi | `MOONSHOT_API_KEY` |
| Zhipu | GLM-4 | `ZHIPU_API_KEY` |
| Minimax | abab | `MINIMAX_API_KEY` |
| 01.AI | Yi | `01AI_API_KEY` |
| Inflection | Pi | `INFLECTION_API_KEY` |

### Local/Self-Hosted
| Provider | Type |
|----------|------|
| Ollama | Local inference |
| vLLM | High-throughput GPU |
| TGI | HuggingFace Text Gen |
| LlamaCpp | CPU/Metal |
| LocalAI | OpenAI-compatible |
| Tabby | Local GPU |
| LM Studio | Desktop |
| GPT4All | CPU optimized |
| Jan | Desktop app |
| llama-cpp-python | Python bindings |

### Enterprise
| Provider | Platform |
|----------|----------|
| Azure OpenAI | Azure |
| AWS Bedrock | AWS |
| Google Vertex | GCP |
| IBM watsonx | IBM Cloud |
| Aleph Alpha | EU Cloud |
| OCI Generative AI | Oracle |
| SAP AI Core | SAP |
| Snowflake Cortex | Snowflake |
| Databricks | Databricks |

---

## 📄 Document Loaders (135+)

### CRM & Sales
`HubSpot` `Salesforce` `Pipedrive` `Zoho` `Dynamics365` `Freshsales` `Close` `SugarCRM`

### Project Management
`Jira` `Asana` `Trello` `Linear` `ClickUp` `Monday` `Basecamp` `Wrike` `Smartsheet` `Notion` `Coda` `Airtable`

### Communication
`Slack` `Discord` `Telegram` `Mattermost` `Zulip` `WhatsApp` `RocketChat` `Microsoft Teams`

### Email
`Gmail` `IMAP` `Outlook` `Exchange`

### Documentation & Wiki
`Confluence` `Notion` `GitBook` `MediaWiki` `MkDocs` `ReadMe` `DokuWiki` `BookStack`

### Developer Tools
`GitHub` `GitLab` `Bitbucket` `Jira` `YouTrack` `Sentry` `Azure DevOps` `Redmine` `Bugzilla` `Phabricator`

### Cloud Storage
`S3` `GCS` `Azure Blob` `Dropbox` `Google Drive` `OneDrive` `Box`

### Databases
`PostgreSQL` `MySQL` `SQLite` `MongoDB` `BigQuery` `Snowflake` `Redshift` `DynamoDB` `Cassandra` `Neo4j` `ArangoDB`

### Data & APIs
`REST API` `GraphQL` `RSS` `Elasticsearch` `Wikipedia` `arXiv` `PubMed` `Hacker News` `Reddit`

### E-Commerce
`Shopify` `WooCommerce` `Magento` `BigCommerce` `Stripe`

### Analytics
`Mixpanel` `Metabase` `Tableau` `PowerBI` `Datadog` `Google Analytics` `Segment` `Looker` `Amplitude`

### HR & Recruiting
`Greenhouse` `Lever` `BambooHR` `Workday`

### File Formats
`PDF` `Word` `Excel` `PowerPoint` `CSV` `JSON` `XML` `HTML` `Markdown` `EPUB` `TOML` `YAML` `INI` `Log` `IPYNB`

### Media
`Image (OCR)` `Audio (Whisper)` `Video` `Subtitles (SRT/VTT)` `YouTube`

---

## 🗃️ Vector Stores (20+)

### Cloud-Native
| Store | Type |
|-------|------|
| Pinecone | Managed |
| Weaviate | Managed/Self-hosted |
| Qdrant | Managed/Self-hosted |
| Milvus | Self-hosted |
| Chroma | Local/Cloud |
| Upstash | Serverless Redis |
| Neon | Serverless Postgres |

### Enterprise
| Store | Platform |
|-------|----------|
| Elasticsearch | Elastic |
| OpenSearch | AWS |
| MongoDB Atlas | MongoDB |
| Azure AI Search | Azure |
| Vertex AI | Google |
| Astra DB | DataStax |
| SingleStore | SingleStore |
| Snowflake Cortex | Snowflake |
| Databricks | Databricks |

### Specialized
| Store | Use Case |
|-------|----------|
| Vespa | Large-scale |
| Marqo | Tensor search |
| Redis | Caching + search |
| Supabase | Postgres + pgvector |
| Typesense | Typo-tolerant |

### Local/Open-Source
| Store | Type |
|-------|------|
| HNSWlib | ANN index |
| Annoy | Spotify ANN |
| FAISS | Facebook ANN |
| ScaNN | Google ANN |
| LanceDB | Embedded |
| USearch | Single-file |

---

## 🧬 Embeddings (15+)

### Cloud APIs
| Provider | Models |
|----------|--------|
| OpenAI | text-embedding-3-large/small, ada-002 |
| Cohere | embed-english-v3, embed-multilingual |
| Voyage | voyage-2, voyage-large-2 |
| Jina | jina-embeddings-v2 |
| Mistral | mistral-embed |
| Together | m2-bert, bge |
| Google | textembedding-gecko |

### Local Models
| Model | Size |
|-------|------|
| BGE | 335M-1.3B |
| E5 | 335M-1.5B |
| GTE | 335M-1.5B |
| Instructor | 335M |
| Nomic | 137M |
| all-MiniLM | 23M |
| LaBSE | 471M (multilingual) |

### Specialized
| Model | Use Case |
|-------|----------|
| CLIP | Image+Text |
| ColBERT | Late interaction |
| SPLADE | Sparse |

---

## 🔧 Tools (20+)

| Category | Tools |
|----------|-------|
| **Weather** | OpenWeatherMap |
| **Translation** | Google Translate, DeepL |
| **Image** | DALL-E 3, Stable Diffusion |
| **Audio** | Whisper, TTS |
| **Email** | Gmail, SendGrid |
| **Calendar** | Google Calendar |
| **News** | NewsAPI |
| **Social** | Twitter/X Search |
| **Finance** | Yahoo Finance, CoinGecko |
| **Utility** | DateTime, UUID, Hash, Base64, JSON |

---

## ✂️ Text Splitters (10)

| Splitter | Use Case |
|----------|----------|
| CharacterSplitter | Fixed chunks |
| RecursiveSplitter | Smart splitting |
| TokenSplitter | Token-aware |
| SemanticSplitter | Embedding-based |
| MarkdownSplitter | MD sections |
| HTMLSplitter | HTML structure |
| CodeSplitter | AST-aware |
| LatexSplitter | LaTeX sections |
| JSONSplitter | JSON structure |
| SentenceSplitter | By sentences |

---

## 📡 Callbacks (12)

| Callback | Purpose |
|----------|---------|
| ConsoleCallback | Debug logging |
| FileCallback | Log to file |
| WandBCallback | Weights & Biases |
| MLflowCallback | MLflow tracking |
| LangfuseCallback | Langfuse observability |
| LangSmithCallback | LangSmith tracing |
| PhoenixCallback | Arize Phoenix |
| HeliconeCallback | Helicone analytics |
| OpenTelemetryCallback | OTel tracing |
| PrometheusCallback | Metrics |
| WebhookCallback | HTTP webhooks |
| CompositeCallback | Multiple callbacks |

---

## 📦 Installation

```bash
# Core only
pip install rlm-toolkit

# With all integrations
pip install rlm-toolkit[all]

# Specific categories
pip install rlm-toolkit[loaders]
pip install rlm-toolkit[vectorstores]
pip install rlm-toolkit[embeddings]
pip install rlm-toolkit[tools]
```

---

*Last updated: 2026-01-17*
