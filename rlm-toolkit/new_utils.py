"""New utility module for testing."""


class DataProcessor:
    """Process data for testing purposes."""

    def transform(self, data: list) -> list:
        """Transform input data."""
        return [x * 2 for x in data]


def validate_input(value: str) -> bool:
    """Validate input string."""
    return len(value) > 0


def calculate_score(items: list) -> int:
    """Calculate total score from items."""
    return sum(items)
