# Tutorial 9: Multi-Agent Systems

Build decentralized P2P multi-agent systems with Trust Zones using the Meta Matrix architecture.

## What is Multi-Agent?

RLM-Toolkit's multi-agent system provides:

- **Decentralized P2P**: No central orchestrator bottleneck
- **Trust Zones**: Memory isolation and security
- **Message-Driven**: Async communication between agents
- **Self-Evolving Agents**: Agents that improve over time

## Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Meta Matrix Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    Agent A ←──────→ Agent B                                      │
│       ↑                ↑                                        │
│       ↓                ↓                                        │
│    Agent C ←──────→ Agent D                                      │
│                                                                  │
│  • P2P messaging (no central orchestrator)                      │
│  • Each agent has own memory + shared pool                      │
│  • Trust zones control visibility                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Step 1: Create Basic Agents

```python
from rlm_toolkit.agents import Agent, AgentConfig

# Create researcher agent
researcher = Agent(
    name="researcher",
    role="Research specialist",
    goal="Find accurate information from multiple sources",
    llm="gpt-4o"
)

# Create writer agent
writer = Agent(
    name="writer", 
    role="Content writer",
    goal="Create clear, engaging content",
    llm="gpt-4o"
)

# Create reviewer agent
reviewer = Agent(
    name="reviewer",
    role="Quality reviewer",
    goal="Ensure accuracy and quality",
    llm="gpt-4o"
)
```

## Step 2: Create Multi-Agent Runtime

```python
from rlm_toolkit.agents import MultiAgentRuntime

# Create runtime
runtime = MultiAgentRuntime()

# Register agents
runtime.register(researcher)
runtime.register(writer)
runtime.register(reviewer)

# Run a task
result = runtime.run(
    task="Write a comprehensive article about quantum computing",
    workflow=[
        {"agent": "researcher", "action": "research the topic"},
        {"agent": "writer", "action": "write the article"},
        {"agent": "reviewer", "action": "review and suggest improvements"},
        {"agent": "writer", "action": "incorporate feedback"}
    ]
)

print(result.final_output)
```

## Step 3: Message-Driven Communication

```python
from rlm_toolkit.agents import Agent, AgentMessage, MessageQueue

# Create message queue
queue = MessageQueue()

# Agents communicate via messages
researcher = Agent(name="researcher", message_queue=queue)
writer = Agent(name="writer", message_queue=queue)

# Send message
researcher.send(AgentMessage(
    to="writer",
    content="Here are the research findings: ...",
    metadata={"sources": ["arxiv", "wikipedia"]}
))

# Writer receives and processes
message = writer.receive()
response = writer.process(message)
```

## Step 4: Trust Zones

```python
from rlm_toolkit.agents import SecureAgent, TrustZone

# Define trust zones
public_zone = TrustZone(name="public", level=0)
internal_zone = TrustZone(name="internal", level=1)
confidential_zone = TrustZone(name="confidential", level=2)

# Create agents in different zones
public_agent = SecureAgent(
    name="public_helper",
    trust_zone=public_zone
)

internal_agent = SecureAgent(
    name="internal_processor",
    trust_zone=internal_zone
)

confidential_agent = SecureAgent(
    name="data_handler",
    trust_zone=confidential_zone,
    encryption_enabled=True
)

# Agents can only communicate within or up their trust level
# confidential can talk to all
# internal can talk to internal and public
# public can only talk to public
```

## Step 5: Self-Evolving Agents

```python
from rlm_toolkit.agents import EvolvingAgent

# Create agent that improves over time
evolving = EvolvingAgent(
    name="learning_agent",
    role="Adaptive problem solver",
    evolution_strategy="challenger_solver",
    meta_store_path="./agent_evolution"
)

# Agent learns from each interaction
for task in tasks:
    result = evolving.run(task)
    # Agent stores successful patterns
    
# Later interactions benefit from learning
```

## Step 6: Secure Evolving Agents

Combine security and evolution:

```python
from rlm_toolkit.agents import SecureEvolvingAgent, TrustZone

# Agent with both security and self-improvement
agent = SecureEvolvingAgent(
    name="secure_evolution",
    trust_zone=TrustZone(name="confidential", level=2),
    encryption_enabled=True,
    evolution_strategy="challenger_solver",
    h_mem_enabled=True  # Use hierarchical memory
)

# Secure, persistent, and improving
result = agent.run("Analyze sensitive financial data")
```

## Step 7: Agent Registry and Discovery

```python
from rlm_toolkit.agents import AgentRegistry, MultiAgentRuntime

# Create registry
registry = AgentRegistry()

# Register agents with capabilities
registry.register(
    Agent(name="math_expert"),
    capabilities=["calculation", "statistics", "algebra"]
)

registry.register(
    Agent(name="code_expert"),
    capabilities=["python", "javascript", "debugging"]
)

registry.register(
    Agent(name="writer"),
    capabilities=["writing", "editing", "summarization"]
)

# Runtime discovers agents by capability
runtime = MultiAgentRuntime(registry=registry)

# Automatically selects appropriate agents
result = runtime.run(
    "Calculate statistics for this data, then write a report",
    auto_select=True  # Auto-select by capability
)
```

