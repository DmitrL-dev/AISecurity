# Troubleshooting

Common issues and how to solve them.

---

## Installation Issues

### ❌ `pip install rlm-toolkit` fails

**Symptoms:** Error during installation, missing dependencies.

**Solutions:**

1. **Upgrade pip:**
   ```bash
   pip install --upgrade pip
   ```

2. **Use Python 3.9+:**
   ```bash
   python --version  # Should be 3.9 or higher
   ```

3. **Install in fresh virtual environment:**
   ```bash
   python -m venv rlm-env
   source rlm-env/bin/activate  # Linux/Mac
   rlm-env\Scripts\activate     # Windows
   pip install rlm-toolkit
   ```

---

### ❌ Import errors after installation

**Symptoms:** `ModuleNotFoundError: No module named 'rlm_toolkit'`

**Solutions:**

1. Make sure you're in the correct virtual environment
2. Check if package is installed:
   ```bash
   pip show rlm-toolkit
   ```
3. Try reinstalling:
   ```bash
   pip uninstall rlm-toolkit
   pip install rlm-toolkit
   ```

---

## API Key Issues

### ❌ `AuthenticationError: Incorrect API key`

**Symptoms:** Error when creating RLM instance.

**Solutions:**

1. **Check environment variable:**
   ```bash
   # Linux/Mac
   echo $OPENAI_API_KEY
   
   # Windows PowerShell
   echo $env:OPENAI_API_KEY
   ```

2. **Set API key correctly:**
   ```bash
   # Linux/Mac (add to ~/.bashrc or ~/.zshrc)
   export OPENAI_API_KEY="sk-..."
   
   # Windows PowerShell
   $env:OPENAI_API_KEY = "sk-..."
   ```

3. **Pass API key directly:**
   ```python
   rlm = RLM.from_openai("gpt-4o", api_key="sk-...")
   ```

4. **Using .env file:**
   ```bash
   # .env file
   OPENAI_API_KEY=sk-...
   ```
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

---

### ❌ Where do I get an API key?

| Provider | Get API Key |
|----------|-------------|
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) |
| Google | [aistudio.google.com](https://aistudio.google.com) |
| Groq | [console.groq.com](https://console.groq.com) |

---

## Rate Limits

### ❌ `RateLimitError: Too many requests`

**Symptoms:** Error after many requests.

**Solutions:**

1. **Add delay between requests:**
   ```python
   import time
   
   for item in items:
       response = rlm.run(item)
       time.sleep(1)  # Wait 1 second
   ```

2. **Use exponential backoff:**
   ```python
   from rlm_toolkit.utils import with_retry
   
   @with_retry(max_attempts=3, backoff_factor=2)
   def safe_request(prompt):
       return rlm.run(prompt)
   ```

3. **Batch your requests** instead of one-by-one

4. **Upgrade your API tier** for higher limits

---

## Memory Issues

### ❌ `OutOfMemoryError` with large documents

**Solutions:**

1. **Use smaller chunks:**
   ```python
   splitter = RecursiveTextSplitter(chunk_size=500)  # Smaller chunks
   ```

2. **Enable InfiniRetri:**
   ```python
   config = RLMConfig(enable_infiniretri=True)
   rlm = RLM.from_openai("gpt-4o", config=config)
   ```

3. **Process in batches:**
   ```python
   for batch in chunks(documents, size=10):
       process_batch(batch)
   ```

---

## Context Too Long

### ❌ `ContextLengthExceeded: Maximum context length exceeded`

**Symptoms:** Error when prompt is too large.

**Solutions:**

1. **Check your prompt length:**
   ```python
   import tiktoken
   enc = tiktoken.encoding_for_model("gpt-4o")
   tokens = len(enc.encode(your_prompt))
   print(f"Tokens: {tokens}")
   ```

2. **Use a model with larger context:**
   ```python
   # GPT-4o: 128K tokens
   # Claude 3: 200K tokens
   rlm = RLM.from_anthropic("claude-3-sonnet")
   ```

3. **Enable InfiniRetri** for automatic context management

4. **Summarize long texts** before sending

---

## Connection Issues

### ❌ `ConnectionError: Failed to connect to API`

**Solutions:**

1. **Check internet connection**

2. **Check for proxy issues:**
   ```python
   import os
   os.environ["HTTP_PROXY"] = "http://proxy:8080"
   os.environ["HTTPS_PROXY"] = "http://proxy:8080"
   ```

3. **Increase timeout:**
   ```python
   rlm = RLM.from_openai("gpt-4o", timeout=60)
   ```

---

## Ollama (Local LLMs)

### ❌ Can't connect to Ollama

**Solutions:**

1. **Make sure Ollama is running:**
   ```bash
   ollama serve
   ```

2. **Check if model is downloaded:**
   ```bash
   ollama list
   ollama pull llama3
   ```

3. **Specify correct URL:**
   ```python
   rlm = RLM.from_ollama("llama3", base_url="http://localhost:11434")
   ```

---

## Getting Help

If your issue isn't listed here:

1. **Check the [GitHub Issues](https://github.com/sentinel/rlm-toolkit/issues)**
2. **Search documentation** using the search bar
3. **Ask in [Discussions](https://github.com/sentinel/rlm-toolkit/discussions)**
4. **Create a new issue** with:
   - RLM-Toolkit version (`pip show rlm-toolkit`)
   - Python version (`python --version`)
   - Full error message
   - Minimal code to reproduce

---

## See Also

- [Quickstart](./quickstart.md) — Getting started guide
- [Glossary](./glossary.md) — Understand the terminology
- [API Reference](./reference/) — Detailed API docs
