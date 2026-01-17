# How-to: Multi-Agent Systems

Recipes for building multi-agent applications.

## Create Meta Matrix Network

```python
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent

matrix = MetaMatrix(
    topology="mesh",
    consensus="raft",
    enable_discovery=True
)
```

## Define Specialized Agents

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents.multiagent import Agent
from rlm_toolkit.tools import WebSearchTool, PythonREPL

researcher = Agent(
    name="researcher",
    description="Searches and analyzes information",
    llm=RLM.from_openai("gpt-4o"),
    tools=[WebSearchTool()]
)

coder = Agent(
    name="coder",
    description="Writes and executes Python code",
    llm=RLM.from_openai("gpt-4o"),
    tools=[PythonREPL()]
)

writer = Agent(
    name="writer",
    description="Writes clear documentation",
    llm=RLM.from_anthropic("claude-3-sonnet"),
    tools=[]
)
```

## Register and Run

```python
matrix.register(researcher)
matrix.register(coder)
matrix.register(writer)

result = matrix.run(
    "Research Python trends, analyze with code, write a report"
)
```

## Sequential Workflow

```python
from rlm_toolkit.agents.multiagent import SequentialWorkflow

workflow = SequentialWorkflow([
    ("researcher", "Find Python framework benchmarks"),
    ("coder", "Create comparison chart"),
    ("writer", "Write summary report")
])

result = matrix.run_workflow(workflow)
```

## Parallel Workflow

```python
from rlm_toolkit.agents.multiagent import ParallelWorkflow

workflow = ParallelWorkflow({
    "researcher": "Research aspect A",
    "coder": "Build prototype B"
})

results = matrix.run_workflow(workflow)
```

## Agent Communication

```python
# Direct message
researcher.send_message(
    to="coder",
    content="Here is the data",
    data=research_results
)

# Broadcast
matrix.broadcast(
    from_agent="leader",
    content="New task available"
)

# Request-response
response = researcher.request(
    to="coder",
    action="analyze",
    data=raw_data,
    timeout=30
)
```

## Trust Zones

```python
from rlm_toolkit.agents.multiagent import TrustZone

confidential = TrustZone(
    name="confidential",
    level=2,
    encryption_enabled=True
)

secure_agent = Agent(
    name="data_processor",
    trust_zone=confidential,
    encryption_key="your-256-bit-key"
)
```

## Monitoring

```python
from rlm_toolkit.callbacks import MultiAgentCallback

callback = MultiAgentCallback(log_messages=True)
matrix = MetaMatrix(callbacks=[callback])

# Get metrics
metrics = matrix.get_metrics()
print(f"Messages: {metrics['total_messages']}")
print(f"Activity: {metrics['agent_activity']}")
```

## Related

- [Concept: Multi-Agent](../concepts/multiagent.md)
- [Tutorial: Multi-Agent](../tutorials/09-multiagent.md)
