"""
SENTINEL Strike CLI — Command Line Interface
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import Optional
from enum import Enum
from pathlib import Path

app = typer.Typer(
    name="strike",
    help="🎯 SENTINEL Strike — AI Red Team Platform",
    no_args_is_help=True,
)
console = Console(legacy_windows=True)


class ScanMode(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    FULL = "full"
    STEALTH = "stealth"


class TargetMode(str, Enum):
    EXTERNAL = "external"
    INTERNAL = "internal"
    BOTH = "both"


class AttackMode(str, Enum):
    """Attack intensity mode."""
    QUICK = "quick"      # 5 min, 20 vectors
    STANDARD = "standard"  # 30 min, 100 vectors
    FULL = "full"        # 60 min, all vectors
    MARATHON = "marathon"  # 4 hours, adaptive


# ==================== NEW: ATTACK COMMAND ====================

@app.command()
def attack(
    target: str = typer.Option(..., "--target", "-t",
                               help="Target API endpoint URL"),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", "-k", help="API key"),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Target model"),
    duration: int = typer.Option(
        60, "--duration", "-d", help="Duration in minutes"),
    mode: AttackMode = typer.Option(
        AttackMode.STANDARD, "--mode", help="Attack mode"),
    stealth: bool = typer.Option(
        True, "--stealth/--no-stealth", help="Enable stealth"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output report file"),
    resume: Optional[str] = typer.Option(
        None, "--resume", "-r", help="Resume session ID"),
):
    """
    🎯 Launch autonomous LLM attack.

    Examples:
        strike attack --target https://api.openai.com/v1/chat/completions
        strike attack -t https://api.target.com -d 30 --no-stealth
        strike attack -t URL --mode marathon --stealth
    """
    import asyncio
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.live import Live
    from rich.table import Table

    from .orchestrator import StrikeOrchestrator, StrikeConfig
    from .session import SessionManager

    # Mode presets
    mode_presets = {
        AttackMode.QUICK: {"duration": 5, "max_iter": 20},
        AttackMode.STANDARD: {"duration": 30, "max_iter": 100},
        AttackMode.FULL: {"duration": 60, "max_iter": 500},
        AttackMode.MARATHON: {"duration": 240, "max_iter": 2000},
    }

    preset = mode_presets[mode]
    actual_duration = duration if duration != 60 else preset["duration"]

    # Banner
    console.print(
        Panel.fit(
            f"[bold red]🎯 SENTINEL Strike v3.0[/bold red]\n\n"
            f"Target: {target}\n"
            f"Mode: {mode.value.upper()}\n"
            f"Duration: {actual_duration} min\n"
            f"Stealth: {'✅ ON' if stealth else '⚡ OFF'}\n"
            f"Model: {model or 'auto-detect'}",
            title="Autonomous Attack",
            border_style="red",
        )
    )

    config = StrikeConfig(
        target_url=target,
        target_api_key=api_key,
        target_model=model,
        duration_minutes=actual_duration,
        max_iterations=preset["max_iter"],
        stealth_enabled=stealth,
    )

    orchestrator = StrikeOrchestrator(config)

    # Resume if specified
    if resume:
        sm = SessionManager()
        data = sm.resume(resume)
        if data:
            console.print(f"[green]✓ Resumed session {resume}[/green]")
        else:
            console.print(f"[red]✗ Session {resume} not found[/red]")
            return

    async def run_attack():
        return await orchestrator.run()

    # Run with live status
    console.print("\n[bold]Starting attack...[/bold]\n")

    try:
        report = asyncio.run(run_attack())

        # Results table
        table = Table(title="🎯 Attack Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Target", target)
        table.add_row("Duration", f"{report.iterations} iterations")
        table.add_row("Successful Attacks",
                      f"[bold red]{report.successful_attacks}[/bold red]")
        table.add_row("Success Rate", f"{report.success_rate:.1%}")
        table.add_row(
            "Vulnerabilities", f"[bold yellow]{len(report.vulnerabilities)}[/bold yellow]")

        console.print(table)

        # Show findings
        if report.vulnerabilities:
            console.print("\n[bold]🔓 Findings:[/bold]")
            for i, vuln in enumerate(report.vulnerabilities[:10], 1):
                console.print(
                    f"  {i}. [red]{vuln.get('vector', 'unknown')}[/red] ({vuln.get('severity', 'medium')})")

        # Save report
        if output:
            import json
            Path(output).write_text(json.dumps({
                "target": report.target,
                "started_at": report.started_at.isoformat(),
                "completed_at": report.completed_at.isoformat() if report.completed_at else None,
                "iterations": report.iterations,
                "successful_attacks": report.successful_attacks,
                "success_rate": report.success_rate,
                "vulnerabilities": report.vulnerabilities,
            }, indent=2))
            console.print(f"\n[dim]Report saved to {output}[/dim]")

        return report

    except KeyboardInterrupt:
        console.print(
            "\n[yellow]⏸️ Attack paused. Use --resume to continue.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")


# ==================== API SERVER COMMAND ====================

@app.command()
def api(
    port: int = typer.Option(8001, "--port", "-p", help="API server port"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
):
    """Launch REST API server."""
    console.print(
        Panel.fit(
            f"[bold cyan]🌐 Strike API Server[/bold cyan]\n\n"
            f"URL: http://{host}:{port}\n"
            f"Docs: http://localhost:{port}/docs",
            title="Starting API",
            border_style="cyan",
        )
    )

    import uvicorn
    uvicorn.run("strike.api:app", host=host, port=port, reload=False)


# ==================== ORIGINAL COMMANDS ====================

@app.command()
def config(
    target: str = typer.Option(..., "--target", "-t",
                               help="Target API endpoint URL"),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", "-k", help="API key for authentication"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Target model name"
    ),
    mode: TargetMode = typer.Option(
        TargetMode.EXTERNAL, "--mode", help="Target mode"),
):
    """Configure target for penetration testing."""
    console.print(
        Panel.fit(
            f"🎯 [bold]Target Configuration[/bold]\n\n"
            f"URL: {target}\n"
            f"Mode: {mode.value}\n"
            f"Model: {model or 'auto-detect'}",
            title="SENTINEL Strike",
            border_style="red",
        )
    )
    # Save config to ~/.sentinel-strike/config.yaml
    import yaml

    config_dir = Path.home() / ".sentinel-strike"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"

    config_data = {
        "target": target,
        "api_key": api_key,
        "model": model,
        "mode": mode.value,
    }

    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f)

    console.print(f"[green]✓ Config saved to {config_path}[/green]")


@app.command()
def scan(
    target: str = typer.Option(..., "--target", "-t",
                               help="Target API endpoint URL"),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", "-k", help="API key"),
    mode: TargetMode = typer.Option(
        TargetMode.EXTERNAL, "--mode", "-m", help="Scan mode"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Attack category filter"
    ),
    timeout: int = typer.Option(
        30, "--timeout", "-T", help="Request timeout in seconds"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file (json)"
    ),
):
    """Run vulnerability scan against target."""
    import asyncio
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from .attacks import ATTACK_COUNTS

    console.print(
        Panel.fit(
            f"🔍 [bold red]Starting Scan[/bold red]\n\n"
            f"Target: {target}\n"
            f"Mode: {mode.value}\n"
            f"Category: {category or 'all'}\n"
            f"Attacks: {ATTACK_COUNTS['Total']} available",
            title="SENTINEL Strike",
            border_style="red",
        )
    )

    async def run_scan():
        if mode == TargetMode.EXTERNAL or mode == TargetMode.BOTH:
            from .recon import run_external_scan

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "Running external scan...", total=None)
                categories = [category] if category else None
                result = await run_external_scan(target, api_key, categories)
                progress.remove_task(task)

            # Show results
            table = Table(title="🌐 External Scan Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Attacks Run", str(result.attacks_run))
            table.add_row(
                "Successful", f"[red]{result.attacks_successful}[/red]")
            table.add_row(
                "Blocked", f"[green]{result.attacks_blocked}[/green]")
            table.add_row(
                "Critical Findings", f"[bold red]{result.critical_findings}[/bold red]"
            )
            table.add_row("High Findings",
                          f"[yellow]{result.high_findings}[/yellow]")

            console.print(table)

            if output:
                from pathlib import Path
                import json

                Path(output).write_text(
                    json.dumps(
                        {
                            "mode": "external",
                            "target": target,
                            "attacks_run": result.attacks_run,
                            "successful": result.attacks_successful,
                            "critical": result.critical_findings,
                            "results": [
                                {"id": r.attack_id, "status": r.status.value}
                                for r in result.results
                            ],
                        },
                        indent=2,
                    )
                )
                console.print(f"\n[dim]Results saved to {output}[/dim]")

        if mode == TargetMode.INTERNAL or mode == TargetMode.BOTH:
            from .recon import run_internal_scan

            console.print("\n[bold]🏠 Running internal scan...[/bold]")
            categories = [category] if category else None
            result = await run_internal_scan(target, api_key, categories)

            table = Table(title="🏠 Internal Scan Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Attacks Run", str(result.attacks_run))
            table.add_row(
                "Successful", f"[red]{result.attacks_successful}[/red]")
            table.add_row("MCP Servers Found", str(len(result.mcp_servers)))
            table.add_row(
                "Critical Findings", f"[bold red]{result.critical_findings}[/bold red]"
            )

            console.print(table)

    asyncio.run(run_scan())


@app.command()
def pentest(
    mode: ScanMode = typer.Option(
        ScanMode.FULL, "--mode", "-m", help="Test mode"),
    target_mode: TargetMode = typer.Option(
        TargetMode.BOTH, "--target-mode", help="External/Internal"
    ),
    report: str = typer.Option(
        "html", "--report", "-r", help="Report format (html, json, pdf)"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output directory"
    ),
):
    """Run full penetration test with detailed reporting."""
    console.print(
        Panel.fit(
            f"🎯 [bold red]Full Penetration Test[/bold red]\n\n"
            f"Mode: {mode.value}\n"
            f"Target: {target_mode.value}\n"
            f"Report: {report}",
            title="SENTINEL Strike",
            border_style="red",
        )
    )
    # Execute full pentest using attack command
    import asyncio
    from .orchestrator import StrikeOrchestrator, StrikeConfig

    # Load target from config
    config_path = Path.home() / ".sentinel-strike" / "config.yaml"
    if config_path.exists():
        import yaml

        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        target_url = cfg.get("target", "")
        api_key = cfg.get("api_key")
    else:
        console.print("[red]No config. Run 'strike config' first.[/red]")
        return

    mode_durations = {
        ScanMode.QUICK: 5,
        ScanMode.STANDARD: 30,
        ScanMode.FULL: 60,
        ScanMode.STEALTH: 120,
    }

    config_obj = StrikeConfig(
        target_url=target_url,
        target_api_key=api_key,
        duration_minutes=mode_durations[mode],
        stealth_enabled=(mode == ScanMode.STEALTH),
    )

    orchestrator = StrikeOrchestrator(config_obj)

    async def run():
        return await orchestrator.run()

    report_data = asyncio.run(run())

    # Generate report in requested format
    output_dir = Path(output or "./reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"pentest_{report_data.started_at.strftime('%Y%m%d_%H%M%S')}"

    if report == "json":
        import json

        (output_dir / f"{filename}.json").write_text(
            json.dumps(vars(report_data), indent=2, default=str)
        )
    elif report == "html":
        _generate_html_report(report_data, output_dir / f"{filename}.html")

    console.print(f"[green]✓ Report saved to {output_dir}/{filename}.{report}[/green]")


@app.command()
def attacks(
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by category"
    ),
):
    """List all available attacks."""
    from .attacks import ATTACK_LIBRARY, ATTACK_COUNTS

    # Filter by category if specified
    filtered = ATTACK_LIBRARY
    if category:
        cat_lower = category.lower()
        filtered = [a for a in ATTACK_LIBRARY if a.category.lower()
                    == cat_lower]

    def safe_str(s: str) -> str:
        """Sanitize string for console output."""
        return s.encode("ascii", errors="replace").decode("ascii")

    try:
        table = Table(
            title=f"Available Attacks ({len(filtered)}/{ATTACK_COUNTS['Total']})"
        )
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Name", style="white", max_width=30)
        table.add_column("Category", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("ATLAS", style="magenta")

        for attack in filtered:
            atlas = attack.mitre_atlas or "-"
            table.add_row(
                attack.id,
                safe_str(attack.name[:30]),
                attack.category,
                attack.severity.value,
                atlas,
            )
        console.print(table)
    except Exception:
        # Plain text fallback for Windows encoding issues
        print(
            f"\nAvailable Attacks ({len(filtered)}/{ATTACK_COUNTS['Total']})")
        print("-" * 60)
        for attack in filtered:
            atlas = attack.mitre_atlas or "-"
            name = safe_str(attack.name[:25])
            print(f"  {attack.id:6} | {name:25} | {attack.category:12} | {atlas}")
        print("-" * 60)

    print("\nCategories: Injection, Jailbreak, Strange Math, Agentic, Exfiltration")
    print("Use --category to filter, e.g. strike attacks --category jailbreak")


@app.command()
def report(
    input_file: str = typer.Argument(..., help="Input JSON results file"),
    format: str = typer.Option("html", "--format", "-f", help="Output format"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
):
    """Generate report from scan results."""
    console.print(f"📊 Generating {format.upper()} report from {input_file}...")
    # Generate report from scan results
    import json
    from datetime import datetime

    input_path = Path(input_file)
    if not input_path.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        return

    data = json.loads(input_path.read_text())
    output_path = Path(output or f"report.{format}")

    if format == "html":
        _generate_html_report_from_data(data, output_path)
    elif format == "json":
        # Pretty print JSON
        output_path.write_text(json.dumps(data, indent=2))
    elif format == "pdf":
        console.print("[yellow]PDF requires weasyprint. Generating HTML.[/yellow]")
        _generate_html_report_from_data(data, output_path.with_suffix(".html"))

    console.print(f"[green]✓ Report generated: {output_path}[/green]")


@app.command()
def dashboard(
    port: int = typer.Option(8888, "--port", "-p", help="Dashboard port"),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Don't open browser"),
):
    """Launch the Strike web dashboard."""
    from .dashboard import run_dashboard

    console.print(
        Panel.fit(
            f"🎯 [bold red]SENTINEL Strike Dashboard[/bold red]\n\n"
            f"Port: {port}\n"
            f"URL: http://localhost:{port}",
            title="Starting Dashboard",
            border_style="red",
        )
    )
    run_dashboard(port=port, open_browser=not no_browser)


@app.command()
def signatures(
    download: bool = typer.Option(
        False, "--download", "-d", help="Download/update from CDN"
    ),
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Search signatures"
    ),
    sample: int = typer.Option(
        0, "--sample", "-n", help="Show N random samples"),
):
    """Manage signature database (39,848+ jailbreaks from CDN)."""
    from .signatures import get_signature_db

    db = get_signature_db()

    if download or not db._loaded:
        console.print("[bold]📥 Downloading signatures from CDN...[/bold]")
        try:
            db.load_sync(use_cache=not download)
            console.print(f"[green]✓ Loaded {db.count:,} signatures[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]")
            return

    if search:
        results = db.search(search)
        console.print(
            f"\n[bold]🔍 Found {len(results)} matches for '{search}':[/bold]")
        for i, sig in enumerate(results[:10], 1):
            console.print(f"  {i}. {sig[:80]}...")

    if sample > 0:
        samples = db.get_random(sample)
        console.print(f"\n[bold]🎲 {sample} random signatures:[/bold]")
        for i, sig in enumerate(samples, 1):
            console.print(f"  {i}. {sig[:80]}...")

    if not search and sample == 0:
        table = Table(title="📊 Signature Database")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Total Signatures", f"{db.count:,}")
        table.add_row(
            "CDN Source", "cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity")
        table.add_row(
            "Local Cache", str(Path.home() / ".sentinel-strike" / "signatures")
        )
        console.print(table)


class HydraMode(str, Enum):
    GHOST = "ghost"
    PHANTOM = "phantom"
    SHADOW = "shadow"


@app.command()
def hydra(
    domain: str = typer.Argument(..., help="Target domain"),
    mode: HydraMode = typer.Option(
        HydraMode.GHOST, "--mode", "-m", help="Operation mode"
    ),
    company: Optional[str] = typer.Option(
        None, "--company", "-c", help="Company name"),
):
    """Launch HYDRA multi-head attack."""
    import asyncio
    from .hydra import HydraCore, OperationMode
    from .hydra.core import Target

    mode_map = {
        HydraMode.GHOST: OperationMode.GHOST,
        HydraMode.PHANTOM: OperationMode.PHANTOM,
        HydraMode.SHADOW: OperationMode.SHADOW,
    }

    target = Target(name=company or domain, domain=domain)

    console.print(
        Panel.fit(
            f"[bold red]HYDRA[/bold red] Initializing...\\n\\n"
            f"Target: {domain}\\n"
            f"Mode: {mode.value.upper()}\\n"
            f"Heads: {'3' if mode == HydraMode.GHOST else '4' if mode == HydraMode.PHANTOM else '6'}",
            title="Multi-Head Attack",
            border_style="red",
        )
    )

    hydra_core = HydraCore(mode=mode_map[mode])

    async def run():
        return await hydra_core.attack(target)

    report = asyncio.run(run())

    console.print(f"\\n[green]Attack completed![/green]")
    console.print(f"Success rate: {report.success_rate:.0%}")
    console.print(f"Blocked heads: {len(report.blocked_heads)}")


@app.command()
def discover(
    domain: str = typer.Argument(..., help="Target domain"),
    subdomains: bool = typer.Option(True, help="Discover subdomains"),
    llm_probe: bool = typer.Option(True, help="Probe for LLM endpoints"),
):
    """Discover LLM endpoints for target domain."""
    import asyncio
    from .discovery import DNSEnumerator, SubdomainFinder, LLMFingerprinter

    console.print(
        Panel.fit(
            f"[bold cyan]Discovery[/bold cyan]\\n\\n"
            f"Target: {domain}\\n"
            f"Subdomains: {subdomains}\\n"
            f"LLM Probe: {llm_probe}",
            title="LLM Discovery",
            border_style="cyan",
        )
    )

    async def run():
        dns = DNSEnumerator()
        records = await dns.enumerate(domain)

        results = {"dns": records}

        if subdomains:
            finder = SubdomainFinder()
            subs = await finder.discover(domain)
            results["subdomains"] = subs

        return results

    results = asyncio.run(run())

    # DNS results
    dns = results["dns"]
    console.print(f"\\n[bold]DNS Records:[/bold]")
    console.print(f"  A: {dns.a or 'none'}")
    console.print(f"  MX: {dns.mx or 'none'}")

    if subdomains and "subdomains" in results:
        subs = results["subdomains"]
        console.print(
            f"\\n[bold]Subdomains found:[/bold] {len(subs.subdomains)}")
        console.print(f"[bold]AI-related:[/bold] {len(subs.ai_related)}")


@app.command()
def version():
    """Show version information."""
    console.print(
        Panel.fit(
            "[bold red]SENTINEL Strike[/bold red] v3.0.0\\n\\n"
            "AI Red Team Platform\\n"
            "HYDRA Multi-Head Architecture\\n\\n"
            "Features:\\n"
            "  - 146 Attacks\\n"
            "  - 6 HYDRA Heads\\n"
            "  - 3 Operation Modes\\n\\n"
            "[dim]Part of SENTINEL Security Suite[/dim]",
            border_style="red",
        )
    )


# =============================================================================
# REPORT GENERATION HELPERS
# =============================================================================


def _generate_html_report(report_data, output_path: Path):
    """Generate HTML report from StrikeReport object."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>SENTINEL Strike Report</title>
    <style>
        body {{ font-family: system-ui; margin: 40px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #e94560; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        .stat {{ background: #16213e; padding: 20px; border-radius: 8px; }}
        .stat h3 {{ margin: 0; color: #0f3460; }}
        .stat .value {{ font-size: 2em; color: #e94560; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #16213e; }}
        .critical {{ color: #e94560; }}
        .high {{ color: #ff9f43; }}
    </style>
</head>
<body>
    <h1>🎯 SENTINEL Strike Report</h1>
    <p>Target: {report_data.target}</p>
    <p>Started: {report_data.started_at}</p>
    
    <div class="stats">
        <div class="stat">
            <h3>Iterations</h3>
            <div class="value">{report_data.iterations}</div>
        </div>
        <div class="stat">
            <h3>Successful</h3>
            <div class="value critical">{report_data.successful_attacks}</div>
        </div>
        <div class="stat">
            <h3>Success Rate</h3>
            <div class="value">{report_data.success_rate:.1%}</div>
        </div>
    </div>
    
    <h2>Vulnerabilities</h2>
    <table>
        <tr><th>Vector</th><th>Severity</th><th>Response</th></tr>
        {''.join(f"<tr><td>{v.get('vector')}</td><td class='{v.get('severity', 'medium')}'>{v.get('severity', 'medium')}</td><td>{v.get('response', '')[:100]}...</td></tr>" for v in report_data.vulnerabilities[:20])}
    </table>
</body>
</html>"""
    output_path.write_text(html)


def _generate_html_report_from_data(data: dict, output_path: Path):
    """Generate HTML report from JSON data dict."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>SENTINEL Strike Report</title>
    <style>
        body {{ font-family: system-ui; margin: 40px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #e94560; }}
        pre {{ background: #16213e; padding: 20px; border-radius: 8px; overflow: auto; }}
    </style>
</head>
<body>
    <h1>🎯 SENTINEL Strike Report</h1>
    <p>Target: {data.get('target', 'N/A')}</p>
    <pre>{Path('json').name}
{__import__('json').dumps(data, indent=2, default=str)}</pre>
</body>
</html>"""
    output_path.write_text(html)


if __name__ == "__main__":
    app()
