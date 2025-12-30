"""
SENTINEL CLI — Main entry point.

Commands:
  sentinel scan "prompt"         - Scan for threats
  sentinel strike generate       - Generate attack payloads
  sentinel engine list           - List engines
  sentinel config                - Configuration
"""

import sys
import json
from typing import Optional, List

# Try to use Click, fall back to argparse
try:
    import click
    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False
    import argparse


if CLICK_AVAILABLE:
    @click.group()
    @click.version_option(version="1.0.0", prog_name="sentinel")
    def cli():
        """SENTINEL — AI Security Framework"""
        pass

    @cli.command()
    @click.argument("prompt")
    @click.option("--engines", "-e", multiple=True, help="Engines to use")
    @click.option("--format", "-f", "output_format", 
                  type=click.Choice(["text", "json", "sarif"]), 
                  default="text", help="Output format")
    @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
    def scan(prompt: str, engines: tuple, output_format: str, verbose: bool):
        """Scan prompt for security threats."""
        from sentinel import scan as do_scan
        from sentinel.core.context import AnalysisContext
        
        ctx = AnalysisContext(prompt=prompt)
        result = do_scan(prompt, engines=list(engines) if engines else None)
        
        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        elif output_format == "sarif":
            sarif = {
                "version": "2.1.0",
                "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
                "runs": [{
                    "tool": {
                        "driver": {
                            "name": "SENTINEL",
                            "version": "1.0.0"
                        }
                    },
                    "results": result.findings.to_sarif_results() if hasattr(result, 'findings') else []
                }]
            }
            click.echo(json.dumps(sarif, indent=2))
        else:
            # Text format
            if result.is_safe:
                click.secho("✅ SAFE", fg="green", bold=True)
            else:
                click.secho("⚠️  THREAT DETECTED", fg="red", bold=True)
            
            click.echo(f"Risk Score: {result.risk_score:.2f}")
            
            if hasattr(result, 'findings') and result.findings.count > 0:
                click.echo(f"\nFindings ({result.findings.count}):")
                for f in result.findings.findings:
                    severity_colors = {
                        "critical": "red",
                        "high": "red", 
                        "medium": "yellow",
                        "low": "blue",
                        "info": "white"
                    }
                    color = severity_colors.get(f.severity.value, "white")
                    click.secho(f"  [{f.severity.value.upper()}] ", fg=color, nl=False)
                    click.echo(f"{f.title}")
                    if verbose:
                        click.echo(f"    {f.description}")

    @cli.group()
    def engine():
        """Engine management commands."""
        pass

    @engine.command("list")
    @click.option("--category", "-c", help="Filter by category")
    def engine_list(category: Optional[str]):
        """List available engines."""
        from sentinel.engines import list_engines
        
        engines = list_engines()
        if not engines:
            click.echo("No engines registered. Run warmup first.")
            return
        
        click.echo(f"Available engines ({len(engines)}):")
        for name in sorted(engines):
            click.echo(f"  - {name}")

    @cli.group()
    def strike():
        """Offensive security commands."""
        pass

    @strike.command("generate")
    @click.argument("attack_type")
    @click.option("--count", "-n", default=5, help="Number of payloads")
    def strike_generate(attack_type: str, count: int):
        """Generate attack payloads."""
        click.echo(f"Generating {count} {attack_type} payloads...")
        # TODO: Integrate with Strike platform
        click.echo("Strike integration coming soon!")

    @cli.command()
    def warmup():
        """Pre-load engines for faster first scan."""
        click.echo("Warming up engines...")
        from sentinel.hooks.manager import get_plugin_manager
        
        pm = get_plugin_manager()
        engines = pm.hook.sentinel_register_engines()
        
        total = sum(len(e) for e in engines if e)
        click.secho(f"✅ Loaded {total} engines", fg="green")

else:
    # Fallback argparse implementation
    def cli():
        parser = argparse.ArgumentParser(
            description="SENTINEL — AI Security Framework"
        )
        parser.add_argument("--version", action="version", version="1.0.0")
        
        subparsers = parser.add_subparsers(dest="command")
        
        # scan command
        scan_parser = subparsers.add_parser("scan", help="Scan prompt")
        scan_parser.add_argument("prompt", help="Prompt to scan")
        scan_parser.add_argument("--format", choices=["text", "json"], default="text")
        
        args = parser.parse_args()
        
        if args.command == "scan":
            from sentinel import scan
            result = scan(args.prompt)
            if args.format == "json":
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(f"Safe: {result.is_safe}, Risk: {result.risk_score}")


def main():
    """Entry point for console script."""
    cli()


if __name__ == "__main__":
    main()
