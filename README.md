# learner-profile-mcp

**Helping teachers spot a child's strengths in term 2, not at the national exam.**

An [MCP](https://modelcontextprotocol.io) server that turns quizzes, projects and teacher notes into a
**sourced learner profile** and plain-language conversation starters for teachers and families.
The agent drafts. A named teacher approves. It never delivers a verdict on a child.

## Run it (one command)

```bash
git clone https://github.com/Benedictmusyoka/learner-profile-mcp && cd learner-profile-mcp && python quickstart.py
```

Needs Python 3.10+ and internet for `pip`. It creates a virtualenv, installs the one dependency,
loads a **fictional** demo learner, and has an agent draft a profile update, then stops and waits for a teacher.
It uses a local open-weights model through [Ollama](https://ollama.com) if one is running, otherwise a built-in stub.
Then, as the teacher:

```bash
.venv/bin/python approve.py list
.venv/bin/python approve.py approve 1 --by "Benedictmusyoka"     # Windows: .venv\Scripts\python
```

## What problem this addresses

IB-style "Approaches to Learning" records are valuable and expensive. A public-school teacher has quiz scores,
registers and memory, spread across several teachers and several years, so patterns that would be obvious over
four years of data stay invisible one term at a time. This tool keeps a lightweight, cited running record so a
pattern can surface after about two terms of evidence, and gives teachers a respectful way to open the conversation.

## How it works

```
teacher/app --add_evidence--> [pending] --get_profile--> open-weights model drafts wording
                                                              |
                          guardrails reject (retry up to 3) <-- propose_update
                                                              |
                         pending proposal --> TEACHER approves (approve.py) --> profile
```

| MCP tool | What it does |
|---|---|
| `add_evidence` | Stores one quiz / project / note as **pending**. No effect on the profile yet. |
| `get_profile` | Returns patterns from **approved** evidence only, each cited `[E12]`, plus pending items and drafting rules. |
| `propose_update` | Accepts model-drafted wording only if it cites sources, asks an open question and avoids labelling or prescriptive language. Then it waits for the teacher. |

`approve.py` is **deliberately not an MCP tool**, so no agent can approve its own work. Approvals record who, when and which model drafted.

## Use with your own model or client

- Real model: `ollama pull qwen2.5:7b` (or Llama, Gemma, Mistral, Aya), then `python quickstart.py` or
  `.venv/bin/python agent.py L-0042 --age 9-12`. Set `OLLAMA_MODEL` / `OLLAMA_HOST` to change.
- Any MCP client (Claude Desktop, Cursor, etc.): command `python`, args `["/path/to/server.py"]`.
- Tests: `python test_e2e.py`.

## Safeguards and honest limits

- **Evidence floor:** fewer than 3 sources across 2 terms shows "not enough evidence yet" (`core.py`; a starting guess to tune with teachers).
- **Context first:** "may need support" comes with checks (attendance, language of instruction, sight/hearing, home circumstances) before anything is read as aptitude.
- **Not prescriptive:** output is questions and options. Ages 9-12 get activities, 13-15 get subject areas to explore.
- The banned-phrase list is a first pass and **will miss things**; the teacher gate is the real safeguard.
- Small local models follow rules imperfectly. Test yours on real notes.
- **Privacy:** use pseudonymous learner IDs; free-text notes can contain names. Get guardian consent and follow local data-protection law (e.g. Kenya's Data Protection Act 2019) before real use. Data stays in a local SQLite file.
- Pattern detection is simple arithmetic, not a validated psychometric instrument. It supports a conversation; it does not measure aptitude.

## License

[MIT](LICENSE)
