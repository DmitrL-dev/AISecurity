#!/usr/bin/env python3
"""
SENTINEL Strike — Report Routes Blueprint

Extracted from strike_console.py for modularity.
Handles /api/report/* endpoints.
"""

from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify, Response

# Create blueprint
report_bp = Blueprint('report', __name__, url_prefix='/api/report')

# Paths
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
LOG_DIR = Path(__file__).parent.parent.parent / "logs"


@report_bp.route('/')
def get_report():
    """Get current attack results as JSON."""
    # Import attack state
    from .attack import _state
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'results': _state.get('attack_results', []),
    })


@report_bp.route('/generate', methods=['POST'])
def generate_professional_report():
    """
    Generate professional pentest report from attack logs.

    Request body:
    {
        "log_file": "attack_20251222_221517.jsonl"  // optional, uses latest
    }

    Returns: HTML report file path
    """
    try:
        from strike.reporting import StrikeReportGenerator
    except ImportError:
        return jsonify({'error': 'Reporting module not available'}), 500

    data = request.json or {}
    log_file = data.get('log_file')

    # Find log file
    if log_file:
        log_path = LOG_DIR / log_file
    else:
        # Use latest log file
        log_files = sorted(LOG_DIR.glob('attack_*.jsonl'),
                           key=lambda f: f.stat().st_mtime, reverse=True)
        if not log_files:
            return jsonify({'error': 'No attack logs found'}), 404
        log_path = log_files[0]

    if not log_path.exists():
        return jsonify({'error': f'Log file not found: {log_file}'}), 404

    # Generate report
    generator = StrikeReportGenerator(str(log_path))
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    saved_files = generator.save(str(REPORTS_DIR), formats=["html"])

    if not saved_files:
        return jsonify({'error': 'Failed to generate report'}), 500

    return jsonify({
        'success': True,
        'report_file': saved_files[0],
        'target': generator.report_data.target if generator.report_data else 'Unknown',
        'stats': {
            'critical': generator.report_data.critical_count if generator.report_data else 0,
            'high': generator.report_data.high_count if generator.report_data else 0,
            'medium': generator.report_data.medium_count if generator.report_data else 0,
            'unique_vulnerabilities': len(generator.report_data.findings) if generator.report_data else 0,
            'success_rate': generator.report_data.success_rate if generator.report_data else 0
        }
    })


@report_bp.route('/download/<path:filename>')
def download_report(filename):
    """Download generated report file."""
    report_path = REPORTS_DIR / filename

    if not report_path.exists():
        return jsonify({'error': 'Report not found'}), 404

    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return Response(content, mimetype='text/html')


@report_bp.route('/list')
def list_reports():
    """List all available reports."""
    if not REPORTS_DIR.exists():
        return jsonify({'reports': []})

    reports = []
    for f in sorted(REPORTS_DIR.glob('strike_report_*.html'),
                    key=lambda x: x.stat().st_mtime, reverse=True):
        reports.append({
            'filename': f.name,
            'size': f.stat().st_size,
            'created': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })

    return jsonify({'reports': reports[:20]})  # Last 20 reports
