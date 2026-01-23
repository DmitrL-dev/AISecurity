"""Test module for fact extraction."""


class TestExtractor:
    """Test class for extraction verification."""

    def verify_extraction(self, data: str) -> bool:
        """Verify that extraction works correctly."""
        return len(data) > 0


def process_test_data(input_value: int) -> int:
    """Process test data for validation."""
    return input_value * 2
