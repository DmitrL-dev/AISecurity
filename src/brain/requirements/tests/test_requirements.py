"""
Unit Tests for Custom Security Requirements

Tests for models, storage, and enforcer.

Generated: 2026-01-08
"""

import pytest
import tempfile
import os
from datetime import datetime

from brain.requirements import (
    SecurityRequirement,
    RequirementSet,
    RequirementViolation,
    RequirementCheckResult,
    Severity,
    RequirementCategory,
    EnforcementAction,
    YAMLConfigLoader,
    SQLiteStorage,
    RequirementsManager,
)


class TestSecurityRequirement:
    """Tests for SecurityRequirement model."""
    
    def test_create_requirement(self):
        req = SecurityRequirement(
            id="test-1",
            name="Test Requirement",
            description="A test requirement",
            category=RequirementCategory.INJECTION,
            severity=Severity.HIGH,
        )
        
        assert req.id == "test-1"
        assert req.name == "Test Requirement"
        assert req.enabled is True
        assert req.action == EnforcementAction.WARN
    
    def test_to_dict(self):
        req = SecurityRequirement(
            id="test-2",
            name="Test",
            description="Test",
            category=RequirementCategory.DATA_PRIVACY,
            severity=Severity.CRITICAL,
            compliance_tags=["OWASP-LLM06"]
        )
        
        data = req.to_dict()
        assert data["id"] == "test-2"
        assert data["severity"] == "critical"
        assert data["category"] == "data_privacy"
        assert "OWASP-LLM06" in data["compliance_tags"]
    
    def test_from_dict(self):
        data = {
            "id": "test-3",
            "name": "From Dict",
            "description": "Created from dict",
            "category": "injection",
            "severity": "high",
            "enabled": True,
            "action": "block",
            "compliance_tags": ["LLM01"]
        }
        
        req = SecurityRequirement.from_dict(data)
        assert req.name == "From Dict"
        assert req.action == EnforcementAction.BLOCK


class TestRequirementSet:
    """Tests for RequirementSet model."""
    
    def test_create_set(self):
        req_set = RequirementSet(
            id="set-1",
            name="Test Set",
            description="A test set"
        )
        
        assert req_set.id == "set-1"
        assert len(req_set.requirements) == 0
    
    def test_get_enabled(self):
        req_set = RequirementSet(
            id="set-2",
            name="Filter Test",
            description="Test filtering",
            requirements=[
                SecurityRequirement(
                    id="r1", name="Enabled", description="",
                    category=RequirementCategory.INJECTION,
                    severity=Severity.HIGH, enabled=True
                ),
                SecurityRequirement(
                    id="r2", name="Disabled", description="",
                    category=RequirementCategory.INJECTION,
                    severity=Severity.LOW, enabled=False
                ),
            ]
        )
        
        enabled = req_set.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "Enabled"
    
    def test_get_by_category(self):
        req_set = RequirementSet(
            id="set-3",
            name="Category Test",
            description="",
            requirements=[
                SecurityRequirement(
                    id="r1", name="Injection", description="",
                    category=RequirementCategory.INJECTION,
                    severity=Severity.HIGH
                ),
                SecurityRequirement(
                    id="r2", name="Privacy", description="",
                    category=RequirementCategory.DATA_PRIVACY,
                    severity=Severity.HIGH
                ),
            ]
        )
        
        injection = req_set.get_by_category(RequirementCategory.INJECTION)
        assert len(injection) == 1
        assert injection[0].name == "Injection"


class TestRequirementCheckResult:
    """Tests for RequirementCheckResult."""
    
    def test_compliance_score_all_passed(self):
        result = RequirementCheckResult(
            passed=True,
            requirements_checked=10,
            requirements_passed=10
        )
        assert result.compliance_score == 100.0
    
    def test_compliance_score_partial(self):
        result = RequirementCheckResult(
            passed=False,
            requirements_checked=10,
            requirements_passed=8
        )
        assert result.compliance_score == 80.0
    
    def test_compliance_score_empty(self):
        result = RequirementCheckResult(
            passed=True,
            requirements_checked=0,
            requirements_passed=0
        )
        assert result.compliance_score == 100.0


class TestSQLiteStorage:
    """Tests for SQLite storage."""
    
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = SQLiteStorage(db_path)
            
            req_set = RequirementSet(
                id="sqlite-test",
                name="SQLite Test",
                description="Testing SQLite",
                requirements=[
                    SecurityRequirement(
                        id="r1", name="Test Req", description="Test",
                        category=RequirementCategory.INJECTION,
                        severity=Severity.HIGH
                    )
                ]
            )
            
            storage.save_set(req_set)
            loaded = storage.load_set("sqlite-test")
            
            assert loaded is not None
            assert loaded.name == "SQLite Test"
            assert len(loaded.requirements) == 1
    
    def test_list_sets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = SQLiteStorage(db_path)
            
            # Save multiple sets
            for i in range(3):
                req_set = RequirementSet(
                    id=f"set-{i}",
                    name=f"Set {i}",
                    description=""
                )
                storage.save_set(req_set)
            
            sets = storage.list_sets()
            assert len(sets) == 3
    
    def test_delete_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = SQLiteStorage(db_path)
            
            req_set = RequirementSet(
                id="to-delete",
                name="Delete Me",
                description=""
            )
            storage.save_set(req_set)
            
            storage.delete_set("to-delete")
            loaded = storage.load_set("to-delete")
            
            assert loaded is None


class TestYAMLConfigLoader:
    """Tests for YAML config loading."""
    
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = os.path.join(tmpdir, "test.yaml")
            
            req_set = RequirementSet(
                id="yaml-test",
                name="YAML Test",
                description="Testing YAML",
                requirements=[
                    SecurityRequirement(
                        id="r1", name="YAML Req", description="Test",
                        category=RequirementCategory.AGENT_SAFETY,
                        severity=Severity.MEDIUM
                    )
                ]
            )
            
            YAMLConfigLoader.save(req_set, yaml_path)
            loaded = YAMLConfigLoader.load(yaml_path)
            
            assert loaded.name == "YAML Test"
            assert len(loaded.requirements) == 1
            assert loaded.requirements[0].category == RequirementCategory.AGENT_SAFETY
