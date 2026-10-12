# Architecture

One agent, one custom MCP server, one human gate.

```
Teacher/app --add_evidence--> MCP server (server.py) <--MCP--> Drafting agent (agent.py) --HTTP--> local LLM (Ollama)
                                  |  core.py: analysis + guardrails
                               SQLite  <-- approve.py / /teacher page (teacher credential, not MCP)
```

## Agent shape

A single agent written as a plain Python loop. No agent framework.

1. Read the profile (`get_profile`), including pending evidence and the drafting rules.
2. Ask the local open-weights model to draft wording.
3. Submit it (`propose_update`). If the server's guardrails reject it, feed the reasons back and retry, at most 3 times.
4. Stop. The agent never approves.

The script, not the model, chooses which tools to call and in what order. The model only writes text. That is a deliberate limit: for a tool that touches children's records, a fixed sequence is easier to audit than a model choosing its own path. The agent still checks its work and recovers from rejection, but it is not fully autonomous. Letting the model pick tools through Ollama tool-calling is a possible later step behind the same gate.

## MCP servers: built versus borrowed

| | What | Why |
|---|---|---|
| **Built** | `learner-profile`: tools `add_evidence`, `get_profile`, `propose_update`. Stdio locally; streamable HTTP in hosted mode with a bearer token. | The domain rules live here: an evidence floor, citations on every claim, a ban on labelling or predictive wording, and pending-until-approved state. Putting them in the server means any client or model gets the same checks. |
| **Borrowed** | None. | A generic database or filesystem MCP server would give an agent raw write access to learner records and bypass the approval gate. A hosted third-party server would also send child data to someone else. |

What is borrowed is infrastructure, not servers: the official `mcp` Python SDK (1.x, pinned below 2), Ollama for local model serving, and SQLite.

Not implemented: MCP resources and prompts. The drafting rules travel inside the `get_profile` result instead.
I did not audit the wider MCP server ecosystem for a closer fit. The decision rests on the privacy and approval requirements above.

## Why approval is not an MCP tool

`approve.py` and the `/teacher` page write to the same database but sit outside MCP, behind a separate credential. An agent connected over MCP has no tool, and no token, that can approve its own proposal. In hosted mode the agent token and the teacher password must differ or the server will not start.

## Known limits

The pattern analysis is simple arithmetic, not a validated psychometric method. The banned-phrase list will miss things, so the teacher is the real safeguard. Tested end to end with a stub drafter; not yet with a real model or an external MCP client. Hosted mode uses shared passwords, with no per-user accounts or rate limiting.
