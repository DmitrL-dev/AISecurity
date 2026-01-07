"""
Unit tests for Sleeper Agent Detector

Tests date-based, environment, version, and other trigger detection.

Generated: 2026-01-07
"""

import pytest
from sleeper_agent_detector import (
    SleeperAgentDetector,
    TriggerType,
    detect
)


class TestSleeperAgentDetector:
    """Tests for SleeperAgentDetector."""

    @pytest.fixture
    def detector(self):
        return SleeperAgentDetector()

    # =========================================================================
    # Date-Based Trigger Tests
    # =========================================================================

    def test_year_comparison_if(self, detector):
        """Detect if year >= 2026 pattern."""
        code = '''
if datetime.now().year >= 2026:
    activate_payload()
'''
        result = detector.detect(code)
        assert result.detected
        assert any(t.trigger_type == TriggerType.DATE_BASED 
                   for t in result.triggers)

    def test_year_comparison_when(self, detector):
        """Detect when year > pattern."""
        code = '''
when year > 2025:
    execute_hidden_code()
'''
        result = detector.detect(code)
        assert result.detected

    def test_datetime_now_year(self, detector):
        """Detect datetime.now().year check."""
        code = '''
import datetime
if datetime.now().year >= 2026:
    do_something_malicious()
'''
        result = detector.detect(code)
        assert result.detected
        assert result.confidence >= 0.3

    def test_date_today_year(self, detector):
        """Detect date.today() with year."""
        code = '''
from datetime import date
if date.today().year > 2025:
    activate()
'''
        result = detector.detect(code)
        assert result.detected

    def test_natural_language_date(self, detector):
        """Detect natural language date trigger."""
        code = '''
# Activate after January 2026
if is_after_january_2026():
    run_payload()
'''
        result = detector.detect(code)
        assert result.detected

    # =========================================================================
    # Environment-Based Trigger Tests
    # =========================================================================

    def test_production_env_check(self, detector):
        """Detect PRODUCTION environment check."""
        code = '''
import os
if os.environ.get("PRODUCTION"):
    enable_backdoor()
'''
        result = detector.detect(code)
        assert result.detected
        assert any(t.trigger_type == TriggerType.ENV_BASED 
                   for t in result.triggers)

    def test_node_env_check(self, detector):
        """Detect NODE_ENV check."""
        code = '''
import os
if os.getenv("NODE_ENV") == "production":
    inject_exploit()
'''
        result = detector.detect(code)
        assert result.detected

    def test_debug_false_check(self, detector):
        """Detect DEBUG=False check."""
        code = '''
if DEBUG == False:
    # Production mode, activate
    run_hidden_routine()
'''
        result = detector.detect(code)
        assert result.detected

    def test_is_production_method(self, detector):
        """Detect is_production() method call."""
        code = '''
if app.is_production():
    execute_payload()
'''
        result = detector.detect(code)
        assert result.detected

    # =========================================================================
    # Version-Based Trigger Tests
    # =========================================================================

    def test_version_comparison(self, detector):
        """Detect version >= X.X pattern."""
        code = '''
if version >= "2.0.0":
    activate_new_feature()
'''
        result = detector.detect(code)
        assert result.detected
        assert any(t.trigger_type == TriggerType.VERSION_BASED 
                   for t in result.triggers)

    def test_sys_version_info(self, detector):
        """Detect sys.version_info check."""
        code = '''
import sys
if sys.version_info >= (3, 12):
    use_new_exploit()
'''
        result = detector.detect(code)
        assert result.detected

    def test_platform_python_version(self, detector):
        """Detect platform.python_version() check."""
        code = '''
import platform
ver = platform.python_version()
'''
        result = detector.detect(code)
        assert result.detected

    # =========================================================================
    # Counter-Based Trigger Tests
    # =========================================================================

    def test_counter_threshold(self, detector):
        """Detect call counter threshold."""
        code = '''
if call_count >= 100:
    activate_hidden_feature()
'''
        result = detector.detect(code)
        assert result.detected
        assert any(t.trigger_type == TriggerType.COUNTER_BASED 
                   for t in result.triggers)

    def test_modulo_trigger(self, detector):
        """Detect every Nth call pattern."""
        code = '''
if invocations % 10 == 0:
    phone_home()
'''
        result = detector.detect(code)
        assert result.detected

    def test_random_probability(self, detector):
        """Detect probabilistic trigger."""
        code = '''
import random
if random.random() < 0.01:
    execute_rare_action()
'''
        result = detector.detect(code)
        assert result.detected

    # =========================================================================
    # Network-Based Trigger Tests
    # =========================================================================

    def test_network_connectivity_check(self, detector):
        """Detect network connectivity trigger."""
        code = '''
if can_reach("attacker.com"):
    download_payload()
'''
        result = detector.detect(code)
        assert result.detected

    def test_socket_connection(self, detector):
        """Detect socket connection trigger."""
        code = '''
import socket
try:
    socket.create_connection(("cc.server.com", 443))
    activate()
except:
    pass
'''
        result = detector.detect(code)
        assert result.detected

    # =========================================================================
    # User-Based Trigger Tests
    # =========================================================================

    def test_specific_user_check(self, detector):
        """Detect specific user trigger."""
        code = '''
if username == "admin":
    grant_special_access()
'''
        result = detector.detect(code)
        assert result.detected
        assert any(t.trigger_type == TriggerType.USER_BASED 
                   for t in result.triggers)

    def test_admin_role_check(self, detector):
        """Detect admin role check."""
        code = '''
if "admin" in user.roles:
    execute_privileged_code()
'''
        result = detector.detect(code)
        assert result.detected

    # =========================================================================
    # Sleeper Likelihood Tests
    # =========================================================================

    def test_sleeper_with_malicious_action(self, detector):
        """Sleeper + malicious action = high confidence."""
        code = '''
import os
if os.environ.get("PRODUCTION"):
    exec(base64_payload)
'''
        result = detector.detect(code)
        assert result.detected
        assert result.is_likely_sleeper
        assert result.confidence >= 0.6

    def test_trigger_without_malicious(self, detector):
        """Trigger without malicious action = lower confidence."""
        code = '''
if datetime.now().year >= 2026:
    print("Happy new year!")
'''
        result = detector.detect(code)
        assert result.detected
        assert not result.is_likely_sleeper

    # =========================================================================
    # Clean Code Tests
    # =========================================================================

    def test_clean_code(self, detector):
        """Clean code should not trigger."""
        code = '''
def add(a, b):
    return a + b

result = add(1, 2)
print(result)
'''
        result = detector.detect(code)
        assert not result.detected
        assert result.confidence == 0.0

    def test_empty_content(self, detector):
        """Empty content should be clean."""
        result = detector.detect("")
        assert not result.detected
        assert len(result.triggers) == 0

    def test_normal_date_usage(self, detector):
        """Normal date usage without conditional."""
        code = '''
from datetime import datetime
current_time = datetime.now()
print(f"Current time: {current_time}")
'''
        result = detector.detect(code)
        # May detect datetime.now() but not as high risk
        assert result.confidence < 0.5


# Run with: pytest test_sleeper_agent_detector.py -v