## Complete Application: Research Team

```python
# research_team.py
from rlm_toolkit.agents import (
    Agent, SecureAgent, EvolvingAgent,
    MultiAgentRuntime, AgentRegistry, TrustZone
)
from rlm_toolkit.tools import WebSearch, Calculator, PythonREPL

class ResearchTeam:
    def __init__(self):
        self.registry = AgentRegistry()
        self._setup_agents()
        self.runtime = MultiAgentRuntime(registry=self.registry)
    
    def _setup_agents(self):
        # Research lead - evolving with memory
        research_lead = EvolvingAgent(
            name="research_lead",
            role="Research team leader",
            goal="Coordinate research and synthesize findings",
            llm="gpt-4o",
            tools=[WebSearch()],
            evolution_strategy="self_critique"
        )
        
        # Data analyst - with tools
        data_analyst = Agent(
            name="data_analyst",
            role="Data analysis specialist",
            goal="Analyze data and find patterns",
            llm="gpt-4o",
            tools=[Calculator(), PythonREPL(sandbox=True)]
        )
        
        # Writer - focused on communication
        writer = Agent(
            name="writer",
            role="Technical writer",
            goal="Create clear reports and documentation",
            llm="gpt-4o"
        )
        
        # Quality reviewer - secure zone
        reviewer = SecureAgent(
            name="reviewer",
            role="Quality assurance",
            goal="Ensure accuracy and completeness",
            llm="gpt-4o",
            trust_zone=TrustZone(name="internal", level=1)
        )
        
        # Register with capabilities
        self.registry.register(research_lead, 
            capabilities=["research", "coordination", "synthesis"])
        self.registry.register(data_analyst,
            capabilities=["data", "statistics", "analysis"])
        self.registry.register(writer,
            capabilities=["writing", "documentation", "reports"])
        self.registry.register(reviewer,
            capabilities=["review", "quality", "validation"])
    
    def research(self, topic: str) -> dict:
        """Conduct comprehensive research on a topic."""
        
        workflow = [
            {"agent": "research_lead", "action": f"research {topic} thoroughly"},
            {"agent": "data_analyst", "action": "analyze any quantitative data"},
            {"agent": "writer", "action": "write comprehensive report"},
            {"agent": "reviewer", "action": "review for accuracy and completeness"},
            {"agent": "writer", "action": "incorporate feedback and finalize"}
        ]
        
        result = self.runtime.run(
            task=f"Research and report on: {topic}",
            workflow=workflow
        )
        
        return {
            "report": result.final_output,
            "agents_used": result.agents_used,
            "iterations": result.workflow_iterations,
            "sources": result.sources
        }

def main():
    print("🔬 Research Team Multi-Agent System")
    print("   Powered by RLM-Toolkit\n")
    
    team = ResearchTeam()
    
    while True:
        topic = input("📝 Research topic: ").strip()
        
        if topic.lower() in ['quit', 'exit']:
            break
        
        print("\n⏳ Research team is working...\n")
        
        result = team.research(topic)
        
        print(f"📄 Research Report:\n")
        print(result["report"])
        print(f"\n👥 Agents used: {', '.join(result['agents_used'])}")
        print(f"🔄 Workflow iterations: {result['iterations']}\n")

if __name__ == "__main__":
    main()
```

## Comparison with Other Frameworks

| Feature | LangGraph | CrewAI | RLM Multi-Agent |
|---------|-----------|--------|-----------------|
| Architecture | Centralized | Centralized | **Decentralized P2P** |
| Trust Zones | ❌ | ❌ | ✅ |
| Self-Evolving | ❌ | ❌ | ✅ |
| H-MEM Integration | ❌ | ❌ | ✅ |
| Encryption | ❌ | ❌ | ✅ |

## Best Practices

!!! tip "Agent Specialization"
    Create agents with specific, focused roles:
    ```python
    Agent(name="sql_expert", role="Database query specialist")
    ```

!!! tip "Trust Zone Design"
    Use trust zones for security:
    - Public: User-facing agents
    - Internal: Processing agents
    - Confidential: Data handlers

!!! tip "Message Timeouts"
    Set timeouts for agent communication:
    ```python
    runtime = MultiAgentRuntime(message_timeout=30)
    ```

!!! warning "Resource Management"
    Monitor agent count and memory:
    ```python
    runtime.get_stats()  # Check resource usage
    ```

## Next Steps

- [Concept: Multi-Agent Architecture](../concepts/agents.md)
- [Concept: Trust Zones](../concepts/security.md)
- [API Reference: Agents](../api/agents.md)
