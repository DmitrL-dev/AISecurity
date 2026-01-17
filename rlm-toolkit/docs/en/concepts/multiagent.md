# Multi-Agent Systems

RLM-Toolkit implements decentralized P2P multi-agent systems with Meta Matrix architecture.

## What is Multi-Agent?

Multi-Agent Systems (MAS) enable:
- **Collaboration**: Agents work together on complex tasks
- **Specialization**: Each agent handles specific domains
- **Scalability**: Add agents without redesigning system
- **Resilience**: No single point of failure

## Agent Topologies

### Centralized (Orchestrator)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Centralized Topology                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌─────────────┐                              │
│                    │ Orchestrator│                              │
│                    └──────┬──────┘                              │
│              ┌────────────┼────────────┐                        │
│              ▼            ▼            ▼                        │
│        ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│        │ Agent A │  │ Agent B │  │ Agent C │                   │
│        └─────────┘  └─────────┘  └─────────┘                   │
│                                                                  │
│        ✅ Simple control                                        │
│        ❌ Single point of failure                               │
│        ❌ Limited scalability                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Decentralized (P2P)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Decentralized (P2P) Topology                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│             ┌─────────┐ ←──→ ┌─────────┐                       │
│             │ Agent A │      │ Agent B │                       │
│             └────┬────┘      └────┬────┘                       │
│                  │                │                              │
│                  ▼                ▼                              │
│             ┌─────────┐ ←──→ ┌─────────┐                       │
│             │ Agent C │      │ Agent D │                       │
│             └─────────┘      └─────────┘                       │
│                                                                  │
│        ✅ No single point of failure                            │
│        ✅ Highly scalable                                       │
│        ✅ Resilient                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Meta Matrix Architecture

RLM's decentralized multi-agent system:

```python
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent, TrustZone

# Create Meta Matrix network
matrix = MetaMatrix(
    topology="mesh",
    consensus="raft",
    enable_discovery=True
)

# Define specialized agents
researcher = Agent(
    name="researcher",
    description="Searches and analyzes information",
    llm=RLM.from_openai("gpt-4o"),
    tools=[WebSearchTool(), ArxivTool()]
)

analyst = Agent(
    name="analyst",
    description="Analyzes data and creates reports",
    llm=RLM.from_openai("gpt-4o"),
    tools=[PythonREPL(), ChartTool()]
)

writer = Agent(
    name="writer",
    description="Writes clear, engaging content",
    llm=RLM.from_anthropic("claude-3-sonnet"),
    tools=[FileWriter()]
)

# Register agents
matrix.register(researcher)
matrix.register(analyst)
matrix.register(writer)

# Run collaborative task
result = matrix.run(
    "Research AI trends 2024, analyze data, write a report"
)
```

## Trust Zones

Security boundaries for agent communication:

```python
from rlm_toolkit.agents.multiagent import TrustZone

# Define trust zones
public_zone = TrustZone(
    name="public",
    level=0,
    allowed_agents=["assistant"]
)

internal_zone = TrustZone(
    name="internal",
    level=1,
    allowed_agents=["researcher", "analyst"]
)

confidential_zone = TrustZone(
    name="confidential",
    level=2,
    allowed_agents=["data_processor"],
    encryption_enabled=True
)

# Assign zones to agents
researcher = Agent(
    name="researcher",
    trust_zone=internal_zone,
    ...
)

data_processor = Agent(
    name="data_processor",
    trust_zone=confidential_zone,
    encryption_key="your-256-bit-key"
)
```

## Communication Patterns

### Direct Messaging

```python
# Agent A sends to Agent B
researcher.send_message(
    to="analyst",
    content="Here is the research data",
    data=research_results
)

# Agent B receives
message = analyst.receive_message()
```

### Broadcast

```python
# Broadcast to all agents
matrix.broadcast(
    from_agent="orchestrator",
    content="New task available",
    data=task_details
)
```

### Request-Response

```python
# Synchronous request with response
response = researcher.request(
    to="analyst",
    action="analyze",
    data=raw_data,
    timeout=30
)
```

## Agent Specialization

```python
# Research agent
researcher = Agent(
    name="researcher",
    system_prompt="""You are a research specialist.
    Your role is to find and verify information.
    Always cite your sources.""",
    tools=[WebSearchTool(), WikipediaTool(), ArxivTool()]
)

# Code agent
coder = Agent(
    name="coder",
    system_prompt="""You are a Python expert.
    Write clean, efficient, well-documented code.
    Always include tests.""",
    tools=[PythonREPL(), FileWriter(), GitTool()]
)

# Reviewer agent
reviewer = Agent(
    name="reviewer",
    system_prompt="""You are a code reviewer.
    Check for bugs, security issues, and best practices.
    Be thorough but constructive.""",
    tools=[CodeAnalyzer(), SecurityScanner()]
)
```

## Workflow Patterns

### Sequential

```python
# Agents work in sequence
workflow = SequentialWorkflow([
    ("researcher", "Find information on topic X"),
    ("analyst", "Analyze the findings"),
    ("writer", "Write a summary")
])

result = matrix.run_workflow(workflow)
```

### Parallel

```python
# Agents work simultaneously
workflow = ParallelWorkflow({
    "researcher": "Research aspect A",
    "analyst": "Analyze existing data B",
    "coder": "Prototype solution C"
})

results = matrix.run_workflow(workflow)
# results = {"researcher": ..., "analyst": ..., "coder": ...}
```

### Hierarchical

```python
# Manager delegates to specialized teams
workflow = HierarchicalWorkflow(
    manager="project_lead",
    teams={
        "research_team": ["researcher_1", "researcher_2"],
        "dev_team": ["coder_1", "coder_2", "tester"]
    }
)

result = matrix.run_workflow(workflow, task="Build feature X")
```

## Consensus Mechanisms

```python
# Voting on decisions
matrix = MetaMatrix(
    consensus="voting",
    voting_threshold=0.6  # 60% agreement required
)

# Raft consensus (leader election)
matrix = MetaMatrix(
    consensus="raft",
    election_timeout=5
)

# Byzantine fault tolerance
matrix = MetaMatrix(
    consensus="pbft",
    fault_tolerance=1  # Tolerate 1 faulty agent
)
```

## Monitoring & Observability

```python
from rlm_toolkit.callbacks import MultiAgentCallback

# Monitor agent interactions
callback = MultiAgentCallback(
    log_messages=True,
    log_tool_calls=True,
    metrics_endpoint="http://localhost:8080"
)

matrix = MetaMatrix(callbacks=[callback])

# Access metrics
metrics = matrix.get_metrics()
print(metrics)
# {
#   "total_messages": 45,
#   "agent_activity": {"researcher": 20, "analyst": 15, ...},
#   "avg_response_time": 1.5,
#   "consensus_rounds": 3
# }
```

## Best Practices

!!! tip "Agent Design"
    - Keep agents focused on specific domains
    - Clear separation of responsibilities
    - Define explicit communication protocols

!!! tip "Security"
    - Use trust zones for sensitive data
    - Enable encryption for confidential zones
    - Audit all cross-zone communication

!!! tip "Scalability"
    - Start with minimal agents
    - Add agents as needed
    - Use P2P topology for large systems

!!! tip "Debugging"
    - Enable verbose logging
    - Monitor message flows
    - Use callbacks for observability

## Related

- [Tutorial: Multi-Agent](../tutorials/09-multiagent.md)
- [Concept: Agents](./agents.md)
- [Concept: Security](./security.md)
