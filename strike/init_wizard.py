"""
🏰 SENTINEL Init Wizard v2
Modes: Quick Start (interactive) + Advanced (config template)
"""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

# =============================================================================
# CONFIGURATION
# =============================================================================

MODES = {
    "defense": {"icon": "🛡️", "name": "Defense", "desc": "Protect your LLM"},
    "attack": {"icon": "🐉", "name": "Attack", "desc": "Red team testing"},
    "gateway": {"icon": "⚡", "name": "Gateway", "desc": "Production proxy"},
}

TARGETS = {
    "api": "OpenAI/Anthropic API",
    "langchain": "LangChain/LlamaIndex",
    "rag": "RAG pipeline",
    "agents": "AI Agents (MCP/A2A)",
    "local": "Local LLM (Ollama)",
}

LEVELS = {
    "quick": {"engines": 10, "latency": "<5ms"},
    "standard": {"engines": 50, "latency": "~30ms"},
    "paranoid": {"engines": 200, "latency": "~100ms"},
}

MODELS = {
    "builtin": "Встроенные engines",
    "qwen3guard": "🛡️ Qwen3Guard",
    "aprielguard": "🧠 AprielGuard",
    "full": "🔬 Full Stack (+ DeepSeek)",
}


# =============================================================================
# GENERATORS
# =============================================================================


def gen_defense_config(targets, level, model):
    """Generate sentinel/config.py."""
    targets_str = ", ".join(f'"{t}"' for t in targets)
    model_cfg = {
        "builtin": "None",
        "qwen3guard": '"qwen3guard"',
        "aprielguard": '"aprielguard"',
        "full": '{"filter": "qwen3guard", "deep": "aprielguard", "math": "deepseek-v3"}',
    }
    return f'''"""
SENTINEL Defense Configuration

Usage:
    from sentinel import guard, scan
    
    @guard
    def call_llm(prompt):
        return your_llm_call(prompt)
"""

from sentinel import SENTINEL

sentinel = SENTINEL(
    level="{level}",
    targets=[{targets_str}],
    model={model_cfg[model]},
)

guard = sentinel.guard
scan = sentinel.scan
'''


def gen_attack_config(targets, mode):
    """Generate strike_config.yaml."""
    return f"""# SENTINEL Strike Configuration
# Usage: strike attack -t YOUR_URL

strike:
  version: "1.0"
  targets: {targets}
  mode: {mode}
  payloads_path: ~/.sentinel/payloads/
  output:
    format: html
    path: ./reports/
"""


def gen_gateway_config(backend):
    """Generate docker-compose.yml."""
    return f"""# SENTINEL Gateway
# Usage: docker-compose up -d

version: "3.8"

services:
  gateway:
    image: sentinel-ai/gateway:latest
    ports:
      - "8080:8080"
    environment:
      - BACKEND_PROVIDER={backend}
      - SECURITY_LEVEL=standard

  brain:
    image: sentinel-ai/brain:latest
    environment:
      - ENGINES=50
"""


def gen_advanced_config():
    """Generate full sentinel.yaml template."""
    return """# SENTINEL — Advanced Configuration
# Для сложных сценариев: множество LLM, RAG, агентов
# Docs: https://github.com/SENTINEL-AI

targets:
  llm:
    - name: openai-prod
      provider: openai
      api_key_env: OPENAI_API_KEY
      
    - name: anthropic
      provider: anthropic
      
    # Добавьте свои...

  local:
    - name: ollama
      url: http://localhost:11434
      
  rag:
    - name: docs-rag
      type: langchain
      # Для множества: pattern: "rag-*"
      
  agents:
    - name: support-agent
      protocol: mcp
      endpoint: http://localhost:3000

security:
  level: standard
  models:
    filter: qwen3guard
    deep: aprielguard
    math: deepseek-v3
  checks:
    - injection
    - jailbreak
    - pii
    - rag_poisoning

gateway:
  enabled: false
  port: 8080

logging:
  level: info
  output: ./logs/sentinel.log
"""


# =============================================================================
# WIZARD FLOWS
# =============================================================================


def multi_select(prompt_text, options, hint="Введи номера через пробел"):
    """Multi-select prompt."""
    console.print(f"\n[bold]{prompt_text}[/]")
    console.print(f"[dim]{hint}[/]\n")

    table = Table(show_header=False, box=None)
    items = list(options.items())
    for i, (key, desc) in enumerate(items, 1):
        table.add_row(f"  [{i}]", desc)
    console.print(table)

    raw = Prompt.ask("\nВыбор", default="1")
    choices = raw.replace(",", " ").split()

    selected = []
    for c in choices:
        try:
            idx = int(c.strip()) - 1
            if 0 <= idx < len(items):
                selected.append(items[idx][0])
        except ValueError:
            pass

    return selected if selected else [items[0][0]]


def single_select(prompt_text, options):
    """Single-select prompt."""
    console.print(f"\n[bold]{prompt_text}[/]\n")

    table = Table(show_header=False, box=None)
    items = list(options.items())
    for i, (key, val) in enumerate(items, 1):
        if isinstance(val, dict):
            table.add_row(
                f"  [{i}]",
                key.capitalize(),
                f"[dim]{val.get('engines', '')} engines[/]",
            )
        else:
            table.add_row(f"  [{i}]", val)
    console.print(table)

    valid = [str(i) for i in range(1, len(items) + 1)]
    choice = Prompt.ask("\nВыбор", choices=valid, default="1")
    return items[int(choice) - 1][0]


