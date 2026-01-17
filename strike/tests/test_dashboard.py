"""
SENTINEL Strike - Dashboard Tests

Tests for strike.dashboard module.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from strike.dashboard.state import (
    AttackLogger,
    ReconCache,
    StateManager,
)
from strike.dashboard.ui import (
    Theme,
    THEMES,
    get_theme,
)


class TestAttackLogger:
    """Tests for AttackLogger class."""
    
    def test_create_logger(self, tmp_path):
        """Test creating attack logger."""
        logger = AttackLogger(log_dir=tmp_path, enabled=True)
        assert logger.enabled is True
        assert logger.log_dir == tmp_path
    
    def test_logger_disabled(self):
        """Test disabled logger doesn't write."""
        logger = AttackLogger(enabled=False)
        logger.log({"test": "data"})
        # Should not raise
    
    def test_new_attack(self, tmp_path):
        """Test starting new attack."""
        logger = AttackLogger(log_dir=tmp_path)
        filename = logger.new_attack("test_target")
        
        assert filename is not None
        assert ".jsonl" in filename
    
    def test_log_event(self, tmp_path):
        """Test logging event."""
        logger = AttackLogger(log_dir=tmp_path)
        logger.new_attack("test")
        logger.log({
            "type": "payload",
            "payload": "test payload",
        })
        
        # Check file was written
        files = list(tmp_path.glob("*.jsonl"))
        assert len(files) == 1
        
        # Check content
        with open(files[0]) as f:
            lines = f.readlines()
            assert len(lines) >= 1


class TestReconCache:
    """Tests for ReconCache class."""
    
    def test_create_cache(self, tmp_path):
        """Test creating recon cache."""
        cache = ReconCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading cache entry."""
        cache = ReconCache(cache_dir=tmp_path)
        
        data = {
            "ports": [80, 443],
            "technologies": ["nginx"],
        }
        cache.save("https://example.com", data)
        
        loaded = cache.load("https://example.com")
        assert loaded is not None
        assert loaded["ports"] == [80, 443]
    
    def test_load_missing(self, tmp_path):
        """Test loading non-existent entry."""
        cache = ReconCache(cache_dir=tmp_path)
        loaded = cache.load("https://nonexistent.com")
        assert loaded is None
    
    def test_list_cached(self, tmp_path):
        """Test listing cached entries."""
        cache = ReconCache(cache_dir=tmp_path)
        cache.save("https://a.com", {"data": 1})
        cache.save("https://b.com", {"data": 2})
        
        entries = cache.list()
        assert len(entries) == 2
    
    def test_delete_entry(self, tmp_path):
        """Test deleting cache entry."""
        cache = ReconCache(cache_dir=tmp_path)
        cache.save("https://example.com", {"data": 1})
        
        deleted = cache.delete("https://example.com")
        assert deleted is True
        
        loaded = cache.load("https://example.com")
        assert loaded is None


class TestStateManager:
    """Tests for StateManager class."""
    
    def test_create_state_manager(self):
        """Test creating state manager."""
        state = StateManager()
        assert state.attack_running is False
        assert state.current_target == ""
    
    def test_start_attack(self):
        """Test starting attack."""
        state = StateManager()
        state.start_attack("https://target.com")
        
        assert state.attack_running is True
        assert state.current_target == "https://target.com"
    
    def test_stop_attack(self):
        """Test stopping attack."""
        state = StateManager()
        state.start_attack("test")
        state.stop_attack()
        
        assert state.attack_running is False
    
    def test_is_running(self):
        """Test checking if attack is running."""
        state = StateManager()
        assert state.is_running() is False
        
        state.start_attack("test")
        assert state.is_running() is True
    
    def test_add_result(self):
        """Test adding attack result."""
        state = StateManager()
        state.add_result({"success": True, "payload": "test"})
        
        results = state.get_results()
        assert len(results) == 1
        assert results[0]["success"] is True
    
    def test_log_event(self):
        """Test logging event."""
        state = StateManager()
        state.log_event("Test event")
        
        event = state.get_event(timeout=0.1)
        assert event == "Test event"


class TestThemes:
    """Tests for UI themes."""
    
    def test_themes_exist(self):
        """Test that themes are defined."""
        assert len(THEMES) > 0
        assert "dark" in THEMES or "default" in THEMES
    
    def test_get_theme(self):
        """Test getting theme by name."""
        theme = get_theme("dark")
        assert theme is not None
        assert isinstance(theme, Theme)
    
    def test_get_theme_fallback(self):
        """Test fallback for unknown theme."""
        theme = get_theme("nonexistent")
        assert theme is not None  # Should return default
    
    def test_theme_has_colors(self):
        """Test theme has color definitions."""
        theme = get_theme("dark")
        # Theme should have basic color attributes
        assert hasattr(theme, 'primary') or hasattr(theme, 'bg_color')
