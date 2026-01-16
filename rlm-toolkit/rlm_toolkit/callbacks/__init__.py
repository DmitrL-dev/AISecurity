"""
Callbacks and Handlers
======================

Callback system for monitoring and logging LLM operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging


@dataclass
class LLMEvent:
    """Event data for LLM operations."""
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0
    cost: float = 0
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None


class BaseCallback(ABC):
    """Base callback handler."""
    
    @abstractmethod
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        pass
    
    @abstractmethod
    def on_llm_end(self, response: str, **kwargs) -> None:
        pass
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        pass


class LoggingCallback(BaseCallback):
    """Log all LLM operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("rlm_toolkit")
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        self.logger.info(f"LLM Start: {prompt[:100]}...")
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        self.logger.info(f"LLM End: {response[:100]}...")
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        self.logger.error(f"LLM Error: {error}")


class FileCallback(BaseCallback):
    """Write LLM operations to file."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        self._write({"event": "start", "prompt": prompt, **kwargs})
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        self._write({"event": "end", "response": response, **kwargs})
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        self._write({"event": "error", "error": str(error), **kwargs})
    
    def _write(self, data: Dict) -> None:
        data["timestamp"] = datetime.now().isoformat()
        with open(self.file_path, "a") as f:
            f.write(json.dumps(data) + "\n")


class LangSmithCallback(BaseCallback):
    """Send traces to LangSmith."""
    
    def __init__(self, api_key: Optional[str] = None, project: str = "default"):
        import os
        self.api_key = api_key or os.getenv("LANGSMITH_API_KEY")
        self.project = project
        self._run_id = None
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        try:
            from langsmith import Client
            client = Client(api_key=self.api_key)
            # Create run
            self._run_id = client.create_run(
                name="llm_call",
                run_type="llm",
                inputs={"prompt": prompt},
                project_name=self.project,
            ).id
        except ImportError:
            pass
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        try:
            from langsmith import Client
            if self._run_id:
                client = Client(api_key=self.api_key)
                client.update_run(self._run_id, outputs={"response": response})
        except ImportError:
            pass


class LangfuseCallback(BaseCallback):
    """Send traces to Langfuse."""
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: str = "https://cloud.langfuse.com",
    ):
        import os
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host
        self._trace = None
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        try:
            from langfuse import Langfuse
            langfuse = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host,
            )
            self._trace = langfuse.trace(name="llm_call")
            self._trace.generation(name="llm", input=prompt)
        except ImportError:
            pass
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        if self._trace:
            self._trace.update(output=response)


class WeightsAndBiasesCallback(BaseCallback):
    """Log to Weights & Biases."""
    
    def __init__(self, project: str = "rlm-toolkit"):
        self.project = project
        self._run = None
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        try:
            import wandb
            if not self._run:
                self._run = wandb.init(project=self.project)
            wandb.log({"prompt": prompt, "prompt_length": len(prompt)})
        except ImportError:
            pass
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        try:
            import wandb
            wandb.log({
                "response": response,
                "response_length": len(response),
                **kwargs,
            })
        except ImportError:
            pass


class CometCallback(BaseCallback):
    """Log to Comet ML."""
    
    def __init__(self, project: str = "rlm-toolkit"):
        self.project = project
        self._experiment = None
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        try:
            from comet_ml import Experiment
            if not self._experiment:
                self._experiment = Experiment(project_name=self.project)
            self._experiment.log_text(prompt, metadata={"type": "prompt"})
        except ImportError:
            pass
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        if self._experiment:
            self._experiment.log_text(response, metadata={"type": "response"})
            for key, value in kwargs.items():
                self._experiment.log_metric(key, value)


class MLflowCallback(BaseCallback):
    """Log to MLflow."""
    
    def __init__(self, experiment_name: str = "rlm-toolkit"):
        self.experiment_name = experiment_name
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        try:
            import mlflow
            mlflow.set_experiment(self.experiment_name)
            mlflow.start_run()
            mlflow.log_param("prompt", prompt[:250])
        except ImportError:
            pass
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        try:
            import mlflow
            mlflow.log_param("response", response[:250])
            for key, value in kwargs.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value)
            mlflow.end_run()
        except ImportError:
            pass


class PrometheusCallback(BaseCallback):
    """Export metrics to Prometheus."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self._counter = None
        self._histogram = None
    
    def _init_metrics(self):
        if self._counter is None:
            try:
                from prometheus_client import Counter, Histogram, start_http_server
                self._counter = Counter("llm_requests_total", "Total LLM requests", ["model", "provider"])
                self._histogram = Histogram("llm_latency_seconds", "LLM latency", ["model"])
                start_http_server(self.port)
            except ImportError:
                pass
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        self._init_metrics()
        self._start_time = datetime.now()
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        if self._counter:
            model = kwargs.get("model", "unknown")
            provider = kwargs.get("provider", "unknown")
            self._counter.labels(model=model, provider=provider).inc()
            
            latency = (datetime.now() - self._start_time).total_seconds()
            self._histogram.labels(model=model).observe(latency)


class OpenTelemetryCallback(BaseCallback):
    """Send traces via OpenTelemetry."""
    
    def __init__(self, service_name: str = "rlm-toolkit"):
        self.service_name = service_name
        self._tracer = None
        self._span = None
    
    def _init_tracer(self):
        if self._tracer is None:
            try:
                from opentelemetry import trace
                from opentelemetry.sdk.trace import TracerProvider
                
                trace.set_tracer_provider(TracerProvider())
                self._tracer = trace.get_tracer(self.service_name)
            except ImportError:
                pass
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        self._init_tracer()
        if self._tracer:
            self._span = self._tracer.start_span("llm_call")
            self._span.set_attribute("prompt", prompt[:1000])
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        if self._span:
            self._span.set_attribute("response", response[:1000])
            for key, value in kwargs.items():
                self._span.set_attribute(key, str(value))
            self._span.end()


class ArizeCallback(BaseCallback):
    """Log to Arize AI for ML observability."""
    
    def __init__(self, api_key: Optional[str] = None, space_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.getenv("ARIZE_API_KEY")
        self.space_key = space_key or os.getenv("ARIZE_SPACE_KEY")
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        self._prompt = prompt
        self._start = datetime.now()
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        try:
            from arize.pandas.logger import Client
            client = Client(api_key=self.api_key, space_key=self.space_key)
            # Log prediction
        except ImportError:
            pass


class HeliconeCallback(BaseCallback):
    """Log to Helicone."""
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.getenv("HELICONE_API_KEY")
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        pass  # Helicone uses proxy, not callbacks
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        pass


class CallbackManager:
    """Manage multiple callbacks."""
    
    def __init__(self, callbacks: Optional[List[BaseCallback]] = None):
        self.callbacks = callbacks or []
    
    def add(self, callback: BaseCallback) -> None:
        self.callbacks.append(callback)
    
    def remove(self, callback: BaseCallback) -> None:
        self.callbacks.remove(callback)
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        for callback in self.callbacks:
            try:
                callback.on_llm_start(prompt, **kwargs)
            except Exception:
                pass
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        for callback in self.callbacks:
            try:
                callback.on_llm_end(response, **kwargs)
            except Exception:
                pass
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        for callback in self.callbacks:
            try:
                callback.on_llm_error(error, **kwargs)
            except Exception:
                pass
