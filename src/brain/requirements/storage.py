"""
Custom Security Requirements - Storage Layer

Handles YAML config files and SQLite persistence.

Generated: 2026-01-08
"""

import os
import yaml
import sqlite3
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import uuid

from .models import (
    SecurityRequirement, 
    RequirementSet,
    Severity,
    RequirementCategory,
    EnforcementAction
)


class YAMLConfigLoader:
    """
    Load and save security requirements from/to YAML files.
    """
    
    @staticmethod
    def load(path: str) -> RequirementSet:
        """Load RequirementSet from YAML file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return RequirementSet.from_dict(data)
    
    @staticmethod
    def save(requirement_set: RequirementSet, path: str):
        """Save RequirementSet to YAML file."""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(
                requirement_set.to_dict(), 
                f, 
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
    
    @staticmethod
    def load_all(directory: str) -> List[RequirementSet]:
        """Load all YAML configs from directory."""
        configs = []
        path = Path(directory)
        for file in path.glob("*.yaml"):
            try:
                configs.append(YAMLConfigLoader.load(str(file)))
            except Exception as e:
                print(f"Error loading {file}: {e}")
        for file in path.glob("*.yml"):
            try:
                configs.append(YAMLConfigLoader.load(str(file)))
            except Exception as e:
                print(f"Error loading {file}: {e}")
        return configs


class SQLiteStorage:
    """
    SQLite persistence for security requirements.
    """
    
    def __init__(self, db_path: str = "requirements.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Requirement sets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirement_sets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                version TEXT DEFAULT '1.0.0',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Requirements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id TEXT PRIMARY KEY,
                set_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                engine TEXT,
                engine_config TEXT,
                action TEXT DEFAULT 'warn',
                compliance_tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                created_by TEXT DEFAULT 'system',
                FOREIGN KEY (set_id) REFERENCES requirement_sets(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_set(self, requirement_set: RequirementSet):
        """Save a requirement set to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Upsert set
        cursor.execute("""
            INSERT OR REPLACE INTO requirement_sets 
            (id, name, description, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            requirement_set.id,
            requirement_set.name,
            requirement_set.description,
            requirement_set.version,
            requirement_set.created_at.isoformat() if requirement_set.created_at else now,
            now
        ))
        
        # Delete existing requirements for this set
        cursor.execute("DELETE FROM requirements WHERE set_id = ?", (requirement_set.id,))
        
        # Insert requirements
        for req in requirement_set.requirements:
            cursor.execute("""
                INSERT INTO requirements 
                (id, set_id, name, description, category, severity, enabled,
                 engine, engine_config, action, compliance_tags, 
                 created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.id,
                requirement_set.id,
                req.name,
                req.description,
                req.category.value,
                req.severity.value,
                1 if req.enabled else 0,
                req.engine,
                json.dumps(req.engine_config),
                req.action.value,
                json.dumps(req.compliance_tags),
                req.created_at.isoformat() if req.created_at else now,
                now,
                req.created_by
            ))
        
        conn.commit()
        conn.close()
    
    def load_set(self, set_id: str) -> Optional[RequirementSet]:
        """Load a requirement set from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get set
        cursor.execute("SELECT * FROM requirement_sets WHERE id = ?", (set_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # Get requirements
        cursor.execute("SELECT * FROM requirements WHERE set_id = ?", (set_id,))
        req_rows = cursor.fetchall()
        
        requirements = []
        for r in req_rows:
            req = SecurityRequirement(
                id=r['id'],
                name=r['name'],
                description=r['description'] or '',
                category=RequirementCategory(r['category']),
                severity=Severity(r['severity']),
                enabled=bool(r['enabled']),
                engine=r['engine'],
                engine_config=json.loads(r['engine_config']) if r['engine_config'] else {},
                action=EnforcementAction(r['action']),
                compliance_tags=json.loads(r['compliance_tags']) if r['compliance_tags'] else [],
                created_at=datetime.fromisoformat(r['created_at']) if r['created_at'] else None,
                updated_at=datetime.fromisoformat(r['updated_at']) if r['updated_at'] else None,
                created_by=r['created_by'] or 'system'
            )
            requirements.append(req)
        
        conn.close()
        
        return RequirementSet(
            id=row['id'],
            name=row['name'],
            description=row['description'] or '',
            version=row['version'],
            requirements=requirements,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
    
    def list_sets(self) -> List[Dict]:
        """List all requirement sets (metadata only)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rs.*, COUNT(r.id) as requirement_count
            FROM requirement_sets rs
            LEFT JOIN requirements r ON rs.id = r.set_id
            GROUP BY rs.id
        """)
        
        sets = []
        for row in cursor.fetchall():
            sets.append({
                "id": row['id'],
                "name": row['name'],
                "description": row['description'],
                "version": row['version'],
                "requirement_count": row['requirement_count'],
                "updated_at": row['updated_at']
            })
        
        conn.close()
        return sets
    
    def delete_set(self, set_id: str):
        """Delete a requirement set and its requirements."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM requirements WHERE set_id = ?", (set_id,))
        cursor.execute("DELETE FROM requirement_sets WHERE id = ?", (set_id,))
        conn.commit()
        conn.close()


