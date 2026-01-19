# Testing Utilities

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Тестовые утилиты** для RLM приложений

## MockLLM

```python
from rlm_toolkit.testing import MockLLM

# Детерминированные ответы
mock = MockLLM(responses=[
    "Первый ответ",
    "Второй ответ"
])

rlm = RLM(provider=mock)
assert rlm.run("любой").final_answer == "Первый ответ"
assert rlm.run("любой").final_answer == "Второй ответ"
```

## MockEmbeddings

```python
from rlm_toolkit.testing import MockEmbeddings

mock = MockEmbeddings(dimension=1536)
vector = mock.embed_query("тест")
assert len(vector) == 1536
```

## Фикстуры (pytest)

```python
# conftest.py
from rlm_toolkit.testing import fixtures

@pytest.fixture
def mock_rlm():
    return fixtures.create_mock_rlm(responses=["тест"])

def test_my_function(mock_rlm):
    result = my_function(mock_rlm)
    assert result == expected
```

## Связанное

- [Evaluation](evaluation.md)
