"""
SENTINEL Strike - Orchestrator Tests

Tests for strike.orchestrator module.
"""

import pytest
from strike.orchestrator import (
    DefenseType,
    TargetProfile,
    AttackResult,
    detect_defense,
    DEFENSE_PATTERNS,
    CATEGORY_PRIORITY,
    get_priority_categories,
    get_best_category,
)


class TestDefenseType:
    """Tests for DefenseType enum."""
    
    def test_defense_types_exist(self):
        """Test all defense types are defined."""
        assert DefenseType.NONE is not None
        assert DefenseType.KEYWORD_BLOCK is not None
        assert DefenseType.OUTPUT_FILTER is not None
        assert DefenseType.LLM_JUDGE is not None
        assert DefenseType.POLICY_CITE is not None
        assert DefenseType.MULTI_LAYER is not None
        assert DefenseType.UNKNOWN is not None
    
    def test_defense_type_values(self):
        """Test defense type string values."""
        assert DefenseType.NONE.value == "none"
        assert DefenseType.KEYWORD_BLOCK.value == "keyword_block"
        assert DefenseType.UNKNOWN.value == "unknown"


class TestTargetProfile:
    """Tests for TargetProfile dataclass."""
    
    def test_create_profile(self):
        """Test creating a target profile."""
        profile = TargetProfile(
            url="https://example.com",
            name="Test Target",
        )
        assert profile.url == "https://example.com"
        assert profile.name == "Test Target"
        assert profile.defenses == []
        assert profile.blocked_words == []
    
    def test_add_defense(self):
        """Test adding defenses to profile."""
        profile = TargetProfile(url="test")
        profile.add_defense(DefenseType.KEYWORD_BLOCK)
        
        assert DefenseType.KEYWORD_BLOCK in profile.defenses
    
    def test_add_defense_no_duplicates(self):
        """Test that duplicate defenses are not added."""
        profile = TargetProfile(url="test")
        profile.add_defense(DefenseType.KEYWORD_BLOCK)
        profile.add_defense(DefenseType.KEYWORD_BLOCK)
        
        assert len(profile.defenses) == 1
    
    def test_add_blocked_word(self):
        """Test adding blocked words."""
        profile = TargetProfile(url="test")
        profile.add_blocked_word("password")
        profile.add_blocked_word("secret")
        
        assert "password" in profile.blocked_words
        assert "secret" in profile.blocked_words
    
    def test_get_primary_defense(self):
        """Test getting primary defense."""
        profile = TargetProfile(url="test")
        profile.add_defense(DefenseType.KEYWORD_BLOCK)
        profile.add_defense(DefenseType.LLM_JUDGE)
        
        primary = profile.get_primary_defense()
        assert primary == DefenseType.KEYWORD_BLOCK


class TestAttackResult:
    """Tests for AttackResult dataclass."""
    
    def test_create_result(self):
        """Test creating attack result."""
        result = AttackResult(
            success=True,
            payload="test payload",
            response="test response",
        )
        assert result.success is True
        assert result.payload == "test payload"
        assert result.response == "test response"
    
    def test_result_to_dict(self):
        """Test converting result to dict."""
        result = AttackResult(
            success=True,
            payload="test",
            response="response",
            category="jailbreak",
        )
        d = result.to_dict()
        
        assert d["success"] is True
        assert d["payload"] == "test"
        assert d["category"] == "jailbreak"


class TestDetectDefense:
    """Tests for detect_defense function."""
    
    def test_detect_none(self):
        """Test detecting no defense."""
        response = "Here is the information you requested."
        defense = detect_defense(response)
        assert defense == DefenseType.NONE
    
    def test_detect_keyword_block(self):
        """Test detecting keyword blocking."""
        response = "I cannot discuss that word."
        defense = detect_defense(response)
        assert defense == DefenseType.KEYWORD_BLOCK
    
    def test_detect_policy_cite(self):
        """Test detecting policy citation."""
        response = "According to our content policy, I cannot help with that."
        defense = detect_defense(response)
        assert defense == DefenseType.POLICY_CITE
    
    def test_detect_llm_judge(self):
        """Test detecting LLM judge."""
        response = "This request has been flagged for review."
        defense = detect_defense(response)
        assert defense == DefenseType.LLM_JUDGE
    
    def test_empty_response(self):
        """Test with empty response."""
        defense = detect_defense("")
        assert defense == DefenseType.UNKNOWN


class TestCategoryPriority:
    """Tests for category priority."""
    
    def test_priority_dict_exists(self):
        """Test CATEGORY_PRIORITY is populated."""
        assert len(CATEGORY_PRIORITY) > 0
        assert DefenseType.NONE in CATEGORY_PRIORITY
        assert DefenseType.UNKNOWN in CATEGORY_PRIORITY
    
    def test_get_priority_categories(self):
        """Test getting priority categories."""
        cats = get_priority_categories(DefenseType.NONE)
        assert isinstance(cats, list)
        assert len(cats) > 0
    
    def test_get_best_category(self):
        """Test getting best category."""
        best = get_best_category(DefenseType.KEYWORD_BLOCK)
        assert best is not None
        assert isinstance(best, str)
    
    def test_get_best_category_with_exclude(self):
        """Test getting best category with exclusions."""
        cats = get_priority_categories(DefenseType.NONE)
        first = cats[0]
        
        best = get_best_category(DefenseType.NONE, exclude=[first])
        assert best != first
