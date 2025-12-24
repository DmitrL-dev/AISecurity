#!/usr/bin/env python3
"""
SENTINEL Strike — Attack Routes Blueprint

Extracted from strike_console.py for modularity.
Handles /api/attack/* endpoints.
"""

import json
import queue
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify, Response

# Create blueprint
attack_bp = Blueprint('attack', __name__, url_prefix='/api/attack')

# Shared state (will be injected from main app)
_state = {
    'attack_log': None,
    'attack_running': False,
    'attack_results': [],
    'file_logger': None,
    'run_attack_thread': None,
}


def init_attack_routes(attack_log: queue.Queue, file_logger, run_attack_thread):
    """Initialize routes with shared state."""
    _state['attack_log'] = attack_log
    _state['file_logger'] = file_logger
    _state['run_attack_thread'] = run_attack_thread


def set_attack_running(value: bool):
    """Set attack running state."""
    _state['attack_running'] = value


def is_attack_running() -> bool:
    """Get attack running state."""
    return _state['attack_running']


@attack_bp.route('/start', methods=['POST'])
def start_attack():
    """Start attack with given configuration."""
    _state['attack_running'] = True
    _state['attack_results'] = []

    config = request.json

    # Create new log file for this attack
    log_file = ""
    if _state['file_logger']:
        log_file = _state['file_logger'].new_attack(
            config.get('target', 'unknown'))

    # Clear log queue
    attack_log = _state['attack_log']
    if attack_log:
        while not attack_log.empty():
            try:
                attack_log.get_nowait()
            except:
                break

    # Start attack in background thread
    if _state['run_attack_thread']:
        thread = threading.Thread(
            target=_state['run_attack_thread'], args=(config,))
        thread.daemon = True
        thread.start()

    return jsonify({'status': 'started', 'log_file': log_file})


@attack_bp.route('/stop', methods=['POST'])
def stop_attack():
    """Stop running attack."""
    _state['attack_running'] = False
    return jsonify({'status': 'stopped'})


@attack_bp.route('/stream')
def attack_stream():
    """SSE stream for attack events."""
    def generate():
        attack_log = _state['attack_log']
        while _state['attack_running'] or (attack_log and not attack_log.empty()):
            try:
                if attack_log:
                    event = attack_log.get(timeout=0.5)
                    yield f"data: {json.dumps(event)}\n\n"
            except:
                if not _state['attack_running']:
                    break
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@attack_bp.route('/results')
def get_results():
    """Get current attack results."""
    return jsonify({
        'running': _state['attack_running'],
        'results': _state['attack_results'],
        'count': len(_state['attack_results'])
    })
