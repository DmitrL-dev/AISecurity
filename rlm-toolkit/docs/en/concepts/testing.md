# Testing Utilities

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Test helpers** for RLM applications

## MockLLM

```python
from rlm_toolkit.testing import MockLLM

# Deterministic responses
mock = MockLLM(responses=[
    "First response",
    "Second response"
])

rlm = RLM(provider=mock)
assert rlm.run("any").final_answer == "First response"
assert rlm.run("any").final_answer == "Second response"
```

## MockEmbeddings

```python
from rlm_toolkit.testing import MockEmbeddings

mock = MockEmbeddings(dimension=1536)
vector = mock.embed_query("test")
assert len(vector) == 1536
```

## Fixtures (pytest)

```python
# conftest.py
from rlm_toolkit.testing import fixtures

@pytest.fixture
def mock_rlm():
    return fixtures.create_mock_rlm(responses=["test"])

def test_my_function(mock_rlm):
    result = my_function(mock_rlm)
    assert result == expected
```

## Related

- [Evaluation](evaluation.md)
