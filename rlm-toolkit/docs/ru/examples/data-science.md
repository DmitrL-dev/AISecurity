# Примеры Data Science

Полные data science workflow с RLM.

## Ассистент анализа данных

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL
import pandas as pd

class DataAnalyst:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL(max_execution_time=60)],
            system_prompt="""
            Ты эксперт data science. 
            Используй pandas, numpy, matplotlib, seaborn для анализа.
            Всегда показывай работу и объясняй находки.
            """
        )
        
    def analyze(self, data_path: str, question: str) -> str:
        return self.agent.run(f"""
        Загрузи данные из {data_path} и ответь: {question}
        
        Шаги:
        1. Загрузи и исследуй данные
        2. Очисти если нужно
        3. Выполни анализ
        4. Создай визуализации
        5. Суммируй находки
        """)
    
    def generate_report(self, data_path: str) -> str:
        return self.agent.run(f"""
        Создай полный EDA отчёт для {data_path}:
        
        Включи:
        - Обзор датасета (размер, типы, пропуски)
        - Статистическое резюме
        - Графики распределений числовых колонок
        - Корреляционный анализ
        - Ключевые инсайты
        
        Сохрани все графики в ./output/
        """)

# Использование
analyst = DataAnalyst()
result = analyst.analyze(
    "sales_data.csv",
    "Какие топ продукты и сезонные тренды?"
)
print(result)
```

## ML Model Builder

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, FileWriter

class MLBuilder:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[
                PythonREPL(max_execution_time=120),
                FileWriter()
            ],
            system_prompt="""
            Ты ML инженер. Строй production-quality модели.
            Используй scikit-learn, xgboost, или pytorch.
            Всегда включай:
            - Препроцессинг данных
            - Train/test split
            - Cross-validation
            - Метрики
            - Сохранение модели
            """
        )
        
    def build_model(self, data_path: str, target: str, task_type: str) -> str:
        return self.agent.run(f"""
        Построй {task_type} модель:
        - Данные: {data_path}
        - Целевая переменная: {target}
        
        Шаги:
        1. Загрузи и подготовь данные
        2. Feature engineering
        3. Обучи несколько моделей (сравни минимум 3)
        4. Оцени подходящими метриками
        5. Выбери лучшую модель
        6. Сохрани модель в model.pkl
        7. Сгенерируй код предсказаний
        """)
    
    def explain_predictions(self, model_path: str, data_path: str) -> str:
        return self.agent.run(f"""
        Загрузи модель из {model_path} и объясни предсказания на {data_path}:
        - Используй SHAP или LIME для интерпретации
        - Покажи важность признаков
        - Объясни топ-5 предсказаний
        """)

# Использование
builder = MLBuilder()
result = builder.build_model(
    "customer_churn.csv",
    target="churned",
    task_type="classification"
)
```

## Прогнозирование временных рядов

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL

class TimeSeriesForecaster:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL(max_execution_time=120)],
            system_prompt="""
            Ты эксперт по временным рядам.
            Используй statsmodels, prophet, или sklearn для прогнозов.
            Всегда проверяй стационарность и сезонность.
            """
        )
        
    def forecast(
        self, 
        data_path: str, 
        date_col: str, 
        value_col: str,
        periods: int = 30
    ) -> str:
        return self.agent.run(f"""
        Прогнозируй временной ряд:
        - Файл: {data_path}
        - Колонка даты: {date_col}
        - Колонка значений: {value_col}
        - Периодов прогноза: {periods}
        
        Шаги:
        1. Загрузи и разбери даты
        2. Визуализируй ряд
        3. Проверь стационарность (ADF тест)
        4. Декомпозиция: тренд, сезонность, остаток
        5. Попробуй несколько моделей (ARIMA, Prophet и т.д.)
        6. Оцени с MAPE, RMSE
        7. Сгенерируй прогноз
        8. Построй график прогноза с доверительными интервалами
        9. Сохрани прогноз в forecast.csv
        """)
    
    def detect_anomalies(self, data_path: str, date_col: str, value_col: str) -> str:
        return self.agent.run(f"""
        Найди аномалии во временном ряду {data_path}:
        - Используй isolation forest или статистические методы
        - Визуализируй аномалии на графике
        - Выведи даты с аномалиями
        """)

# Использование
forecaster = TimeSeriesForecaster()
result = forecaster.forecast(
    "monthly_sales.csv",
    date_col="date",
    value_col="revenue",
    periods=12
)
```

## Natural Language to SQL

```python
from rlm_toolkit import RLM
import sqlite3

