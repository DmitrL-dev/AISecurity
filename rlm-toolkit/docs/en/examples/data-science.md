# Data Science Examples

Complete data science workflows with RLM.

## Data Analysis Assistant

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
            You are a data science expert. 
            Use pandas, numpy, matplotlib, seaborn for analysis.
            Always show your work and explain findings.
            """
        )
        
    def analyze(self, data_path: str, question: str) -> str:
        return self.agent.run(f"""
        Load the data from {data_path} and answer: {question}
        
        Steps:
        1. Load and explore the data
        2. Clean if necessary
        3. Perform analysis
        4. Create visualizations
        5. Summarize findings
        """)
    
    def generate_report(self, data_path: str) -> str:
        return self.agent.run(f"""
        Create a comprehensive EDA report for {data_path}:
        
        Include:
        - Dataset overview (shape, types, missing values)
        - Statistical summary
        - Distribution plots for numeric columns
        - Correlation analysis
        - Key insights
        
        Save all charts to ./output/
        """)

# Usage
analyst = DataAnalyst()
result = analyst.analyze(
    "sales_data.csv",
    "What are the top performing products and seasonal trends?"
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
            You are an ML engineer. Build production-quality models.
            Use scikit-learn, xgboost, or pytorch as appropriate.
            Always include:
            - Data preprocessing
            - Train/test split
            - Cross-validation
            - Metrics reporting
            - Model saving
            """
        )
        
    def build_model(self, data_path: str, target: str, task_type: str) -> str:
        return self.agent.run(f"""
        Build a {task_type} model:
        - Data: {data_path}
        - Target variable: {target}
        
        Steps:
        1. Load and preprocess data
        2. Feature engineering
        3. Train multiple models (compare at least 3)
        4. Evaluate with appropriate metrics
        5. Select best model
        6. Save model to model.pkl
        7. Generate prediction code
        """)
    
    def explain_predictions(self, model_path: str, data_path: str) -> str:
        return self.agent.run(f"""
        Load model from {model_path} and explain predictions on {data_path}:
        - Use SHAP or LIME for interpretability
        - Show feature importance
        - Explain top 5 predictions
        """)

# Usage
builder = MLBuilder()
result = builder.build_model(
    "customer_churn.csv",
    target="churned",
    task_type="classification"
)
```

## Time Series Forecasting

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL

class TimeSeriesForecaster:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL(max_execution_time=120)],
            system_prompt="""
            You are a time series expert.
            Use statsmodels, prophet, or sklearn for forecasting.
            Always check for stationarity and seasonality.
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
        Forecast time series data:
        - File: {data_path}
        - Date column: {date_col}
        - Value column: {value_col}
        - Forecast periods: {periods}
        
        Steps:
        1. Load and parse dates
        2. Visualize the series
        3. Check stationarity (ADF test)
        4. Decompose into trend, seasonal, residual
        5. Try multiple models (ARIMA, Prophet, etc.)
        6. Evaluate with MAPE, RMSE
        7. Generate forecast
        8. Plot forecast with confidence intervals
        9. Save forecast to forecast.csv
        """)
    
    def detect_anomalies(self, data_path: str, date_col: str, value_col: str) -> str:
        return self.agent.run(f"""
        Detect anomalies in time series {data_path}:
        - Use isolation forest or statistical methods
        - Visualize anomalies on the chart
        - List dates with anomalies
        """)

# Usage
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
from rlm_toolkit.tools import Tool
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
        # Generate SQL
        sql = self.rlm.run(f"""
        Convert this question to SQL:
        
        Question: {natural_language}
        
        Database schema:
        {self.schema}
        
        Return ONLY the SQL query, no explanation.
        """)
        
        # Execute
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
        
        # Format answer
        answer = self.rlm.run(f"""
        Answer the question naturally based on the data:
        
        Question: {natural_language}
        SQL: {sql}
        Results: {results[:50]}
        Columns: {columns}
        """)
        
        return {
            "question": natural_language,
            "sql": sql,
            "results": results,
            "answer": answer
        }

# Usage
nl2sql = NL2SQL("sales.db")
result = nl2sql.query("What were total sales last month by region?")
print(f"SQL: {result['sql']}")
print(f"Answer: {result['answer']}")
```

