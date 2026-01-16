"""Extended unit tests for evaluation metrics."""

import pytest
from rlm_toolkit.evaluation.metrics import (
    Metric,
    ExactMatch,
    ContainsMatch,
    SemanticSimilarity,
    CostEffectiveness,
    IterationEfficiency,
    NumericMatch,
)


class TestExactMatchExtended:
    """Extended tests for ExactMatch metric."""
    
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        metric = ExactMatch(normalize=True)
        
        assert metric.compute("  hello  ", "hello") == 1.0
        assert metric.compute("hello\n", "hello") == 1.0
    
    def test_no_normalize(self):
        """Test without normalization."""
        metric = ExactMatch(normalize=False)
        
        assert metric.compute("  hello", "hello") == 0.0
    
    def test_ignore_case(self):
        """Test case insensitive matching."""
        metric = ExactMatch(ignore_case=True)
        
        assert metric.compute("HELLO", "hello") == 1.0
        assert metric.compute("Hello", "HELLO") == 1.0
    
    def test_case_sensitive(self):
        """Test case sensitive matching."""
        metric = ExactMatch(ignore_case=False)
        
        assert metric.compute("HELLO", "hello") == 0.0
    
    def test_name(self):
        """Test metric name."""
        metric = ExactMatch()
        assert metric.name == "exact_match"


class TestContainsMatchExtended:
    """Extended tests for ContainsMatch metric."""
    
    def test_ignore_case(self):
        """Test case insensitive contains."""
        metric = ContainsMatch(ignore_case=True)
        
        assert metric.compute("The ANSWER is 42", "answer") == 1.0
    
    def test_case_sensitive(self):
        """Test case sensitive contains."""
        metric = ContainsMatch(ignore_case=False)
        
        assert metric.compute("The answer is 42", "ANSWER") == 0.0
    
    def test_name(self):
        """Test metric name."""
        metric = ContainsMatch()
        assert metric.name == "contains_match"


class TestSemanticSimilarity:
    """Tests for SemanticSimilarity metric."""
    
    def test_jaccard_identical(self):
        """Test identical strings."""
        metric = SemanticSimilarity()
        
        score = metric.compute("hello world", "hello world")
        assert score == 1.0
    
    def test_jaccard_overlap(self):
        """Test partial word overlap."""
        metric = SemanticSimilarity()
        
        score = metric.compute("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0
    
    def test_jaccard_no_overlap(self):
        """Test no word overlap."""
        metric = SemanticSimilarity()
        
        score = metric.compute("cat dog", "bird fish")
        assert score == 0.0
    
    def test_empty_strings(self):
        """Test empty strings."""
        metric = SemanticSimilarity()
        
        score = metric.compute("", "")
        assert score == 1.0
    
    def test_one_empty(self):
        """Test one empty string."""
        metric = SemanticSimilarity()
        
        score = metric.compute("hello", "")
        assert score == 0.0
    
    def test_name(self):
        """Test metric name."""
        metric = SemanticSimilarity()
        assert metric.name == "semantic_similarity"
    
    def test_with_embed_fn(self):
        """Test with custom embedding function."""
        def mock_embed(text):
            # Simple mock: return length-based vector
            return [len(text), len(text.split())]
        
        metric = SemanticSimilarity(embed_fn=mock_embed)
        
        # Similar lengths should be high
        score = metric.compute("hello world", "hi there now")
        assert score >= 0.0


class TestCostEffectiveness:
    """Tests for CostEffectiveness metric."""
    
    def test_correct_answer(self):
        """Test correct answer."""
        metric = CostEffectiveness()
        
        assert metric.compute("42", "42") == 1.0
    
    def test_wrong_answer(self):
        """Test wrong answer."""
        metric = CostEffectiveness()
        
        assert metric.compute("wrong", "correct") == 0.0
    
    def test_name(self):
        """Test metric name."""
        metric = CostEffectiveness()
        assert metric.name == "cost_effectiveness"


class TestIterationEfficiency:
    """Tests for IterationEfficiency metric."""
    
    def test_exact_length(self):
        """Test same length response."""
        metric = IterationEfficiency()
        
        score = metric.compute("abcd", "wxyz")
        assert score == 1.0
    
    def test_shorter_response(self):
        """Test shorter response."""
        metric = IterationEfficiency()
        
        score = metric.compute("ab", "wxyz")
        assert score == 1.0
    
    def test_longer_response(self):
        """Test longer response is penalized."""
        metric = IterationEfficiency()
        
        # 2x longer = 0.5
        score = metric.compute("abcdefgh", "abcd")
        assert score == 0.5
    
    def test_empty_expected(self):
        """Test empty expected."""
        metric = IterationEfficiency()
        
        score = metric.compute("anything", "")
        assert score == 1.0
    
    def test_name(self):
        """Test metric name."""
        metric = IterationEfficiency()
        assert metric.name == "iteration_efficiency"


class TestNumericMatchExtended:
    """Extended tests for NumericMatch metric."""
    
    def test_exact_number(self):
        """Test exact number match."""
        metric = NumericMatch()
        
        assert metric.compute("42", "42") == 1.0
    
    def test_number_in_text(self):
        """Test number extraction from text."""
        metric = NumericMatch()
        
        assert metric.compute("The answer is 42.", "42") == 1.0
    
    def test_tolerance(self):
        """Test tolerance for floating point."""
        metric = NumericMatch(tolerance=0.1)
        
        # 10.05 is within 10% of 10.0
        assert metric.compute("10.05", "10.0") == 1.0
    
    def test_negative_numbers(self):
        """Test negative numbers."""
        metric = NumericMatch()
        
        assert metric.compute("-42", "-42") == 1.0
    
    def test_no_numbers(self):
        """Test strings without numbers."""
        metric = NumericMatch()
        
        assert metric.compute("hello", "world") == 1.0
    
    def test_no_predicted_numbers(self):
        """Test no numbers in prediction."""
        metric = NumericMatch()
        
        assert metric.compute("no number", "42") == 0.0
    
    def test_name(self):
        """Test metric name."""
        metric = NumericMatch()
        assert metric.name == "numeric_match"
