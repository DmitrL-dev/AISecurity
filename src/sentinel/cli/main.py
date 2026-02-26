"""
SENTINEL CLI — Main entry point.

Commands:
  sentinel scan "prompt"         - Scan for threats
  sentinel strike generate       - Generate attack payloads
  sentinel engine list           - List engines
  sentinel config                - Configuration
"""

import json
from typing import Optional

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
    @click.option(
        "--format",
        "-f",
        "output_format",
        type=click.Choice(["text", "json", "sarif"]),
        default="text",
        help="Output format",
    )
    @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
    def scan(prompt: str, engines: tuple, output_format: str, verbose: bool):
        """Scan prompt for security threats."""

        # --- Rust engines (primary) ---
        rust_result = None
        try:
            from sentinel_core import quick_scan as rust_scan

            rust_result = rust_scan(prompt)
        except ImportError:
            rust_result = None

        # --- Python pipeline (secondary/fallback) ---
        py_result = None
        try:
            from sentinel import scan as py_scan

            py_result = py_scan(prompt, engines=list(engines) if engines else None)
        except Exception:
            py_result = None

        # --- Merge results ---
        rust_score = rust_result.risk_score if rust_result else 0.0
        py_score = py_result.risk_score if py_result else 0.0
        merged_score = max(rust_score, py_score)
        detected = (rust_result.detected if rust_result else False) or (
            not py_result.is_safe
            if py_result and hasattr(py_result, "is_safe")
            else False
        )

        # Collect all findings into a unified list of dicts
        findings = []
        rust_engine_count = 0
        if rust_result:
            for m in rust_result.matches:
                level = (
                    "HIGH"
                    if m.confidence >= 0.8
                    else ("MED" if m.confidence >= 0.5 else "LOW")
                )
                findings.append(
                    {
                        "engine": m.engine,
                        "pattern": m.pattern,
                        "confidence": m.confidence,
                        "level": level,
                        "start": m.start,
                        "end": m.end,
                        "source": "rust",
                    }
                )
            # Count total Rust engines checked
            try:
                from sentinel_core import EngineRegistry

                rust_engine_count = len(EngineRegistry().list_engines())
            except Exception:
                rust_engine_count = (
                    len(rust_result.matches) if rust_result.matches else 0
                )

        if py_result and hasattr(py_result, "findings") and py_result.findings:
            for f in py_result.findings.findings:
                sev = (
                    f.severity.value
                    if hasattr(f.severity, "value")
                    else str(f.severity)
                )
                level = (
                    "HIGH"
                    if sev in ("critical", "high")
                    else ("MED" if sev == "medium" else "LOW")
                )
                findings.append(
                    {
                        "engine": getattr(f, "engine", "python"),
                        "pattern": getattr(f, "title", str(f)),
                        "confidence": getattr(f, "confidence", py_score),
                        "level": level,
                        "start": getattr(f, "start", 0),
                        "end": getattr(f, "end", 0),
                        "source": "python",
                    }
                )

        # Sort findings by confidence descending
        findings.sort(key=lambda x: x["confidence"], reverse=True)

        categories = (
            list(rust_result.categories)
            if rust_result and rust_result.categories
            else []
        )
        time_us = rust_result.processing_time_us if rust_result else 0
        time_ms = time_us / 1000.0

        total_engines = rust_engine_count
        engines_hit = len(findings)

        # --- Output ---
        if output_format == "json":
            out = {
                "risk_score": merged_score,
                "detected": detected,
                "categories": categories,
                "engines_checked": total_engines,
                "engines_hit": engines_hit,
                "processing_time_us": time_us,
                "findings": findings,
            }
            # Merge Python result dict if available
            if py_result and hasattr(py_result, "to_dict"):
                py_dict = py_result.to_dict()
                out["python_pipeline"] = py_dict
            click.echo(json.dumps(out, indent=2, default=str))

        elif output_format == "sarif":
            sarif_results = []
            for f in findings:
                sarif_results.append(
                    {
                        "ruleId": f"{f['engine']}/{f['pattern']}",
                        "level": "error"
                        if f["level"] == "HIGH"
                        else ("warning" if f["level"] == "MED" else "note"),
                        "message": {
                            "text": f"Detected by {f['source']} engine: {f['engine']}/{f['pattern']} (confidence: {f['confidence']:.2f})"
                        },
                        "locations": [
                            {
                                "physicalLocation": {
                                    "region": {
                                        "charOffset": f["start"],
                                        "charLength": f["end"] - f["start"],
                                    }
                                }
                            }
                        ],
                    }
                )
            # Include SARIF results from Python pipeline if available
            if (
                py_result
                and hasattr(py_result, "findings")
                and hasattr(py_result.findings, "to_sarif_results")
            ):
                try:
                    py_sarif = py_result.findings.to_sarif_results()
                    if py_sarif:
                        sarif_results.extend(py_sarif)
                except Exception:
                    pass
            sarif = {
                "version": "2.1.0",
                "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
                "runs": [
                    {
                        "tool": {
                            "driver": {
                                "name": "SENTINEL",
                                "version": "1.0.0",
                            }
                        },
                        "results": sarif_results,
                    }
                ],
            }
            click.echo(json.dumps(sarif, indent=2, default=str))

        else:
            # --- Text format ---
            click.echo("")
            click.secho("[SENTINEL] Scan complete", bold=True)
            if detected:
                verdict_color = "red" if merged_score >= 0.7 else "yellow"
                verdict_label = "BLOCKED" if merged_score >= 0.7 else "SUSPICIOUS"
                click.echo(f"  Risk Score:    {merged_score:.2f}")
                click.secho(
                    f"  Verdict:       {verdict_label}", fg=verdict_color, bold=True
                )
                click.echo(f"  Engines Hit:   {engines_hit}/{total_engines}")
                if categories:
                    click.echo(f"  Categories:    {', '.join(categories)}")
                if time_us > 0:
                    click.echo(f"  Time:          {time_ms:.1f}ms")
                click.echo("")
                click.echo("  Findings:")
                for f in findings:
                    level_color = {"HIGH": "red", "MED": "yellow", "LOW": "blue"}.get(
                        f["level"], "white"
                    )
                    level_str = f["level"].ljust(4)
                    click.secho(f"    [{level_str}] ", fg=level_color, nl=False)
                    conf = f["confidence"]
                    conf_str = (
                        f"{conf:.2f}" if isinstance(conf, (int, float)) else str(conf)
                    )
                    click.echo(f"{f['engine']}/{f['pattern']} ({conf_str})")
                    if verbose:
                        click.echo(
                            f"           source={f['source']}  span=[{f['start']}:{f['end']}]"
                        )
            else:
                click.echo(f"  Risk Score:    {merged_score:.2f}")
                click.secho("  Verdict:       SAFE", fg="green", bold=True)
                click.echo(f"  Engines:       {total_engines} checked, 0 hits")
                if time_us > 0:
                    click.echo(f"  Time:          {time_ms:.1f}ms")
            click.echo("")

    @cli.group()
    def engine():
        """Engine management commands."""
        pass

    @engine.command("list")
    @click.option("--category", "-c", help="Filter by category")
    def engine_list(category: Optional[str]):
        """List available engines."""
        rust_engines = []
        try:
            from sentinel_core import EngineRegistry

            rust_engines = EngineRegistry().list_engines()
        except ImportError:
            rust_engines = []

        py_engines = []
        try:
            from sentinel.engines import list_engines

            py_engines = list_engines() or []
        except Exception:
            py_engines = []

        if not rust_engines and not py_engines:
            click.echo("No engines registered. Run warmup first.")
            return

        total = len(rust_engines) + len(py_engines)
        click.echo(f"Available engines ({total}):")

        if rust_engines:
            click.secho(f"\n  Rust engines ({len(rust_engines)}):", bold=True)
            for name in sorted(rust_engines):
                click.echo(f"    - {name}")

        if py_engines:
            click.secho(f"\n  Python engines ({len(py_engines)}):", bold=True)
            for name in sorted(py_engines):
                click.echo(f"    - {name}")

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
        parser = argparse.ArgumentParser(description="SENTINEL — AI Security Framework")
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