## Visualization Generator

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, FileWriter

class VizGenerator:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL(), FileWriter()],
            system_prompt="""
            Create beautiful, publication-quality visualizations.
            Use matplotlib, seaborn, or plotly.
            Follow best practices for data visualization.
            """
        )
        
    def create_chart(self, data_path: str, chart_type: str, instructions: str) -> str:
        return self.agent.run(f"""
        Create a {chart_type} chart from {data_path}:
        
        Instructions: {instructions}
        
        Requirements:
        - Use a professional color palette
        - Add proper labels, title, legend
        - Make it readable and clear
        - Save as both PNG and interactive HTML
        """)
    
    def create_dashboard(self, data_path: str, metrics: list) -> str:
        return self.agent.run(f"""
        Create a dashboard with these metrics: {metrics}
        Data: {data_path}
        
        Use plotly to create an interactive dashboard with:
        - Multiple charts in a grid layout
        - Filters/dropdowns where appropriate
        - Save as dashboard.html
        """)

# Usage
viz = VizGenerator()
result = viz.create_chart(
    "sales_data.csv",
    "bar chart",
    "Show monthly revenue by product category, stacked"
)
```

## A/B Test Analyzer

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL
from pydantic import BaseModel
from typing import Optional

class ABTestResult(BaseModel):
    test_name: str
    control_mean: float
    treatment_mean: float
    lift: float
    p_value: float
    significant: bool
    confidence_interval: tuple
    recommendation: str

class ABTestAnalyzer:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL()],
            system_prompt="""
            You are a statistics expert analyzing A/B tests.
            Use scipy for statistical tests.
            Report results clearly with business implications.
            """
        )
        
    def analyze(
        self, 
        control_data: str, 
        treatment_data: str,
        metric: str
    ) -> str:
        return self.agent.run(f"""
        Analyze this A/B test:
        - Control: {control_data}
        - Treatment: {treatment_data}
        - Metric: {metric}
        
        Perform:
        1. Descriptive statistics for both groups
        2. Normality check
        3. T-test or Mann-Whitney U test
        4. Calculate effect size (Cohen's d)
        5. Power analysis
        6. Visualize distributions
        7. Provide business recommendation
        """)
    
    def sample_size_calculator(
        self, 
        baseline_rate: float,
        minimum_detectable_effect: float,
        power: float = 0.8,
        significance: float = 0.05
    ) -> str:
        return self.agent.run(f"""
        Calculate required sample size:
        - Baseline conversion rate: {baseline_rate}
        - Minimum detectable effect: {minimum_detectable_effect}
        - Power: {power}
        - Significance level: {significance}
        
        Show the formula and calculation.
        """)

# Usage
analyzer = ABTestAnalyzer()
result = analyzer.analyze(
    "control_clicks.csv",
    "treatment_clicks.csv",
    "click_through_rate"
)
print(result)
```

## Data Quality Checker

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL

class DataQualityChecker:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[PythonREPL()],
            system_prompt="""
            Check data quality thoroughly.
            Report issues and suggest fixes.
            """
        )
        
    def check(self, data_path: str) -> str:
        return self.agent.run(f"""
        Perform comprehensive data quality check on {data_path}:
        
        1. Missing Values:
           - Count and percentage per column
           - Pattern analysis (MCAR, MAR, MNAR)
        
        2. Data Types:
           - Verify expected types
           - Find type mismatches
        
        3. Duplicates:
           - Exact duplicates
           - Near-duplicates (fuzzy matching)
        
        4. Outliers:
           - Statistical outliers (IQR, Z-score)
           - Domain-specific anomalies
        
        5. Consistency:
           - Format consistency (dates, phones, etc.)
           - Referential integrity
        
        6. Completeness:
           - Required fields
           - Valid value ranges
        
        Generate a quality report with:
        - Overall quality score (0-100)
        - Issues by severity
        - Recommended actions
        """)

# Usage
checker = DataQualityChecker()
report = checker.check("customer_data.csv")
print(report)
```

## Related

- [Examples Gallery](./index.md)
- [Tutorial: Agents](../tutorials/04-agents.md)
- [How-to: Tools](../how-to/tools.md)