def run_defense_wizard():
    """Defense mode wizard."""
    console.print(Panel.fit("[bold green]🛡️ Defense Setup[/]", border_style="green"))

    targets = multi_select("Что защищаем?", TARGETS)
    console.print(f"[green]→ Выбрано: {', '.join(targets)}[/]")

    level = single_select("Уровень защиты?", LEVELS)
    model = single_select("Модель анализа?", MODELS)

    # Generate
    sentinel_dir = Path("./sentinel")
    sentinel_dir.mkdir(exist_ok=True)

    config = gen_defense_config(targets, level, model)
    (sentinel_dir / "config.py").write_text(config, encoding="utf-8")
    (sentinel_dir / "__init__.py").write_text(
        "from .config import guard, scan\n", encoding="utf-8"
    )

    console.print(f"\n[green]✅ Created:[/] sentinel/config.py")
    console.print(
        Panel(
            "[bold]Добавь в код:[/]\n"
            "  [cyan]from sentinel import guard[/]\n\n"
            "  [cyan]@guard[/]\n"
            "  [cyan]def my_llm(prompt): ...[/]",
            title="Next Steps",
            border_style="green",
        )
    )
    return "sentinel/config.py"


def run_attack_wizard():
    """Attack mode wizard."""
    console.print(Panel.fit("[bold red]🐉 Attack Setup[/]", border_style="red"))

    target_opts = {"api": "Свой API", "url": "URL", "ctf": "CTF"}
    targets = multi_select("Что тестируем?", target_opts)

    mode_opts = {
        "quick": "Quick (10)",
        "standard": "Standard (100)",
        "full": "Full HYDRA (39K+)",
    }
    mode = single_select("Режим?", mode_opts)

    config = gen_attack_config(targets, mode)
    Path("strike_config.yaml").write_text(config, encoding="utf-8")

    console.print(f"\n[green]✅ Created:[/] strike_config.yaml")
    console.print(
        Panel(
            "[cyan]strike attack -t YOUR_URL[/]", title="Next Steps", border_style="red"
        )
    )
    return "strike_config.yaml"


def run_gateway_wizard():
    """Gateway mode wizard."""
    console.print(Panel.fit("[bold cyan]⚡ Gateway Setup[/]", border_style="cyan"))

    backends = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "azure": "Azure",
        "custom": "Custom",
    }
    backend = single_select("Backend LLM?", backends)

    config = gen_gateway_config(backend)
    Path("docker-compose.yml").write_text(config, encoding="utf-8")

    console.print(f"\n[green]✅ Created:[/] docker-compose.yml")
    console.print(
        Panel("[cyan]docker-compose up -d[/]", title="Next Steps", border_style="cyan")
    )
    return "docker-compose.yml"


def run_advanced_wizard():
    """Advanced mode - generate full config template."""
    console.print(
        Panel.fit(
            "[bold magenta]📋 Advanced Configuration[/]\n"
            "[dim]Полный шаблон для Enterprise[/]",
            border_style="magenta",
        )
    )

    config = gen_advanced_config()
    Path("sentinel.yaml").write_text(config, encoding="utf-8")

    console.print(f"\n[green]✅ Created:[/] sentinel.yaml")
    console.print(
        Panel(
            "[bold]Отредактируй sentinel.yaml:[/]\n"
            "  • Добавь свои LLM endpoints\n"
            "  • Настрой RAG pipelines\n"
            "  • Укажи агентов\n\n"
            "[dim]Docs: https://github.com/SENTINEL-AI/docs/config[/]",
            title="Next Steps",
            border_style="magenta",
        )
    )
    return "sentinel.yaml"


# =============================================================================
# MAIN
# =============================================================================


def run_wizard(modes=None):
    """Main entry point."""
    console.print()
    console.print(
        Panel.fit(
            "[bold]🏰 SENTINEL AI Security[/]\n" "[dim]Setup Wizard v2[/]",
            border_style="bright_white",
        )
    )

    # First: Quick Start or Advanced?
    console.print("\n[bold]Режим настройки?[/]\n")
    console.print("  [1] 🚀 Quick Start — Интерактивный wizard")
    console.print("  [2] 📋 Advanced — Полный шаблон конфига\n")

    setup_mode = Prompt.ask("Выбор", choices=["1", "2"], default="1")

    if setup_mode == "2":
        return run_advanced_wizard()

    # Quick Start: select components
    if not modes:
        console.print("\n[bold]Какие компоненты?[/]")
        console.print("[dim]Введи номера через пробел[/]\n")

        table = Table(show_header=False, box=None)
        mode_list = list(MODES.items())
        for i, (key, info) in enumerate(mode_list, 1):
            table.add_row(
                f"  [{i}]", f"{info['icon']} {info['name']}", f"[dim]{info['desc']}[/]"
            )
        console.print(table)

        raw = Prompt.ask("\nВыбор", default="1")
        choices = raw.replace(",", " ").split()

        modes = []
        for c in choices:
            try:
                idx = int(c.strip()) - 1
                if 0 <= idx < len(mode_list):
                    modes.append(mode_list[idx][0])
            except ValueError:
                pass

        if not modes:
            modes = ["defense"]

        console.print(f"\n[green]→ {', '.join(m.upper() for m in modes)}[/]")

    # Run each wizard
    results = []
    for mode in modes:
        if mode == "defense":
            results.append(run_defense_wizard())
        elif mode == "attack":
            results.append(run_attack_wizard())
        elif mode == "gateway":
            results.append(run_gateway_wizard())

    # Summary
    if len(results) > 1:
        console.print()
        console.print(
            Panel(
                "[bold]📦 Созданные файлы:[/]\n"
                + "\n".join(f"  • {r}" for r in results),
                title="[bold green]✅ Complete[/]",
                border_style="green",
            )
        )

    return results


if __name__ == "__main__":
    import sys

    modes = [m for m in sys.argv[1:] if m in MODES] or None
    run_wizard(modes)
