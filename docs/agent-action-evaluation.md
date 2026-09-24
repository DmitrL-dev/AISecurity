# Before an AI agent takes an action

An agent can read untrusted material and then call a tool with write access. A
prompt filter alone cannot tell you whether the resulting action was authorized.
Use this short worksheet to review one workflow before widening its permissions.

## A synthetic example

A user asks an assistant to mark ticket `T-17` as resolved. The assistant reads
a retrieved support note that asks it to issue a refund instead. The note is
task data; it is not a new grant of authority. Before a write tool runs, ask:

| Question | Evidence to inspect |
| --- | --- |
| What did the user authorize? | The request and the permitted action and target. |
| Where did the new instruction come from? | The source of the retrieved note and its trust level. |
| What will the tool actually do? | The tool name, target and final arguments, checked against the authorization. |
| What happened after the call? | The decision, tool result and a replayable test for both allowed and rejected cases. |

Test the intended ticket update, the attempted refund and an ambiguous request.
Record misses, false blocks and execution errors separately. Use synthetic data
or an authorized sandbox; do not put customer records or credentials in public
issues.

This is an evaluation worksheet, not a claim that this repository enforces tool
actions. [Guard Lab](../tools/guard-lab/README.md) evaluates labelled input text
locally with the public core. It does not exercise the commercial action guard.
For current Spectorn product scope and regional access, [choose your region](https://spectorn.ai/).