class NL2SQL:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.rlm = RLM.from_openai("gpt-4o")
        self.schema = self._get_schema()
        
    def _get_schema(self) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND sql IS NOT NULL
        """)
        schemas = cursor.fetchall()
        conn.close()
        return "\n".join([s[0] for s in schemas])
    
    def query(self, natural_language: str) -> dict:
        # Генерация SQL
        sql = self.rlm.run(f"""
        Преобразуй вопрос в SQL:
        
        Вопрос: {natural_language}
        
        Схема базы данных:
        {self.schema}
        
        Верни ТОЛЬКО SQL запрос, без объяснений.
        """)
        
        # Выполнение
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(sql.strip())
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
        except Exception as e:
            return {"error": str(e), "sql": sql}
        finally:
            conn.close()
        
        # Форматирование ответа
        answer = self.rlm.run(f"""
        Ответь на вопрос естественно на основе данных:
        
        Вопрос: {natural_language}
        SQL: {sql}
        Результаты: {results[:50]}
        Колонки: {columns}
        """)
        
        return {
            "question": natural_language,
            "sql": sql,
            "results": results,
            "answer": answer
        }

# Использование
nl2sql = NL2SQL("sales.db")
result = nl2sql.query("Какие были продажи за прошлый месяц по регионам?")
print(f"SQL: {result['sql']}")
print(f"Ответ: {result['answer']}")
```

## Генератор визуализаций

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, FileWriter

class VizGenerator:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL(), FileWriter()],
            system_prompt="""
            Создавай красивые, publication-quality визуализации.
            Используй matplotlib, seaborn, или plotly.
            Следуй лучшим практикам визуализации данных.
            """
        )
        
    def create_chart(self, data_path: str, chart_type: str, instructions: str) -> str:
        return self.agent.run(f"""
        Создай {chart_type} график из {data_path}:
        
        Инструкции: {instructions}
        
        Требования:
        - Используй профессиональную цветовую палитру
        - Добавь правильные подписи, заголовок, легенду
        - Сделай читаемым и понятным
        - Сохрани как PNG и интерактивный HTML
        """)
    
    def create_dashboard(self, data_path: str, metrics: list) -> str:
        return self.agent.run(f"""
        Создай дашборд с метриками: {metrics}
        Данные: {data_path}
        
        Используй plotly для интерактивного дашборда с:
        - Несколькими графиками в сетке
        - Фильтрами/dropdown где уместно
        - Сохрани как dashboard.html
        """)

# Использование
viz = VizGenerator()
result = viz.create_chart(
    "sales_data.csv",
    "столбчатая диаграмма",
    "Покажи месячную выручку по категориям продуктов, stacked"
)
```

## A/B тест анализатор

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL

class ABTestAnalyzer:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL()],
            system_prompt="""
            Ты эксперт статистики, анализирующий A/B тесты.
            Используй scipy для статистических тестов.
            Сообщай результаты ясно с бизнес-выводами.
            """
        )
        
    def analyze(
        self, 
        control_data: str, 
        treatment_data: str,
        metric: str
    ) -> str:
        return self.agent.run(f"""
        Проанализируй A/B тест:
        - Control: {control_data}
        - Treatment: {treatment_data}
        - Метрика: {metric}
        
        Выполни:
        1. Описательная статистика для обеих групп
        2. Проверка нормальности
        3. T-test или Mann-Whitney U test
        4. Рассчитай effect size (Cohen's d)
        5. Power analysis
        6. Визуализируй распределения
        7. Дай бизнес-рекомендацию
        """)
    
    def sample_size_calculator(
        self, 
        baseline_rate: float,
        minimum_detectable_effect: float,
        power: float = 0.8,
        significance: float = 0.05
    ) -> str:
        return self.agent.run(f"""
        Рассчитай необходимый размер выборки:
        - Baseline conversion rate: {baseline_rate}
        - Минимальный детектируемый эффект: {minimum_detectable_effect}
        - Power: {power}
        - Уровень значимости: {significance}
        
        Покажи формулу и расчёт.
        """)

# Использование
analyzer = ABTestAnalyzer()
result = analyzer.analyze(
    "control_clicks.csv",
    "treatment_clicks.csv",
    "click_through_rate"
)
print(result)
```

## Проверка качества данных

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL

class DataQualityChecker:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL()],
            system_prompt="""
            Проверяй качество данных тщательно.
            Сообщай о проблемах и предлагай исправления.
            """
        )
        
    def check(self, data_path: str) -> str:
        return self.agent.run(f"""
        Выполни комплексную проверку качества данных {data_path}:
        
        1. Пропущенные значения:
           - Количество и процент по колонкам
           - Анализ паттернов (MCAR, MAR, MNAR)
        
        2. Типы данных:
           - Проверь ожидаемые типы
           - Найди несоответствия
        
        3. Дубликаты:
           - Точные дубликаты
           - Почти-дубликаты (fuzzy matching)
        
        4. Выбросы:
           - Статистические выбросы (IQR, Z-score)
           - Доменно-специфичные аномалии
        
        5. Консистентность:
           - Консистентность форматов (даты, телефоны и т.д.)
           - Referential integrity
        
        6. Полнота:
           - Обязательные поля
           - Валидные диапазоны значений
        
        Сгенерируй отчёт качества с:
        - Общий балл качества (0-100)
        - Проблемы по серьёзности
        - Рекомендуемые действия
        """)

# Использование
checker = DataQualityChecker()
report = checker.check("customer_data.csv")
print(report)
```

## Связанное

- [Галерея примеров](./index.md)
- [Туториал: Агенты](../tutorials/04-agents.md)
- [How-to: Инструменты](../how-to/tools.md)