class RequirementsManager:
    """
    High-level manager for security requirements.
    
    Combines YAML and SQLite storage.
    """
    
    def __init__(self, db_path: str = "requirements.db", config_dir: str = None):
        self.storage = SQLiteStorage(db_path)
        self.config_dir = config_dir
        self._cache: Dict[str, RequirementSet] = {}
    
    def load_from_yaml(self, path: str) -> RequirementSet:
        """Load from YAML and save to database."""
        req_set = YAMLConfigLoader.load(path)
        self.storage.save_set(req_set)
        self._cache[req_set.id] = req_set
        return req_set
    
    def export_to_yaml(self, set_id: str, path: str):
        """Export from database to YAML."""
        req_set = self.get(set_id)
        if req_set:
            YAMLConfigLoader.save(req_set, path)
    
    def get(self, set_id: str) -> Optional[RequirementSet]:
        """Get a requirement set by ID."""
        if set_id in self._cache:
            return self._cache[set_id]
        req_set = self.storage.load_set(set_id)
        if req_set:
            self._cache[set_id] = req_set
        return req_set
    
    def save(self, requirement_set: RequirementSet):
        """Save a requirement set."""
        self.storage.save_set(requirement_set)
        self._cache[requirement_set.id] = requirement_set
    
    def create(self, name: str, description: str = "") -> RequirementSet:
        """Create a new empty requirement set."""
        req_set = RequirementSet(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.now()
        )
        self.save(req_set)
        return req_set
    
    def list_all(self) -> List[Dict]:
        """List all requirement sets."""
        return self.storage.list_sets()
    
    def delete(self, set_id: str):
        """Delete a requirement set."""
        self.storage.delete_set(set_id)
        if set_id in self._cache:
            del self._cache[set_id]
    
    def add_requirement(
        self, 
        set_id: str, 
        name: str,
        description: str,
        category: RequirementCategory,
        severity: Severity,
        engine: str = None,
        engine_config: Dict = None,
        action: EnforcementAction = EnforcementAction.WARN,
        compliance_tags: List[str] = None
    ) -> SecurityRequirement:
        """Add a requirement to a set."""
        req_set = self.get(set_id)
        if not req_set:
            raise ValueError(f"Requirement set {set_id} not found")
        
        req = SecurityRequirement(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            category=category,
            severity=severity,
            engine=engine,
            engine_config=engine_config or {},
            action=action,
            compliance_tags=compliance_tags or [],
            created_at=datetime.now()
        )
        
        req_set.requirements.append(req)
        req_set.updated_at = datetime.now()
        self.save(req_set)
        
        return req


# Default templates
DEFAULT_REQUIREMENTS = RequirementSet(
    id="sentinel-default",
    name="SENTINEL Default Requirements",
    description="Default security requirements based on OWASP LLM Top 10",
    requirements=[
        SecurityRequirement(
            id="req-injection-block",
            name="Block Prompt Injection",
            description="Block detected prompt injection attempts",
            category=RequirementCategory.INJECTION,
            severity=Severity.CRITICAL,
            engine="policy_puppetry_detector",
            action=EnforcementAction.BLOCK,
            compliance_tags=["OWASP-LLM01"]
        ),
        SecurityRequirement(
            id="req-pii-redact",
            name="Redact PII in Outputs",
            description="Prevent PII leakage in model outputs",
            category=RequirementCategory.DATA_PRIVACY,
            severity=Severity.HIGH,
            engine="pii_detector",
            action=EnforcementAction.WARN,
            compliance_tags=["OWASP-LLM06", "EU-AI-ACT-10"]
        ),
        SecurityRequirement(
            id="req-agent-loop",
            name="Detect Agent Loops",
            description="Detect and alert on agent loop behavior",
            category=RequirementCategory.AGENT_SAFETY,
            severity=Severity.HIGH,
            engine="agentic_behavior_analyzer",
            action=EnforcementAction.ALERT,
            compliance_tags=["OWASP-ASI01"]
        ),
        SecurityRequirement(
            id="req-mcp-exfil",
            name="Block Data Exfiltration",
            description="Block MCP tool calls that attempt data exfiltration",
            category=RequirementCategory.DATA_PRIVACY,
            severity=Severity.CRITICAL,
            engine="mcp_security_monitor",
            action=EnforcementAction.BLOCK,
            compliance_tags=["OWASP-LLM06", "OWASP-ASI07"]
        ),
    ]
)
